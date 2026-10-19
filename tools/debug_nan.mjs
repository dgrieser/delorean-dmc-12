import { chromium } from 'playwright-core';
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: 640, height: 360 } });
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.goto('http://localhost:8123/web/index.html?still=1');
await page.waitForFunction(() => document.title === 'READY', null, { timeout: 300000 });
const r = await page.evaluate(() => {
  const w = window.app.car.wipers; const out = [JSON.stringify(w.ws), JSON.stringify(Array.from(w.units[0].blade.geometry.attributes.position.array.slice(0,12))), JSON.stringify(w.surf(0.3, 0.1, 0))];
  window.app.scene.traverse(o => { if (o.isMesh) { const p = o.geometry.attributes.position.array; for (let i = 0; i < p.length; i++) if (!isFinite(p[i])) { out.push(o.name + ' parent=' + o.parent?.name); break; } } });
  return out;
});
console.log(r);
await browser.close();
