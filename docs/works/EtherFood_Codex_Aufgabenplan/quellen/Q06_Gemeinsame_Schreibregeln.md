# Q06 — Gemeinsame Schreibregeln

Original: `allsummary(1).md`. SHA-256 der vollständigen Upload-Datei: `55bb37c2fb9909384a89d3ac4c7e4b011f1fa8d0319243c04e436fe567570c69`.

Relevanz: Schreibprüfung und gemeinsamer Controller einschließlich Verschieben direkter Quellen nach PixelEng.

Die Zeilennummern in den folgenden Blöcken beziehen sich auf die Originaldatei. Der Text ist ein Quellenbeleg, keine neu erteilte Arbeitsanweisung.

## Originalzeilen 11660–11845

````text
L11660: ## 📝 PyPipelineOutputs.py — ./PiplineToos/PyPipelineOutputs.py
L11661: 
L11662: """Gemeinsame Schreibregeln: prüfen, fehlende Ausgaben erstellen oder bewusst ersetzen."""
L11663: from __future__ import annotations
L11664: 
L11665: import os
L11666: from pathlib import Path
L11667: import tempfile
L11668: 
L11669: 
L11670: def validate(path: Path) -> None:
L11671:     if path.is_symlink() or (path.exists() and not path.is_file()):
L11672:         raise ValueError(f"Ausgabe ist ein Link oder keine reguläre Datei: {path}")
L11673:     for parent in path.parents:
L11674:         if parent.is_symlink() or (parent.exists() and not parent.is_dir()):
L11675:             raise ValueError(f"Ausgabeordner ist ein Link oder kein Verzeichnis: {parent}")
L11676: 
L11677: 
L11678: def action(path: Path, overwrite: bool = False) -> str:
L11679:     validate(path)
L11680:     return ("ERSETZEN" if overwrite else "SKIP") if path.exists() else "NEU"
L11681: 
L11682: 
L11683: def should_write(path: Path, *, overwrite: bool = False, dry_run: bool = False) -> bool:
L11684:     mode = action(path, overwrite)
L11685:     print(f"[{mode}{'; Plan' if dry_run else ''}] {path}", flush=True)
L11686:     return not dry_run and mode != "SKIP"
L11687: 
L11688: 
L11689: def write_text(path: Path, content: str, *, overwrite: bool = False) -> None:
L11690:     if not should_write(path, overwrite=overwrite):
L11691:         return
L11692:     fd, name = tempfile.mkstemp(prefix=".pipeline-", dir=path.parent)
L11693:     try:
L11694:         with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
L11695:             stream.write(content)
L11696:         os.replace(name, path)
L11697:     finally:
L11698:         Path(name).unlink(missing_ok=True)
L11699: 
L11700: ---
L11701: 
L11702: ## 📝 PySpritesheetPipeline.py — ./PiplineToos/PySpritesheetPipeline.py
L11703: 
L11704: #!/usr/bin/env python3
L11705: """Gemeinsamer Ablauf für Streifen-Pipelines: Originale, Grid-Optimierung und Vorschauen."""
L11706: from __future__ import annotations
L11707: 
L11708: import argparse
L11709: from pathlib import Path
L11710: import sys
L11711: 
L11712: import PyImgGif as gif
L11713: import PyImgGrid as raster
L11714: import PyPipelineOutputs as output_policy
L11715: 
L11716: 
L11717: def build_parser(frame_count: int, target_grid: raster.Grid,
L11718:                  source_grid: raster.Grid | None = None):
L11719:     target_name = raster.grid_name(target_grid)
L11720:     parser = argparse.ArgumentParser(
L11721:         description=f"{frame_count}er-Streifen: Original-GIF/HTML → optimiertes {target_name}-PNG → GIF/HTML.",
L11722:         allow_abbrev=False)
L11723:     parser.add_argument("source", nargs="?", type=Path, default=Path.cwd(),
L11724:                         help=f"Ordner mit {frame_count}er-PNG-Streifen; Standard: aktueller Terminalordner")
L11725:     parser.add_argument("--fps", "-f", type=int, choices=gif.FPS_CHOICES, default=8)
L11726:     choices = ((raster.grid_name(source_grid),) if source_grid is not None
L11727:                else (f"{frame_count}x1", f"1x{frame_count}"))
L11728:     parser.add_argument("--grid", choices=choices,
L11729:                         default=raster.grid_name(source_grid) if source_grid is not None else None,
L11730:                         help=("Quellraster Spalten x Zeilen; "
L11731:                               + (f"fest {raster.grid_name(source_grid)}" if source_grid is not None
L11732:                                  else "sonst anhand der längeren Bildseite")))
L11733:     parser.add_argument("--overwrite", action="store_true", help="Erzeugte PNGs, GIFs und HTML ersetzen; Originale erhalten")
L11734:     parser.add_argument("--dry-run", action="store_true", help="Eingaben und Ziele prüfen; nichts schreiben")
L11735:     return parser
L11736: 
L11737: 
L11738: def run(args, *, frame_count: int, target_grid: raster.Grid):
L11739:     raster.validate_grid(target_grid, frame_count)
L11740:     root = args.source.expanduser().resolve()
L11741:     if not root.is_dir():
L11742:         raise ValueError(f"Quellordner fehlt: {root}")
L11743:     archive = root / "PixelEng"
L11744:     if archive.is_symlink() or (archive.exists() and not archive.is_dir()):
L11745:         raise ValueError(f"PixelEng ist ein Link oder kein Ordner: {archive}")
L11746:     manual_grid = raster.parse_grid(args.grid) if args.grid else None
L11747:     source_grids = (manual_grid,) if manual_grid else ((frame_count, 1), (1, frame_count))
L11748:     pending = raster.find_spritesheets(root, source_grids=source_grids)
L11749:     archived = raster.find_spritesheets(archive, source_grids=source_grids) if archive.exists() else []
L11750:     if not pending and not archived:
L11751:         raise ValueError(f"Keine {frame_count}er-PNG-Streifen in {root} oder PixelEng gefunden.")
L11752:     jobs = []
L11753:     moves = []
L11754:     destinations = set()
L11755:     # Vor dem Verschieben alle Quellen, Namenskonflikte und Ausgaben prüfen.
L11756:     for source in sorted([*pending, *archived]):
L11757:         original = archive / source.name
L11758:         if source.parent == root:
L11759:             if original.exists() or original.is_symlink():
L11760:                 raise ValueError(f"Original existiert bereits in PixelEng: {source.name}. "
L11761:                                  "Namenskonflikt zuerst auflösen; Originale werden nicht überschrieben.")
L11762:             moves.append((source, original))
L11763:         frames, original_size, grid = raster.read_frames(source, frame_count=frame_count, source_grid=manual_grid)
L11764:         if raster.get_common_content_box(frames) is None:
L11765:             raise ValueError(f"Alle Frames sind transparent: {source}")
L11766:         output = root / raster.get_output_paths(source, target_grid)[1].name
L11767:         if output in destinations:
L11768:             raise ValueError(f"Mehrere Quellen würden dieselbe Ausgabe erzeugen: {output.name}")
L11769:         destinations.add(output)
L11770:         for target in (output, output.with_name(f"{output.stem}_{args.fps}fps.gif"),
L11771:                        original.with_name(f"{original.stem}_{args.fps}fps.gif")):
L11772:             output_policy.should_write(target, overwrite=args.overwrite, dry_run=True)
L11773:         if output.exists() and not args.overwrite:
L11774:             expected = raster.pack_frames(frames, target_grid)
L11775:             if not raster.reusable_output(output, expected):
L11776:                 raise ValueError(f"Vorhandenes PNG passt nicht zur Quelle: {output}; bleibt unverändert. "
L11777:                                  "Zum Neuerstellen --overwrite verwenden.")
L11778:         if not args.overwrite:
L11779:             for png, animation, layout in (
L11780:                     (source, original.with_name(f"{original.stem}_{args.fps}fps.gif"), grid),
L11781:                     (output, output.with_name(f"{output.stem}_{args.fps}fps.gif"), target_grid)):
L11782:                 if animation.exists() and png.exists() and not gif.reusable_gif(
L11783:                         png, animation, args.fps, gif.Grid(*layout, "Pipeline"), keep_empty=True):
L11784:                     raise ValueError(f"Vorhandenes GIF ist ungültig oder veraltet: {animation}; "
L11785:                                      "bleibt unverändert. Zum Neuerstellen --overwrite verwenden.")
L11786:         jobs.append((original, output, grid))
L11787:         frame_width, frame_height = frames[0].size
L11788:         print(f"{source.name}: {raster.grid_name(grid)} "
L11789:               f"({original_size[0]}x{original_size[1]} px; "
L11790:               f"{frame_count} Frames à {frame_width}x{frame_height} px)"
L11791:               f" → PixelEng/{source.name} + {output.name}", flush=True)
L11792:     for folder in (root, archive):
L11793:         output_policy.should_write(folder / "gif-vergleich.html", overwrite=args.overwrite, dry_run=True)
L11794:     for source, target in moves:
L11795:         print(f"[ARCHIV; Plan] {source} → {target}", flush=True)
L11796:     if args.dry_run:
L11797:         print(f"Plan geprüft: {len(jobs)} Spritesheet(s); keine Dateien geschrieben.")
L11798:         return 0
L11799:     archive.mkdir(exist_ok=True)
L11800:     for source, target in moves:
L11801:         source.rename(target)
L11802: 
L11803:     print("Schritt 1/3: Original-GIFs und HTML in PixelEng erstellen.", flush=True)
L11804:     errors = 0
L11805:     for original, _, grid in jobs:
L11806:         errors += gif.run_sheets([original], args.fps, gif.Grid(*grid, f"Fram{frame_count}-Quelle"),
L11807:                                  overwrite=args.overwrite, keep_empty=True)
L11808:     gallery = gif.build_html_gallery(archive, archive / "gif-vergleich.html", overwrite=args.overwrite,
L11809:                                     gif_paths=[p.with_name(f"{p.stem}_{args.fps}fps.gif") for p, _, _ in jobs])
L11810:     if errors or gallery.skipped:
L11811:         return 1
L11812: 
L11813:     target_name = raster.grid_name(target_grid)
L11814:     print(f"Schritt 2/3: Gemeinsamen transparenten Rand entfernen und {target_name}-PNGs erstellen.", flush=True)
L11815:     outputs = [raster.convert_to_grid(original, frame_count=frame_count, target_grid=target_grid,
L11816:                                       source_grid=grid, output_path=output, overwrite=args.overwrite)
L11817:                for original, output, grid in jobs]
L11818: 
L11819:     print(f"Schritt 3/3: GIFs und HTML der optimierten {target_name}-Sheets erstellen.", flush=True)
L11820:     errors = gif.run_sheets(outputs, args.fps, gif.Grid(*target_grid, f"Fram{frame_count}-Ausgabe"),
L11821:                             overwrite=args.overwrite, keep_empty=True)
L11822:     # Das HTML leitet jedes Raster aus Sheet- und GIF-Framegröße ab, auch bei älteren Ausgaben.
L11823:     gallery = gif.build_html_gallery(root, root / "gif-vergleich.html", overwrite=args.overwrite,
L11824:                                     gif_paths=[p.with_name(f"{p.stem}_{args.fps}fps.gif") for p in outputs])
L11825:     if errors or gallery.skipped:
L11826:         return 1
L11827:     print(f"Fertig: {len(outputs)} optimierte Spritesheet(s); Originale in {archive}.")
L11828:     return 0
L11829: 
L11830: 
L11831: def main(argv=None, *, frame_count: int, target_grid: raster.Grid,
L11832:          source_grid: raster.Grid | None = None):
L11833:     args = build_parser(frame_count, target_grid, source_grid).parse_args(argv)
L11834:     try:
L11835:         return run(args, frame_count=frame_count, target_grid=target_grid)
L11836:     except KeyboardInterrupt:
L11837:         print("\nAbgebrochen. Originale bleiben im Quellordner bzw. in PixelEng erhalten.", file=sys.stderr)
L11838:         return 130
L11839:     except ImportError as exc:
L11840:         print(f"FEHLER: Pipeline unvollständig oder Pillow fehlt: {exc}. "
L11841:               "PyGameTools.py --install ausführen.", file=sys.stderr)
L11842:         return 1
L11843:     except Exception as exc:
L11844:         print(f"FEHLER: {exc}", file=sys.stderr)
L11845:         return 1
````
