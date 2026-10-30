// Exercise both complete car rigs through the public controls and model URLs.
// Serve the repository on :8123, then: node tools/modeltest.mjs
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan', '--autoplay-policy=no-user-gesture-required'] });
try {
  const page = await browser.newPage({ viewport: { width: 1000, height: 750 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  page.on('response', r => { if (r.status() >= 400 && r.url().includes('/assets/')) errors.push(`${r.status()} ${r.url()}`); });
  const ready = () => page.waitForFunction(() => document.title === 'READY', null, { timeout: 90000 });
  const click = selector => page.evaluate(s => document.querySelector(s).click(), selector);
  const tick = seconds => page.evaluate(n => window.app.tick(n), Math.round(seconds * 60));
  const hold = async (selector, seconds) => {
    await page.evaluate(s => document.querySelector(s).dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })), selector);
    await tick(seconds);
    await page.evaluate(s => document.querySelector(s).dispatchEvent(new PointerEvent('pointerup', { bubbles: true })), selector);
  };
  await page.goto(process.env.URL || 'http://localhost:8123/web/?still=1');
  for (const model of ['donor', 'original']) {
    await ready();
    assert.equal(await page.evaluate(() => window.app.state.model), model);
    const structural = await page.evaluate(() => {
      const { app: a, THREE: T } = window, c = a.car;
      const failures = [];
      for (const k of ['doorL', 'doorR', 'hood', 'lid']) {
        let count = 0; c[k].node.traverse(o => { if (o.isMesh) count += o.geometry.attributes.position.count; });
        if (count < 100) failures.push(`${k}: empty moving panel`);
      }
      for (const side of ['L', 'R']) for (const name of ['hl_bulb_Lo', 'hl_bulb_Hi', 'turn_front', 'marker_front', 'marker_rear', 'tl_tail', 'tl_turn', 'tl_rev']) {
        let mesh; c.root.traverse(o => { if (o.isMesh && o.name === name + '_' + side) mesh = o; });
        if (!mesh?.geometry.index.count || !a.lamps.mats[name + '_' + side]) failures.push('Unbound lamp ' + name + '_' + side);
      }
      for (const [key, wheel] of Object.entries(c.wheels)) {
        if (!wheel.spin || !wheel.radius) failures.push('Missing wheel ' + key);
        const b = new T.Box3().setFromObject(wheel.spin), size = b.getSize(new T.Vector3());
        if (size.x < .4 || size.x > .8 || size.y < .4 || size.y > .8) failures.push('Invalid wheel dimensions ' + key);
      }
      c.root.traverse(o => { if (o.isMesh && !Array.from(o.geometry.attributes.position.array).every(Number.isFinite)) failures.push('Non-finite mesh ' + o.name); });
      return failures;
    });
    assert.deepEqual(structural, []);
    for (const name of ['doorL', 'doorR', 'hood', 'lid']) await click(`[data-panel="${name}"]`);
    await tick(3);
    assert(await page.evaluate(() => ['doorL','doorR','hood','lid'].every(k => window.app.car[k].theta > .65)), 'Panels did not open');
    assert(await page.evaluate(() => window.app.lamps.mats.courtesy_rear_L.emissiveIntensity > 0), 'Door lamp stayed dark');
    await click('[data-ign="2"]'); await hold('[data-ign="3"]', 2.5); await tick(2);
    assert(await page.evaluate(() => window.app.sim.engine === 'running' && window.app.sim.rpm > 500), 'Engine did not start');
    await click('[data-lights="2"]'); await click('#hazard'); await click('[data-wipe="low"]');
    for (const side of ['L','R']) await click(`[data-toll="${side}"]`);
    await tick(3);
    assert(await page.evaluate(() => window.app.lamps.mats.hl_bulb_Lo_L.emissiveIntensity > 0), 'Headlamps stayed dark');
    assert(await page.evaluate(() => Object.values(window.app.car.toll).length === 2 && Object.values(window.app.car.toll).every(t => t.pos > .9 && t.mesh.position.distanceTo(t.base) > .05)), 'Toll windows did not move');
    const phase = await page.evaluate(() => window.app.car.wipers.phase); await tick(.2);
    assert.notEqual(await page.evaluate(() => window.app.car.wipers.phase), phase, 'Wipers did not move');
    for (const name of ['doorL', 'doorR', 'hood', 'lid']) await click(`[data-panel="${name}"]`);
    await tick(3);
    assert(await page.evaluate(() => ['doorL','doorR','hood','lid'].every(k => window.app.car[k].latched)), 'Panels did not latch');
    await click('#hbrake'); await click('#drive'); await click('[data-gear="1"]'); await hold('#throttle', 4);
    assert(await page.evaluate(() => window.app.sim.speedMph > 5 && Object.values(window.app.car.wheels).every(w => Math.abs(w.angle) > .5)), 'Driving/wheel spin failed');
    await click('[data-gear="2"]'); await hold('#throttle', 2); await hold('#brake', 5);
    assert(await page.evaluate(() => Math.abs(window.app.sim.speedMph) < 1), 'Brakes failed');
    await page.evaluate(() => dispatchEvent(new KeyboardEvent('keydown', {code:'ArrowLeft'}))); await tick(.5);
    assert(await page.evaluate(() => Math.abs(window.app.car.steerWheelAngle) > .1), 'Steering failed');
    await page.evaluate(() => dispatchEvent(new KeyboardEvent('keyup', {code:'ArrowLeft'})));
    for (const mode of ['driver','passenger','free','cinematic','orbit']) {
      await click(`[data-cam="${mode}"]`); await tick(1.2);
      assert.equal(await page.evaluate(() => window.app.rig.mode), mode);
    }
    for (const env of ['day','night','studio']) {
      await page.evaluate(name => window.app.setEnv(name), env); await tick(.2);
      assert.equal(await page.evaluate(() => window.app.state.env), env);
    }
    const trim = () => page.evaluate(() => {
      let value; window.app.car.root.traverse(o => { if (o.isMesh && (o.material.userData.donorTrim || o.material.name === 'Leather')) value = o.material.color.getHex(); }); return value;
    });
    await click('[data-trim="grey"]'); const grey = await trim();
    await click('[data-trim="black"]'); assert.notEqual(await trim(), grey, 'Trim did not change');
    assert.deepEqual(errors, []);
    console.log(`${model}: rig, panels, lights, engine, windows, wipers, driving, cameras, scenes and trim passed`);
    if (model === 'donor') {
      const url = new URL(page.url()); url.searchParams.set('model', 'original');
      await page.goto(url.href);
      assert(new URL(page.url()).searchParams.get('model') === 'original');
    }
  }
  const url = new URL(page.url()); url.searchParams.set('model', 'donor');
  await page.goto(url.href); await ready();
  assert.equal(await page.evaluate(() => window.app.state.model), 'donor');
  assert.equal(await page.locator('[data-model]').count(), 0);
  console.log('Both model URLs passed; no selector, page or asset errors.');
} finally { await browser.close(); }
