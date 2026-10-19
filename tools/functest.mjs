// Clicks through the control rack in the live app and reports state + errors.
// Time is advanced with app.tick() so the test does not depend on the (software) frame rate.
import { chromium } from 'playwright-core';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist', '--autoplay-policy=no-user-gesture-required'] });
const page = await browser.newPage({ viewport: { width: 800, height: 450 } });
const errors = [];
page.on('pageerror', e => errors.push('pageerror: ' + e.message));
page.on('console', m => { if (m.type() === 'error' && !m.text().includes('404')) errors.push('console: ' + m.text().slice(0, 200)); });
await page.goto('http://localhost:8123/web/index.html?lite&still=1');
await page.waitForFunction(() => document.title === 'READY', null, { timeout: 300000 });
const snap = async (label) => {
  const s = await page.evaluate(() => {
    const a = window.app, c = a.car, s = a.sim, L = a.lamps;
    return { doorL: +(c.doorL.theta * 57.3).toFixed(0), hood: +(c.hood.theta * 57.3).toFixed(0), lid: +(c.lid.theta * 57.3).toFixed(0),
      ign: s.ignition, eng: s.engine, rpm: Math.round(s.rpm), mph: +s.speedMph.toFixed(1), gear: s.gear, lights: L.state.headlights,
      hazard: L.state.hazard, flash: L.flasher.on, wiper: c.wipers.mode, wphase: +c.wipers.phase.toFixed(2), cam: a.rig.mode, env: a.state.env,
      toll: +(c.toll.L?.pos ?? -1).toFixed(2), x: +s.x.toFixed(2), coolF: Math.round(s.coolantF), volts: +s.volts.toFixed(1) };
  });
  console.log(label.padEnd(16), JSON.stringify(s));
};
const tick = sec => page.evaluate(n => window.app.tick(n), Math.round(sec * 60));
const click = sel => page.evaluate(q => document.querySelector(q).click(), sel);
const hold = async (sel, sec) => {
  await page.evaluate(q => document.querySelector(q).dispatchEvent(new PointerEvent('pointerdown', { bubbles: true })), sel);
  await tick(sec);
  await page.evaluate(q => document.querySelector(q).dispatchEvent(new PointerEvent('pointerup', { bubbles: true })), sel);
};
const key = async (code, sec = 0) => {
  await page.evaluate(c => dispatchEvent(new KeyboardEvent('keydown', { code: c })), code);
  if (sec) await tick(sec);
  await page.evaluate(c => dispatchEvent(new KeyboardEvent('keyup', { code: c })), code);
};
await snap('loaded');
await click('[data-panel="doorL"]'); await click('[data-panel="hood"]'); await click('[data-panel="lid"]');
await tick(3); await snap('panels open');
await click('[data-ign="2"]'); await tick(0.5); await snap('ign on');
await hold('[data-ign="3"]', 2.5); await tick(2); await snap('after start');
await click('[data-lights="2"]'); await click('#hazard'); await click('[data-wipe="low"]'); await click('[data-toll="L"]');
await tick(1.3); await snap('lights/wipers');
await tick(1.6); await snap('  +1.6 s');
await click('[data-panel="doorL"]'); await click('[data-panel="hood"]'); await click('[data-panel="lid"]');
await tick(3); await snap('panels closed');
await click('#hbrake'); await click('#drive'); await tick(1); await click('[data-gear="1"]');
await hold('#throttle', 4); await snap('accelerating');
await click('[data-gear="2"]'); await hold('#throttle', 3); await snap('2nd gear');
await hold('#brake', 4); await snap('braked');
await key('ArrowLeft', 0.5); await snap('steered');
await click('[data-cam="driver"]'); await tick(1.2); await snap('driver cam');
await click('[data-cam="passenger"]'); await tick(1.2); await snap('passenger cam');
await click('[data-cam="free"]'); await key('KeyW', 1.5); await snap('free cam');
await click('[data-cam="cinematic"]'); await tick(2); await snap('cinematic');
await click('[data-env="night"]'); await tick(0.5); await page.waitForTimeout(3000); await snap('night');
await click('[data-trim="black"]'); await tick(0.2); await snap('black trim');
await key('KeyK'); await tick(0.2);
await page.evaluate(() => dispatchEvent(new KeyboardEvent('keydown', { code: 'KeyK', shiftKey: true }))); await tick(2); await snap('ign off');
const cam = await page.evaluate(() => window.app.camera.position.toArray().map(v => +v.toFixed(2)));
console.log('camera', cam);
console.log('ERRORS:', errors.length ? errors.join('\n') : 'none');
await browser.close();
