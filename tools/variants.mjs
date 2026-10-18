// usage: node variants.mjs out_prefix W H "cam:cx,cy,cz:tx,ty,tz:fov" "name1|js1" "name2|js2" ...
import { chromium } from 'playwright-core';
const [,, out, w, h, camSpec, ...vars] = process.argv;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome', args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('pageerror', e => console.log('[pageerror]', e.message));
page.on('console', m => { if (m.type() === 'error') console.log('[console]', m.text().slice(0, 300)); });
await page.goto('http://localhost:8123/web/index.html?still=1' + (process.env.QS || ''));
await page.waitForFunction(() => document.title === 'READY', null, { timeout: 300000 });
await page.evaluate(() => { for (const id of ['rack', 'hud']) { const e = document.getElementById(id); if (e) e.style.display = 'none'; } document.querySelector('.fab').style.display = 'none'; document.querySelector('.brand').style.display = 'none'; });
const [, c, t, f] = camSpec.split(':');
await page.evaluate(() => { window.app.frame(); window.app.frame(); });
for (const v of vars) {
  const [name, js] = v.split('|');
  await page.evaluate(new Function('p', `const [c, t, f] = p; const a = window.app; ${js || ''}; window.view(c, t, f); window.view(c, t, f);`), [c.split(',').map(Number), t.split(',').map(Number), +f]);
  await page.screenshot({ path: `${out}${name}.png`, timeout: 400000 });
  console.log('shot', name);
}
await browser.close();
