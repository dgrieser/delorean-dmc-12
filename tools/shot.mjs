import { chromium } from 'playwright-core';
const [,, url, out, w='1280', h='720', wait='3000'] = process.argv;
const browser = await chromium.launch({ executablePath: '/opt/pw-browsers/chromium-1194/chrome-linux/chrome',
  args: ['--use-angle=swiftshader','--enable-unsafe-swiftshader','--ignore-gpu-blocklist','--enable-webgl'] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on('console', m => console.log('[console]', m.type(), m.text()));
page.on('pageerror', e => console.log('[pageerror]', e.message));
await page.goto(url);
await page.waitForTimeout(+wait);
console.log('TITLE', await page.title());
await page.screenshot({ path: out });
await browser.close();
