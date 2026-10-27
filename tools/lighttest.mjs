// Exercise lighting through the UI and measure actual rendered lenses on both cars.
// Serve the repository on :8123, then: node tools/lighttest.mjs
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan'] });
try {
  for (const model of ['donor', 'original']) {
    const page = await browser.newPage({ viewport: { width: 1200, height: 800 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const url = new URL(process.env.URL || 'http://localhost:8123/web/');
    url.searchParams.set('model', model); url.searchParams.set('still', '1');
    await page.goto(url.href);
    await page.waitForFunction(() => document.title === 'READY', null, { timeout: 90000 });
    // Probe the full car, including occluding parts, through a mask of each lens.
    // This catches correct state values bound to an invisible or covered mesh.
    await page.evaluate(() => {
      const { app: a, THREE: T } = window;
      window.lightPixels = name => {
        const mesh = a.car.root.getObjectByName(name);
        if (!mesh?.isMesh) throw new Error('Missing lens ' + name);
        a.scene.updateMatrixWorld(true);
        const g = mesh.geometry, p = g.attributes.position, center = new T.Vector3();
        const ids = [...new Set(g.index.array)];
        for (const i of ids) center.add(new T.Vector3().fromBufferAttribute(p, i));
        center.multiplyScalar(1 / ids.length).applyMatrix4(mesh.matrixWorld);
        const rear = /^(tl_|plate_|marker_rear)/.test(name);
        const offset = name.startsWith('marker') ? new T.Vector3(0, 0, name.endsWith('_L') ? -1 : 1)
          : new T.Vector3(rear ? -1 : 1, name.startsWith('plate') ? -.35 : 0, 0);
        const halfWidth = name.startsWith('plate') ? .04 : .15;
        const camera = new T.OrthographicCamera(-halfWidth, halfWidth, halfWidth * .75, -halfWidth * .75, .01, 5);
        camera.position.copy(center).add(offset); camera.lookAt(center);
        const rt = new T.WebGLRenderTarget(96, 72, { type: T.FloatType }), renderer = a.renderer;
        const oldTarget = renderer.getRenderTarget(), maskScene = new T.Scene();
        const maskMaterial = new T.MeshBasicMaterial({ color: 0xffffff, side: T.DoubleSide });
        const mask = new T.Mesh(g, maskMaterial); mask.matrixAutoUpdate = false; mask.matrix.copy(mesh.matrixWorld);
        maskScene.background = new T.Color(0); maskScene.add(mask);
        const pixels = new Float32Array(96 * 72 * 4), stencil = new Float32Array(pixels.length);
        try {
          renderer.setRenderTarget(rt); renderer.render(maskScene, camera);
          renderer.readRenderTargetPixels(rt, 0, 0, 96, 72, stencil);
          renderer.render(a.scene, camera); renderer.readRenderTargetPixels(rt, 0, 0, 96, 72, pixels);
          let sum = 0, count = 0;
          for (let i = 0; i < pixels.length; i += 4) if (stencil[i] > .5) {
            sum += Math.log1p(.2126 * pixels[i] + .7152 * pixels[i+1] + .0722 * pixels[i+2]); count++;
          }
          if (count < 5) throw new Error('Empty lens mask ' + name);
          return sum / count;
        } finally { renderer.setRenderTarget(oldTarget); rt.dispose(); maskMaterial.dispose(); }
      };
    });
    const click = s => page.evaluate(s => document.querySelector(s).click(), s);
    const tick = n => page.evaluate(n => window.app.tick(n), n);
    const hold = (s, down) => page.evaluate(({s, down}) => document.querySelector(s).dispatchEvent(
      new PointerEvent(down ? 'pointerdown' : 'pointerup', { bubbles: true })), {s, down});
    const intensity = name => page.evaluate(n => window.app.lamps.mats[n]?.emissiveIntensity, name);
    const pixels = names => page.evaluate(ns => Object.fromEntries(ns.map(n => [n, window.lightPixels(n)])), names);
    const sides = names => names.flatMap(n => [n+'_L', n+'_R']);
    const turns = sides(['turn_front', 'marker_front', 'tl_turn']);
    const park = sides(['turn_front', 'marker_front', 'marker_rear', 'tl_tail', 'plate_lenses']);
    const heads = sides(['hl_bulb_Lo', 'hl_bulb_Hi']);
    const reverse = sides(['tl_rev']);
    await tick(120);
    const dark = await pixels([...new Set([...turns, ...park, ...heads, ...reverse])]);
    const visible = async (names, baseline = dark) => {
      const lit = await pixels(names);
      for (const name of names) assert(lit[name] > baseline[name] + .02,
        `${model} ${name}: lens did not brighten (${baseline[name].toFixed(3)} -> ${lit[name].toFixed(3)})`);
    };
    // Indicators require ignition. Hazards must still work with the key off.
    await click('#turnL'); await tick(15);
    assert((await intensity('turn_front_L')) < .01, 'Indicator powered with ignition off');
    assert.match(await page.locator('#note').innerText(), /Indicators need ignition On/);
    assert(await page.locator('#note').isVisible(), 'Missing ignition feedback');
    await click('#turnL'); await click('#hazard'); await tick(15);
    await visible(turns);
    await tick(23);
    for (const name of turns) assert((await intensity(name)) < .3, 'Hazard did not blink off: '+name);
    await click('#hazard'); await tick(120);
    await click('[data-ign="2"]');
    for (const [button, side, other] of [['#turnL','L','R'], ['#turnR','R','L']]) {
      await click(button); await tick(15);
      await visible(['turn_front_', 'marker_front_', 'tl_turn_'].map(n => n+side));
      for (const n of ['turn_front_', 'marker_front_', 'tl_turn_']) assert((await intensity(n+other)) < .01, 'Wrong side illuminated');
      await tick(23); assert((await intensity('tl_turn_'+side)) < .3, 'Indicator did not blink off');
      await tick(18); assert((await intensity('tl_turn_'+side)) > 3, 'Indicator did not blink again');
      await click(button); await tick(120);
    }
    // Parking lights remain lit through the dark half of an indicator cycle.
    await click('[data-lights="1"]'); await tick(90); await visible(park);
    const parked = await pixels(sides(['tl_tail']));
    await click('#turnL'); await tick(38);
    assert((await intensity('turn_front_L')) >= .59, 'Parking filament went out while indicating');
    await click('#turnL'); await tick(90);
    // Brake pedal increases tail brightness; release restores parking brightness.
    await hold('#brake', true); await tick(90); await visible(sides(['tl_tail']), parked);
    await hold('#brake', false); await tick(120);
    for (const n of sides(['tl_tail'])) assert(Math.abs(await intensity(n) - .7) < .01, 'Brake failed to release');
    await click('[data-lights="2"]'); await tick(90); await visible(sides(['hl_bulb_Lo']));
    const lowHigh = await pixels(sides(['hl_bulb_Hi']));
    await click('[data-lights="3"]'); await tick(90); await visible(sides(['hl_bulb_Hi']), lowHigh);
    assert(await page.evaluate(() => window.app.lamps.lights.lowL.intensity > 1000 && window.app.lamps.lights.highR.intensity > 5000));
    await click('[data-lights="0"]'); await tick(120);
    await hold('#flash', true); await tick(60); await visible(sides(['hl_bulb_Hi']));
    await hold('#flash', false); await tick(120);
    assert((await intensity('hl_bulb_Hi_L')) < .01, 'Headlamp flash stuck on');
    await click('[data-gear="R"]'); await tick(90); await visible(reverse);
    await click('[data-gear="N"]'); await tick(120);
    for (const n of reverse) assert((await intensity(n)) < .01, 'Reverse stayed on in neutral');
    await click('[data-cabin="on"]'); await tick(90);
    assert(await page.evaluate(() => window.app.lamps.lights.cabin.intensity > .7));
    await click('[data-cabin="off"]'); await tick(90);
    assert(await page.evaluate(() => window.app.lamps.lights.cabin.intensity < .01));
    await click('[data-cabin="door"]');
    for (const [panel, side] of [['doorL','L'],['doorR','R']]) {
      await click(`[data-panel="${panel}"]`); await tick(180);
      for (const n of ['courtesy_', 'courtesy_rear_']) assert((await intensity(n+side)) > 2, 'Door lamp failed');
      assert(await page.evaluate(() => window.app.lamps.lights.cabin.intensity > .7));
      await click(`[data-panel="${panel}"]`); await tick(180);
      for (const n of ['courtesy_', 'courtesy_rear_']) assert((await intensity(n+side)) < .01, 'Door lamp stayed on');
    }
    assert.deepEqual(errors, []);
    console.log(`${model}: rendered indicators, hazards, parking/markers/plate, low/high/flash, brake and reverse passed; cabin/door controls passed`);
    await page.close();
  }
} finally { await browser.close(); }
