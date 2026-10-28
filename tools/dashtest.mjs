// Dashboard rendering/animation regression checks. Serve the repo on :8123.
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan'] });
try {
  for (const model of ['donor', 'original']) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const errors = [];
    page.on('pageerror', e => errors.push(e.message));
    const url = new URL(process.env.URL || 'http://localhost:8123/web/');
    url.searchParams.set('model', model); url.searchParams.set('still', '1');
    await page.goto(url.href);
    await page.waitForFunction(() => document.title === 'READY' && window.app.cluster.fontsReady, null, { timeout: 90000 });
    const result = await page.evaluate(async () => {
      const a = window.app, c = a.cluster, d = a.displays;
      const checksum = canvas => {
        const data = canvas.getContext('2d').getImageData(0, 0, canvas.width, canvas.height).data;
        let h = 0; for (let i = 0; i < data.length; i += 4) h = (Math.imul(h, 31) + data[i] + data[i+1] + data[i+2]) | 0;
        return h;
      };
      a.tick(120);
      const initial = Object.fromEntries(Object.entries(c.needles).map(([k,v]) => [k,v.node.rotation.z]));
      const oldOdo = checksum(c.base);
      const sim = { electrics: true, speedMph: 45, rpm: 3500, volts: 14, coolantF: 210,
        oilPsi: 50, fuel: .8, odometer: 12345, trip: 345 };
      for (let i = 0; i < 900; i++) c.update(1/60, sim, { panel: true, dimmer: .8 });
      const moved = Object.fromEntries(Object.entries(c.needles).map(([k,v]) => [k,{value:v.v,angle:v.node.rotation.z,initial:initial[k]}]));
      const newOdo = checksum(c.base);
      c.setLamps({}, false); const dark = checksum(c.glow);
      c.setLamps({turnL:true}, false); const left = checksum(c.glow);
      c.setLamps({turnR:true}, false); const right = checksum(c.glow);
      c.setLamps({high:true}, false); const high = checksum(c.glow);
      c.setLamps({}, true); const backlit = checksum(c.glow);
      document.querySelector('[data-ign="0"]').click(); a.tick(120); const radioOff=d.radioMat.emissiveIntensity,clockOff=d.clockMat.emissiveIntensity;
      document.querySelector('[data-ign="1"]').click(); a.tick(120); const radioOn=d.radioMat.emissiveIntensity,clockOn=d.clockMat.emissiveIntensity;
      let consoleLights;
      if(d.controls) {
        await d.controls.ready;
        document.querySelector('[data-ign="2"]').click();document.querySelector('[data-lights="0"]').click();a.tick(10);
        const off=d.controls.faceMaterial.emissiveIntensity;
        document.querySelector('[data-lights="1"]').click();a.tick(10);
        const on=d.controls.faceMaterial.emissiveIntensity;
        a.lamps.state.dimmer=.2;a.tick(10);const dim=d.controls.faceMaterial.emissiveIntensity;
        document.querySelector('[data-ign="0"]').click();a.tick(10);const keyOff=d.controls.faceMaterial.emissiveIntensity;
        consoleLights={off,on,dim,keyOff};
      }
      a.rig.setMode('driver',true); a.frame(); a.frame();
      return { moved, oldOdo, newOdo, dark, left, right, high, backlit, radioOff, radioOn, clockOff, clockOn, consoleLights,
        face:[c.base.width,c.base.height], radio:[d.radio.c.width,d.radio.c.height],
        radioFace:d.radioFaceTexture?.image.width, radioPixels:checksum(d.radio.c),
        instruments:Object.keys(c.needles).length };
    });
    assert.equal(result.instruments, 6);
    for (const [name,n] of Object.entries(result.moved)) {
      assert(Number.isFinite(n.angle), `${model}: invalid ${name} angle`);
      assert(Math.abs(n.angle - n.initial) > .1, `${model}: ${name} stopped moving`);
    }
    assert(Math.abs(result.moved.speedo.value-45)<.1);
    assert(Math.abs(result.moved.tach.value-35)<.1);
    assert.notEqual(result.oldOdo,result.newOdo,'Odometer texture stayed frozen');
    assert.equal(new Set([result.dark,result.left,result.right,result.high,result.backlit]).size,5,'Warning/illumination textures did not update independently');
    assert.equal(result.radioOff,0); assert(result.radioOn>0); assert.notEqual(result.radioPixels,0);
    assert.equal(result.clockOff,0);assert(result.clockOn>0);
    assert.equal(result.face[0],4096); assert.equal(result.radio[0],1024);
    if(model==='donor') {
      assert.equal(result.radioFace,2048);
      const l=result.consoleLights;assert.equal(l.off,0);assert.equal(l.keyOff,0);assert(l.on>l.dim && l.dim>0,'Console illumination did not follow lamps and dimmer');
    }
    assert.deepEqual(errors,[]);
    console.log(`${model}: six live needles, odometer, warning lamps, backlighting, clock/radio power and console illumination passed`);
    await page.close();
  }
} finally { await browser.close(); }
