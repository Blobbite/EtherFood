"""SourceColor accepts stills only and preserves the common exact-color contract."""
from pathlib import Path
import json,os,subprocess,sys,tempfile,unittest
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'Pipline/PiplineToos'))
import PyImgColorPipeline as pipeline
import PyImgColorMatch as color
import PyImgFixedColors as fixed
CLI=ROOT/'Pipline/SourceColor-Pipline/PyPiplineStart-SourceColor.py'


class SourceColorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='source-color-test-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.sources=self.root/'source'
        self.sources.mkdir()
        self.masks=self.root/'masks'
        self.masks.mkdir()
        self.output=self.root/'output'
        self.references=[]
        for direction in color.DIRECTIONS:
            path=self.sources/'stand'/f'hero_stand_{direction}.png'
            path.parent.mkdir(exist_ok=True)
            Image.new('RGBA',(12,10),(50,130,70,255)).save(path)
            self.references.append((path,direction,(1,1)))
        self.jump=self.sources/'jump'/'hero_jump_N.png'
        self.jump.parent.mkdir()
        with Image.new('RGBA',(24,17),(100,150,120,255)) as im:
            im.putpixel((0,0),(1,2,3,0))
            im.putpixel((1,0),(90,140,110,117))
            im.save(self.jump)

    def call(self,*args,expected=0):
        result=subprocess.run([sys.executable,str(CLI),str(self.sources),*map(str,args)],
            capture_output=True,text=True,timeout=45)
        self.assertEqual(result.returncode,expected,result.stdout+result.stderr)
        return result

    def material_inputs(self):
        refs=[{'path':str(path),'direction':direction,'grid':[1,1],'size':[12,10],'frames':1,
               'sha256':color.sha256(path)} for path,direction,_ in self.references]
        profile={'format':fixed.MATERIAL_FORMAT,'version':1,'color_space':'sRGB',
                 'references':refs,'materials':[{'id':1,'name':'Stoff','colors':[[20,40,30],[80,150,90]]}]}
        path=self.root/'profile.json';path.write_text(json.dumps(profile))
        for source in self.sources.rglob('*.png'):
            target=self.masks/source.relative_to(self.sources);target.parent.mkdir(parents=True,exist_ok=True)
            with Image.open(source) as im,im.convert('RGBA') as rgba:
                labels=rgba.getchannel('A').point([0]+[1]*255)
                labels.save(target,pnginfo=fixed.mask_metadata((1,1),color.sha256(source)))
                labels.close()
        return path

    def test_nested_sources_soft_reference_and_no_animations(self):
        before={p:p.read_bytes() for p in self.sources.rglob('*.png')}
        self.call('--output-dir',self.output)
        report=json.loads((self.output/'color-build.json').read_text())
        self.assertEqual(len(report['images']),9)
        self.assertEqual(report['settings']['source_kind'],'single_image')
        self.assertIsNone(report['settings']['fps'])
        self.assertTrue(all(r['grid']==[1,1] and r['frames']==1 for r in report['images']))
        self.assertFalse(list(self.output.rglob('*.gif')))
        self.assertEqual(before,{p:p.read_bytes() for p in before})

    def test_material_palette_alpha_and_no_write_on_repeat_or_dry_run(self):
        profile=self.material_inputs()
        args=('--color-mode','material','--material-profile',profile,'--mask-dir',self.masks,'--output-dir',self.output)
        self.call(*args,'--dry-run')
        self.assertFalse(self.output.exists())
        self.call(*args)
        page=(self.output/'farbvergleich.html').read_text()
        self.assertEqual(page.count('Jeder eingefärbte sichtbare PNG-Pixel gehört exakt'),1)
        self.assertNotIn('IMAGEFORMATCAVEAT',page)
        out=self.output/self.jump.relative_to(self.sources)
        with color.load_png(self.jump) as source,color.load_png(out) as result:
            color.verify_pixels(source,result)
            self.assertEqual(result.getpixel((0,0)),(1,2,3,0))
            self.assertEqual(result.getpixel((1,0))[3],117)
            self.assertTrue({c[:3] for _,c in result.getcolors(1000) if c[3]}<={(20,40,30),(80,150,90)})
        before={p:(p.read_bytes(),p.stat().st_mtime_ns) for p in self.output.rglob('*') if p.is_file()}
        self.call(*args)
        self.assertEqual(before,{p:(p.read_bytes(),p.stat().st_mtime_ns) for p in before})

    def test_spritesheet_named_input_rejected_before_any_output(self):
        Image.new('RGBA',(160,10),(80,100,40,255)).save(self.sources/'hero_run_spritesheet_N.png')
        result=self.call('--output-dir',self.output,expected=1)
        self.assertIn('Spritesheet erkannt',result.stderr)
        self.assertFalse(self.output.exists())

    def test_pose_discovery_ignores_frames_low_qualities_and_masks(self):
        pose=self.root/'pose';high=pose/'comic_high';high.mkdir(parents=True)
        self.jump.replace(high/self.jump.name)
        for folder in (high/'spritesheet-fram16'/'PixelEng',pose/'comic_low',pose/'materialmasken'):
            folder.mkdir(parents=True)
            Image.new('RGBA',(160,10),(20,80,30,255)).save(folder/'ignored.png')
        self.assertEqual(pipeline.discover_single(pose),[high/self.jump.name])

    def test_wide_unlabelled_still_is_not_split(self):
        path=self.sources/'banner.png';Image.new('RGBA',(160,10),(20,80,30,255)).save(path)
        source=pipeline.inspect([path],self.sources,None,single_images=True)[0]
        self.assertEqual(source.grid,(1,1))
        self.assertEqual(source.size,(160,10))

    def test_prepare_masks_and_export_palette_for_nested_stands(self):
        self.call('--prepare-masks',self.masks)
        with Image.open(self.masks/'jump/hero_jump_N.png') as im:
            self.assertEqual(im.size,(24,17))
            self.assertEqual(im.info[fixed.MASK_GRID],'1x1')
        path=self.root/'fixed.json'
        self.call('--export-fixed-palette',path)
        self.assertEqual(len(fixed.load_palette(path)['references']),8)

    def test_material_export_uses_single_stand_references(self):
        self.material_inputs()
        definitions=self.root/'definitions.json'
        definitions.write_text(json.dumps({'format':fixed.DEFINITIONS_FORMAT,'version':1,
            'materials':[{'id':1,'name':'Stoff','levels':2}]}))
        profile=self.root/'exported.json'
        self.call('--export-material-profile',profile,'--material-definitions',definitions,'--mask-dir',self.masks)
        result=fixed.load_material_profile(profile)
        self.assertTrue(all(r['grid']==[1,1] and r['frames']==1 for r in result['references']))

    def test_missing_mask_prevents_partial_write(self):
        profile=self.material_inputs()
        (self.masks/'jump/hero_jump_N.png').unlink()
        self.call('--color-mode','material','--material-profile',profile,'--mask-dir',self.masks,
                  '--output-dir',self.output,expected=1)
        self.assertFalse(self.output.exists())

    def test_template_words_in_image_names_remain_unchanged(self):
        target=self.jump.with_name('hero_jump_PRESENTATION_GIFNOTE_N.png')
        self.jump.rename(target)
        self.call('--output-dir',self.output)
        page=(self.output/'farbvergleich.html').read_text()
        self.assertIn('jump/hero_jump_PRESENTATION_GIFNOTE_N.png',page)


if __name__=='__main__':unittest.main()
