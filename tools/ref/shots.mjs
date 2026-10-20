// Render the viewer from the calibrated reference cameras (tools/ref/cameras.json).
// usage: node tools/ref/shots.mjs <outdir> [views...]     (serve the repo root on :8123 first:
//        python3 -m http.server 8123)   env: CHROME = browser binary, URL = page, QS = extra query,
//        MASK=1 = silhouette pass (the car alone on magenta), DOOR = open-door angle in degrees,
//        JS = script run in the page before the shots
import { chromium } from 'playwright-core';
import fs from 'fs';
const [,, out, ...only] = process.argv;
const cams = JSON.parse(fs.readFileSync(new URL('./cameras.json', import.meta.url))).cams;
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', headless: true,
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan'] });
const page = await browser.newPage({ viewport: { width: 1024, height: 683 } });
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.goto((process.env.URL || 'http://localhost:8123/web/index.html') + '?still=1' + (process.env.QS || ''));
await page.waitForFunction(() => document.title === 'READY', null, { timeout: 300000 });
await page.evaluate(() => {
  window.app.rig.update = () => {};
  for (const s of ['.rack', '.hud', '.fab', '.brand', '#loader']) document.querySelectorAll(s).forEach(e => { e.style.display = 'none'; });
});
if (process.env.JS) await page.evaluate(new Function(process.env.JS));    // e.g. material experiments
fs.mkdirSync(out, { recursive: true });
for (const [name, c] of Object.entries(cams)) {
  if (only.length && !only.includes(name)) continue;
  await page.evaluate(v => {
    const a = window.app, car = a.car;
    for (const k of ['doorL', 'doorR']) {
      const p = car[k], open = v.doors.includes(k);
      p.latched = !open; p.theta = open ? (v.doorAngle ?? p.p.max) : 0; p.omega = 0; p.apply();
    }
    a.env.contact.update(a.scene, a.scene.getObjectByName('CarRoot'));
    a.renderer.shadowMap.needsUpdate = true;
    a.env.cyc.visible = Math.hypot(...v.p) < 15;            // the long-lens side view stands outside the cyc
    if (v.mask) {                                   // silhouette pass: the car on flat magenta
      a.env.cyc.visible = false; a.env.floor.mesh.visible = false; a.env.contact.mesh.visible = false;
      a.scene.background = new window.THREE.Color(1, 0, 1); a.bloom.strength = 0;
    }
    a.camera.position.set(...v.p); a.camera.quaternion.set(...v.q); a.camera.fov = v.fov;
    a.camera.updateProjectionMatrix(); a.camera.updateMatrixWorld();
    a.frame(); a.frame();
  }, { ...c.three, mask: !!process.env.MASK, doorAngle: process.env.DOOR ? +process.env.DOOR * Math.PI / 180 : undefined });
  await page.screenshot({ path: `${out}/${name}.png` });
  console.log('shot', name);
}
await browser.close();
