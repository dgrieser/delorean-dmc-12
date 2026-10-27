// GPU regression check: transparent atlas texels must reveal the background,
// while opaque texels (including white cabin lettering) must remain visible.
// Run against the repo server: node tools/donor-materialtest.mjs
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan'] });
try {
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  const url = new URL(process.env.URL || 'http://localhost:8123/web/');
  url.searchParams.set('model', 'donor'); url.searchParams.set('still', '1');
  await page.goto(url.href);
  await page.waitForFunction(() => document.title === 'READY', null, { timeout: 90000 });
  const results = await page.evaluate(() => {
    const { THREE: T, app } = window;
    const maps = new Map();
    app.car.root.traverse(o => {
      if (o.isMesh && o.material.map?.image?.src) maps.set(o.material.map.image.src.split('/').pop(), o.material);
    });
    const renderer = new T.WebGLRenderer(), scene = new T.Scene();
    const target = new T.WebGLRenderTarget(4, 4);
    const camera = new T.OrthographicCamera(-1, 1, 1, -1, .1, 10); camera.position.z = 1;
    scene.background = new T.Color('#204060');
    renderer.setRenderTarget(target);
    const pixel = () => {
      renderer.render(scene, camera);
      const p = new Uint8Array(4); renderer.readRenderTargetPixels(target, 2, 2, 1, 1, p);
      return Array.from(p);
    };
    const background = pixel(), results = [];
    try {
      for (const file of ['Interior_D.png', 'Engine_D.png', 'Chassis_D.png', 'Badge_SetA_D.png']) {
        const source = maps.get(file);
        if (!source) throw new Error('Missing material: ' + file);
        const im = source.map.image, canvas = document.createElement('canvas');
        canvas.width = im.width; canvas.height = im.height;
        const ctx = canvas.getContext('2d'); ctx.drawImage(im, 0, 0);
        const data = ctx.getImageData(0, 0, im.width, im.height).data;
        const find = opaque => {
          for (let y = 2; y < im.height - 2; y++) for (let x = 2; x < im.width - 2; x++) {
            const i = (y * im.width + x) * 4;
            if (opaque && file === 'Interior_D.png' && Math.min(data[i], data[i+1], data[i+2]) < 220) continue;
            if ([-1, 0, 1].every(dy => [-1, 0, 1].every(dx => data[((y+dy)*im.width+x+dx)*4+3] === (opaque ? 255 : 0))))
              return [(x+.5)/im.width, (y+.5)/im.height];
          }
          throw new Error('Missing test texel in ' + file);
        };
        const geometry = new T.PlaneGeometry(2, 2), material = source.clone();
        material.emissive.setRGB(1, 1, 1); material.emissiveIntensity = 1;
        const mesh = new T.Mesh(geometry, material); scene.add(mesh);
        const sample = uv => {
          for (let i = 0; i < geometry.attributes.uv.count; i++) geometry.attributes.uv.setXY(i, ...uv);
          geometry.attributes.uv.needsUpdate = true;
          return pixel();
        };
        const holeUV = find(false), hole = sample(holeUV), solid = sample(find(true));
        // Negative control reproduces the original importer bug with the same texel.
        material.alphaTest = 0; const unmasked = sample(holeUV);
        results.push({ file, hole, solid, unmasked, background,
          transparent: source.transparent, depthWrite: source.depthWrite });
        scene.remove(mesh); geometry.dispose(); material.dispose();
      }
    } finally { target.dispose(); renderer.dispose(); }
    return results;
  });
  for (const r of results) {
    assert.deepEqual(r.hole, r.background, `${r.file}: transparent background rendered solid`);
    assert.notDeepEqual(r.solid, r.background, `${r.file}: visible detail disappeared`);
    assert.notDeepEqual(r.unmasked, r.background, `${r.file}: negative control did not reproduce bug`);
    assert.equal(r.transparent, false); assert.equal(r.depthWrite, true);
    console.log(`${r.file}: cutouts visible through; opaque details preserved`);
  }
  assert.deepEqual(errors, []);
} finally { await browser.close(); }
