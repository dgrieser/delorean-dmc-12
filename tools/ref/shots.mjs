// Render the viewer from the calibrated reference cameras (tools/ref/cameras.json).
// usage: node tools/ref/shots.mjs <outdir> [views...]     (serve the repo root on :8123 first:
//        python3 -m http.server 8123)   env: CHROME = browser binary, URL = page, QS = extra query,
//        MASK=1 = silhouette pass (the car alone on magenta), REFL=1 = reflection pass (each stainless
//        pixel holds its reflection direction in the studio rig's camera-relative frame, D * 0.5 + 0.5
//        after the sRGB encode, everything else black; tools/tex/studio_fit.py), DOOR = open-door
//        angle in degrees, JS = script run in the page before the shots
import { chromium } from 'playwright-core';
import fs from 'fs';
const [,, out, ...only] = process.argv;
const cams = JSON.parse(fs.readFileSync(new URL('./cameras.json', import.meta.url))).cams;
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome', headless: true,
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan'] });
const page = await browser.newPage({ viewport: { width: 1024, height: 683 } });
page.on('pageerror', e => console.log('[pageerror]', e.message));
// Calibration and material fitting target our procedural model by default.
// QS='&model=donor' selects the imported car for a visual comparison.
const url = new URL(process.env.URL || 'http://localhost:8123/web/index.html');
url.searchParams.set('still', '1');
for (const [key, value] of new URLSearchParams((process.env.QS || '').replace(/^&/, ''))) url.searchParams.set(key, value);
if (!url.searchParams.has('model')) url.searchParams.set('model', 'original');
await page.goto(url.href);
await page.waitForFunction(() => document.title === 'READY', null, { timeout: 300000 });
await page.evaluate(() => {
  window.app.rig.update = () => {};
  for (const s of ['.rack', '.hud', '.fab', '.brand', '#loader']) document.querySelectorAll(s).forEach(e => { e.style.display = 'none'; });
});
if (process.env.JS) await page.evaluate(new Function(process.env.JS));    // e.g. material experiments
if (process.env.REFL) await page.evaluate(() => {
  const { THREE, app: a } = window;
  a.renderer.toneMapping = THREE.NoToneMapping;
  // the lookup direction of the studio's environment map: the world reflection vector turned by
  // scene.environmentRotation as three.js does it (R_y(-rotation))
  const refl = new THREE.ShaderMaterial({
    uniforms: { rot: { value: 0 } }, side: THREE.DoubleSide,
    vertexShader: 'varying vec3 vN; varying vec3 vP;\n' +
      'void main() { vec4 w = modelMatrix * vec4(position, 1.0); vP = w.xyz;\n' +
      '  vN = transpose(inverse(mat3(modelMatrix))) * normal; gl_Position = projectionMatrix * viewMatrix * w; }',
    fragmentShader: 'uniform float rot; varying vec3 vN; varying vec3 vP;\n' +
      'void main() { vec3 N = normalize(vN) * (gl_FrontFacing ? 1.0 : -1.0);\n' +
      '  vec3 R = reflect(normalize(vP - cameraPosition), N); float c = cos(-rot), s = sin(-rot);\n' +
      '  gl_FragColor = vec4(vec3(c * R.x + s * R.z, R.y, -s * R.x + c * R.z) * 0.5 + 0.5, 1.0); }',
  });
  refl.onBeforeRender = (r, scene) => { refl.uniforms.rot.value = scene.environmentRotation.y; };
  const black = new THREE.MeshBasicMaterial({ color: 0x000000, side: THREE.DoubleSide });
  const isSteel = m => m?.name === 'Stainless';
  a.scene.getObjectByName('CarRoot').traverse(o => {
    if (!o.isMesh) return;
    o.material = Array.isArray(o.material) ? o.material.map(m => isSteel(m) ? refl : black) : isSteel(o.material) ? refl : black;
  });
});
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
    if (v.mask || v.refl) {                         // silhouette pass: the car on flat magenta
      a.env.cyc.visible = false; a.env.floor.mesh.visible = false; a.env.contact.mesh.visible = false;
      a.scene.background = new window.THREE.Color(...(v.refl ? [0, 0, 0] : [1, 0, 1])); a.bloom.strength = 0;
    }
    a.camera.position.set(...v.p); a.camera.quaternion.set(...v.q); a.camera.fov = v.fov;
    a.camera.updateProjectionMatrix(); a.camera.updateMatrixWorld();
    a.frame(); a.frame();
  }, { ...c.three, mask: !!process.env.MASK, refl: !!process.env.REFL, doorAngle: process.env.DOOR ? +process.env.DOOR * Math.PI / 180 : undefined });
  await page.screenshot({ path: `${out}/${name}.png` });
  console.log('shot', name);
}
await browser.close();
