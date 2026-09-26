// Optionaler Browsertest mit Playwright; für die Pipeline selbst nicht erforderlich.
// Fixture: 16- und 8-Frame-Sheets sowie Einzelbilder in jeweils acht Richtungen.
// node test_comparison_browser.cjs /pfad/aufloesungsvergleich.html [Screenshot-Ordner] [Native-GIF-HTML] [Nur-Einzelbilder-HTML]
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {pathToFileURL} = require('node:url');
const {chromium} = require('playwright');

async function main() {
  assert(process.argv[2], 'Pfad zur erzeugten Vergleichsseite fehlt.');
  const browser = await chromium.launch({headless: true});
  try {
    const page = await browser.newPage({viewport: {width: 1500, height: 1000}, reducedMotion: 'reduce'});
    await page.clock.install({time: new Date('2026-01-01T00:00:00Z')});
    await page.clock.pauseAt(new Date('2026-01-01T00:00:00Z'));
    const errors = [], network = [], imageRequests = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('request', request => {if (/^https?:/.test(request.url())) network.push(request.url());if(request.resourceType()==='image')imageRequests.push(request.url());});
    await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
    await page.waitForSelector('body[data-ready="true"]');
    assert.equal(await page.locator('.card').count(), 5);
    assert.equal(await page.locator('.card canvas').count(), 5);
    assert.equal(await page.locator('#directions button:enabled').count(), 8);
    assert.equal(await page.locator('#play').innerText(), 'Abspielen');
    assert.equal(imageRequests.length, 5, 'Zu Beginn nur ein Spritesheet je Variante laden.');
    assert(imageRequests.every(url => url.endsWith('.png') && !url.includes('-bilder/')));
    const fpsChoices = ['2','4','6','8','10','12','16','18','20','22','24'];
    assert.deepEqual(await page.locator('#fps option').evaluateAll(options => options.map(option => option.value)), fpsChoices);
    const equalSizes = () => page.locator('canvas').evaluateAll(canvases => canvases.map(canvas => {
      const box = canvas.getBoundingClientRect(); return Math.max(box.width, box.height);
    }));
    assert((await equalSizes()).every(side => Math.abs(side - 224) < 0.1));
    await page.locator('[data-direction="SW"]').click();
    await page.waitForSelector('body[data-ready="true"]');
    assert((await page.locator('.filename').allTextContents()).every(name => name.includes('_SW_')));
    await page.locator('#next').click();
    assert.equal(await page.locator('#frameLabel').innerText(), 'Frame 2 / 16');
    assert((await page.locator('.frame-info').allTextContents()).every(text => text === 'PNG-Frame 2 / 16'));
    // file:// erlaubt das Anzeigen lokaler PNGs, aber nicht das Auslesen der
    // dadurch geschützten Canvas. Für die Farbprüfung dieselben Dateien lesen.
    const sources = await page.evaluate(() => {
      const tracks = JSON.parse(document.getElementById('comparison-data').textContent).sets[0].directions.SW;
      return Object.fromEntries(['pixel_high','pixel_low'].map(name => [name, tracks[name].sheet]));
    });
    for (const name of Object.keys(sources)) {
      if (!sources[name].startsWith('data:')) sources[name] = 'data:image/png;base64,' + fs.readFileSync(new URL(sources[name], page.url())).toString('base64');
    }
    const lowUsesHighColors = await page.evaluate(async sources => {
      async function colors(variant) {
        const image = new Image();image.src = sources[variant];await image.decode();
        const canvas = document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
        canvas.getContext('2d').drawImage(image,0,0);
        const pixels = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
        const result = new Set();
        for (let i = 0; i < pixels.length; i += 4) if (pixels[i + 3]) result.add(`${pixels[i]},${pixels[i + 1]},${pixels[i + 2]}`);
        return result;
      }
      const high = await colors('pixel_high');return [...await colors('pixel_low')].every(color => high.has(color));
    }, sources);
    assert(lowUsesHighColors, 'Low-Spritesheet verwendet unerwartete neue RGB-Farbwerte.');
    const highTrack = await page.evaluate(() => JSON.parse(document.getElementById('comparison-data').textContent).sets[0].directions.SW.comic_high);
    const sheetData = 'data:image/png;base64,' + fs.readFileSync(new URL(highTrack.sheet, page.url())).toString('base64');
    for (const index of [0, highTrack.columns, highTrack.logicalFrames-1]) {
      await page.locator('#frame').fill(String(index));
      const screenshot = 'data:image/png;base64,' + (await page.locator('[data-variant="comic_high"] canvas').screenshot()).toString('base64');
      const pixels = await page.evaluate(async ({sheetData,screenshot,item,index}) => {
        async function pixel(url, x, y) {
          const image=new Image();image.src=url;await image.decode();
          const canvas=document.createElement('canvas');canvas.width=image.width;canvas.height=image.height;
          const ctx=canvas.getContext('2d');ctx.drawImage(image,0,0);
          return [...ctx.getImageData(x??Math.floor(image.width/2),y??Math.floor(image.height/2),1,1).data];
        }
        return {expected:await pixel(sheetData,(index%item.columns)*item.width+Math.floor(item.width/2),Math.floor(index/item.columns)*item.height+Math.floor(item.height/2)),actual:await pixel(screenshot)};
      }, {sheetData,screenshot,item:highTrack,index});
      if(pixels.expected[3]===255)assert.deepEqual(pixels.actual,pixels.expected,'Falsche Spritesheet-Zelle im Canvas.');
    }
    await page.locator('#frame').fill('1');
    const loadedImages = imageRequests.length;
    for (const fps of fpsChoices) {
      await page.locator('#fps').selectOption(fps);
      assert.match(await page.locator('#status').innerText(), new RegExp(` · ${fps} FPS ·`));
      assert.equal(await page.locator('#frameLabel').innerText(), 'Frame 2 / 16');
    }
    for (const [fps, expectedFrame] of [['2', 2], ['24', 13]]) {
      await page.locator('#frame').fill('0');
      await page.locator('#fps').selectOption(fps);
      await page.locator('#play').click();
      await page.clock.runFor(550);
      await page.locator('#play').click();
      assert.equal(await page.locator('#frameLabel').innerText(), `Frame ${expectedFrame} / 16`);
      assert((await page.locator('.frame-info').allTextContents()).every(text => text === `PNG-Frame ${expectedFrame} / 16`));
    }
    assert.equal(imageRequests.length, loadedImages, 'FPS-Wechsel und Abspielen dürfen keine Bilder nachladen.');
    await page.locator('#fps').selectOption('8');
    await page.locator('#play').click();
    await page.clock.runFor(400);
    await page.locator('#play').click();
    assert.equal(await page.locator('#play').innerText(), 'Abspielen');
    await page.locator('#sequence').selectOption('1');
    await page.waitForSelector('body[data-ready="true"]');
    assert.equal(await page.locator('#frame').getAttribute('max'), '7');
    await page.locator('#background').selectOption('light');
    assert.equal(await page.locator('body').getAttribute('data-background'), 'light');
    await page.locator('#smooth').check();
    assert.equal(await page.locator('body').getAttribute('data-smooth'), 'true');
    await page.locator('#size').fill('320');
    assert((await equalSizes()).every(side => Math.abs(side - 320) < 0.1));
    await page.locator('#size').fill('224');
    await page.locator('#smooth').uncheck();
    await page.locator('#background').selectOption('checker');
    await page.locator('[data-direction="S"]').click();
    await page.waitForSelector('body[data-ready="true"]');
    const gifUrl = await page.locator('[data-variant="comic_mid"] .original-gif').getAttribute('href');
    const singleIndex = await page.evaluate(() => JSON.parse(document.getElementById('comparison-data').textContent).sets.findIndex(set => set.single));
    assert(singleIndex >= 0, 'Einzelbildgruppe fehlt in der Testseite.');
    const beforeSingle = imageRequests.length;
    await page.locator('#sequence').selectOption(String(singleIndex));
    await page.waitForSelector('body[data-ready="true"]');
    assert.equal(imageRequests.length - beforeSingle, 5, 'Nur die fünf vorhandenen Einzelbilder laden.');
    assert.equal(await page.locator('.card canvas').count(), 5);
    assert.equal(await page.locator('#frameLabel').innerText(), 'Einzelbild');
    assert.match(await page.locator('#status').innerText(), / · Einzelbild$/);
    assert((await page.locator('.frame-info').allTextContents()).every(text => text === 'Einzelbild'));
    assert((await page.locator('.card-foot a').allTextContents()).every(text => text === 'PNG herunterladen'));
    assert.equal(await page.locator('.original-gif').count(), 0);
    for (const id of ['play', 'previous', 'next', 'frame', 'fps']) assert.equal(await page.locator('#'+id).isDisabled(), true);
    const singleSizes = await page.locator('.card canvas').evaluateAll(canvases => canvases.map(canvas => [canvas.width, canvas.height]));
    assert.deepEqual(singleSizes, [[256,128],[128,64],[64,32],[128,64],[115,58]]);
    await page.clock.runFor(1000);
    assert.equal(await page.locator('#frameLabel').innerText(), 'Einzelbild');
    assert.equal(imageRequests.length - beforeSingle, 5, 'Statische Anzeige darf keine weiteren Bilder laden.');
    await page.locator('[data-direction="NW"]').click();
    await page.waitForSelector('body[data-ready="true"]');
    assert((await page.locator('.filename').allTextContents()).every(name => name.endsWith('_NW.png')));
    if (process.argv[3]) {
      fs.mkdirSync(process.argv[3], {recursive: true});
      await page.screenshot({path: path.join(process.argv[3], 'vergleich-einzelbilder.png'), fullPage: true});
    }
    await page.locator('#sequence').selectOption('0');
    await page.waitForSelector('body[data-ready="true"]');
    for (const id of ['play', 'previous', 'next', 'frame', 'fps']) assert.equal(await page.locator('#'+id).isDisabled(), false);
    assert.equal(await page.locator('#fps').inputValue(), '8');
    await page.locator('#play').click();
    await page.locator('#sequence').selectOption(String(singleIndex));
    await page.waitForSelector('body[data-ready="true"]');
    assert.equal(await page.locator('#play').innerText(), 'Abspielen');
    await page.locator('h1').click();
    await page.keyboard.press('Space');
    await page.keyboard.press('ArrowRight');
    await page.locator('#sequence').selectOption('1');
    await page.waitForSelector('body[data-ready="true"]');
    assert.equal(await page.locator('#play').innerText(), 'Pause', 'Einzelbilder dürfen den Wiedergabestatus nicht ändern.');
    await page.clock.runFor(400);
    assert.notEqual(await page.locator('#frameLabel').innerText(), 'Frame 1 / 8');
    await page.locator('#play').click();
    if (process.argv[3]) {
      fs.mkdirSync(process.argv[3], {recursive: true});
      await page.screenshot({path: path.join(process.argv[3], 'vergleich-desktop.png'), fullPage: true});
    }
    await page.setViewportSize({width: 390, height: 844});
    const mobile = await page.evaluate(() => ({
      pageWidth: document.documentElement.scrollWidth,
      viewport: innerWidth,
      stripWidth: document.querySelector('.comparison-scroll').scrollWidth,
      stripViewport: document.querySelector('.comparison-scroll').clientWidth,
    }));
    assert(mobile.pageWidth <= mobile.viewport, 'Die ganze Seite läuft auf Mobilgeräten über.');
    assert(mobile.stripWidth > mobile.stripViewport, 'Die fünf Varianten müssen horizontal scrollbar bleiben.');
    if (process.argv[3]) await page.screenshot({path: path.join(process.argv[3], 'vergleich-mobil.png'), fullPage: true});
    assert.deepEqual(errors, [], 'JavaScript-Fehler im Browser.');
    assert.deepEqual(network, [], 'Die Offline-Seite hat externe Anfragen ausgelöst.');
    const gallery = await browser.newPage({viewport: {width: 1500, height: 1000}, reducedMotion: 'reduce'});
    gallery.on('pageerror', error => errors.push(error.message));
    gallery.on('request', request => {if (/^https?:/.test(request.url())) network.push(request.url());});
    await gallery.clock.install({time: new Date('2026-01-01T00:00:00Z')});
    await gallery.clock.pauseAt(new Date('2026-01-01T00:00:00Z'));
    await gallery.goto(new URL('gif-vergleich.html', new URL(gifUrl, page.url())).href);
    await gallery.waitForSelector('body[data-ready="true"]');
    assert.equal(await gallery.locator('.card[data-loaded="true"]').count(), 8);
    assert.deepEqual(await gallery.locator('#globalFps option').evaluateAll(options => options.map(option => option.value)), fpsChoices);
    assert.deepEqual(await gallery.locator('.card-fps').first().locator('option').evaluateAll(options => options.map(option => option.value)), fpsChoices);
    await gallery.locator('#globalMode').selectOption('fixed');
    for (const fps of fpsChoices) {
      await gallery.locator('#globalFps').selectOption(fps);
      assert((await gallery.locator('.card').evaluateAll(cards => cards.map(card => card.dataset.fps))).every(value => value === fps));
    }
    for (const [fps, expectedFrame] of [['2', '1'], ['24', '4']]) {
      await gallery.locator('#reset').click();
      await gallery.locator('#globalMode').selectOption('fixed');
      await gallery.locator('#globalFps').selectOption(fps);
      await gallery.locator('#sync').click();
      await gallery.clock.runFor(550);
      await gallery.locator('#play').click();
      assert((await gallery.locator('.card').evaluateAll(cards => cards.map(card => card.dataset.frame))).every(value => value === expectedFrame));
    }
    await gallery.locator('.card-mode').first().selectOption('fixed');
    await gallery.locator('.card-fps').first().selectOption('18');
    assert.equal(await gallery.locator('.card').first().getAttribute('data-fps'), '18');
    assert.deepEqual(errors, [], 'JavaScript-Fehler in einer der HTML-Ansichten.');
    assert.deepEqual(network, [], 'Die HTML-Ansichten müssen offline funktionieren.');
    if (process.argv[4]) {
      const native=await browser.newPage({reducedMotion:'reduce'});
      native.on('pageerror',error=>errors.push(error.message));
      await native.goto(pathToFileURL(path.resolve(process.argv[4])).href);
      await native.waitForSelector('body[data-ready="true"]');
      await native.waitForFunction(()=>{const img=document.querySelector('.card[data-native="true"] .canvas-wrap img');return img&&img.complete&&img.naturalWidth>0;});
      assert.equal(await native.locator('#play').isDisabled(),true);
      assert.equal(await native.locator('.card .frame-row').count(),0);
      assert.match(await native.locator('.card').innerText(),/ohne FPS- und Einzelbildsteuerung/);
    }
    if (process.argv[5]) {
      const singles=await browser.newPage();
      singles.on('pageerror',error=>errors.push(error.message));
      await singles.goto(pathToFileURL(path.resolve(process.argv[5])).href);
      await singles.waitForSelector('body[data-ready="true"]');
      assert.equal(await singles.locator('.card canvas').count(),5);
      assert.equal(await singles.locator('#sequence option').count(),1);
      assert.equal(await singles.locator('#frameLabel').innerText(),'Einzelbild');
      assert.equal(await singles.locator('#play').isDisabled(),true);
      assert.equal(await singles.locator('#fps').isDisabled(),true);
      assert.equal(await singles.locator('.missing').count(),0);
    }
    assert.deepEqual(errors, [], 'JavaScript-Fehler bei der Spritesheet- oder nativen GIF-Vorschau.');
    console.log('Browser OK: beide HTML-Ansichten, lokale Dateien, 11 FPS-Werte mit geprüfter Wiedergabe, Synchronität, Einzelbilder, Farbtreue, Mobilansicht, offline.');
  } finally {
    await browser.close();
  }
}

main().catch(error => {console.error(error);process.exitCode = 1;});
