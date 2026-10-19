// usage: node shots.mjs url outprefix W H view1 view2 ...   view = name:cx,cy,cz:tx,ty,tz:fov
import { chromium } from 'playwright-core';
const [,, url, out, w, h, ...views] = process.argv;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on("pageerror", e => console.log("[pageerror]", e.message, e.stack?.split("\n").slice(0,3).join(" | ")));
page.on('console', m => { if (m.type() !== 'log' || process.env.LOG) console.log('[console]', m.text()); });
await page.goto(url);
await page.waitForFunction(() => document.title === 'READY', null, { timeout: 400000 });
for (const v of views) {
  const [name, c, t, f] = v.split(':');
  await page.evaluate(([c, t, f]) => window.view(c, t, f), [c.split(',').map(Number), t.split(',').map(Number), +f]);
  await page.screenshot({ path: `${out}${name}.png`, timeout: 400000 });
}
await browser.close();
