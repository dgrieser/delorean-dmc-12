// Real multi-touch browser input, not synthetic calls to the camera implementation.
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser = await chromium.launch({ executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--headless=new', '--enable-gpu', '--ignore-gpu-blocklist', '--use-angle=vulkan', '--enable-features=Vulkan'] });
const url = new URL(process.env.URL || 'http://localhost:8123/web/'); url.searchParams.set('still', '1');
try {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true });
  const page = await context.newPage(), errors = [];
  page.on('pageerror', e => errors.push(e.message));
  await page.goto(url.href);
  await page.waitForFunction(() => document.title === 'READY', null, { timeout: 90000 });
  assert.equal(await page.locator('[data-model]').count(), 0);
  const tick = (n=120) => page.evaluate(n => window.app.tick(n), n);
  const mode = async name => { await page.locator(`[data-cam="${name}"]`).tap(); await tick(); };
  const state = () => page.evaluate(() => {
    const a=window.app; return { p:a.camera.position.toArray(), yaw:a.rig.yaw, pitch:a.rig.pitch, fov:a.camera.fov,
      q:a.camera.quaternion.toArray(), pointers:a.rig.pointers.size, mode:a.rig.mode };
  });
  const distance = (a,b) => Math.hypot(...a.map((v,i)=>v-b[i]));
  const cdp = await context.newCDPSession(page);
  const touch = (type,points) => cdp.send('Input.dispatchTouchEvent', {type, touchPoints:points.map(([x,y],id)=>({id,x,y,radiusX:2,radiusY:2,force:1}))});
  const gesture = async (start,end) => {
    await touch('touchStart',start);
    for(let i=1;i<=8;i++) { await touch('touchMove',start.map(([x,y],j)=>[x+(end[j][0]-x)*i/8,y+(end[j][1]-y)*i/8])); await tick(1); }
    await touch('touchEnd',[]);await tick(60);
  };
  await mode('free'); assert(await page.locator('#free-touch-help').isVisible());
  let before=await state();
  await gesture([[150,180]],[[220,210]]);let after=await state();
  assert(Math.abs(after.yaw-before.yaw)>.1 && Math.abs(after.pitch-before.pitch)>.05,'One-finger look failed');
  assert(distance(before.p,after.p)<.001,'Looking moved the camera');
  before=after;await gesture([[120,170],[220,170]],[[160,210],[260,210]]);after=await state();
  assert(distance(before.p,after.p)>.1,'Two-finger pan failed');
  assert(Math.abs(after.yaw-before.yaw)<.001 && Math.abs(after.pitch-before.pitch)<.001,'Pan changed look direction');
  before=after;await gesture([[140,180],[240,180]],[[105,180],[275,180]]);after=await state();
  assert(distance(before.p,after.p)>.15,'Pinch did not move closer');
  const inward=after.p.map((v,i)=>v-before.p[i]);
  before=after;await gesture([[105,180],[275,180]],[[140,180],[240,180]]);after=await state();
  assert(after.p.reduce((sum,v,i)=>sum+(v-before.p[i])*inward[i],0)<0,'Reverse pinch did not move farther');
  // Looking after moving must rotate at the new position, even with residual drift.
  before=after;
  await page.evaluate(()=>window.app.rig.vel.set(.2,0,.1));
  await gesture([[150,180]],[[200,200]]);after=await state();
  assert(distance(before.p,after.p)<.001,'Rotation drifted away from the current position');
  assert(distance(before.q,after.q)>.03,'Rotation after pan and pinch failed');
  await touch('touchStart',[[130,170],[230,170]]);await touch('touchCancel',[]);assert.equal((await state()).pointers,0);
  before=await state();await gesture([[150,180]],[[170,180]]);after=await state();
  assert(Math.abs(after.yaw-before.yaw)>.02 && Math.abs(after.yaw-before.yaw)<.2,'Fresh drag jumped after cancellation');
  // A mode change while a pointer is held must discard the old gesture.
  await touch('touchStart',[[150,180]]);
  await page.evaluate(()=>window.app.rig.setMode('driver',true));
  assert.equal((await state()).pointers,0);await touch('touchEnd',[]);await tick();
  // The donor Recaros moved forward: seat views must start ahead of the
  // headrests, including when looking down at the dashboard on a phone.
  const seatClear = await page.evaluate(() => {
    const a=window.app,T=window.THREE,blocked=[];
    for(const mode of ['driver','passenger']) {
      a.rig.setMode(mode,true);
      for(const pitch of [-.12,-.55]) {
        a.rig.pitch=pitch;a.tick(120);
        for(const x of [-.65,0,.65])for(const y of [-.8,-.4,0,.4]) {
          const ray=new T.Raycaster();ray.setFromCamera(new T.Vector2(x,y),a.camera);ray.far=.20;
          if(ray.intersectObject(a.car.root,true).some(h=>h.object.name==='seat_leather'))blocked.push([mode,pitch,x,y]);
        }
      }
    }
    a.rig.setMode('driver',true);a.tick(120);
    return blocked;
  });
  assert.deepEqual(seatClear,[],'Seat or headrest blocks the seated camera');
  before=await state();await gesture([[140,180],[240,180]],[[100,180],[280,180]]);after=await state();
  assert(after.fov<before.fov-5,'Seat pinch zoom failed');assert(distance(before.p,after.p)<.001,'Seat zoom left the seat');
  await mode('orbit');assert(!(await page.locator('#free-touch-help').isVisible()));
  // Returning from a seat can leave orbit near its minimum distance: zoom out.
  before=await state();await gesture([[110,180],[270,180]],[[140,180],[240,180]]);after=await state();
  assert(distance(before.p,after.p)>.1,'Orbit pinch regressed');
  assert.deepEqual(errors,[]);
  console.log('Mobile: look, pan, pinch in/out, cancellation, mode changes, seat zoom and orbit passed; selector absent.');
  await context.close();

  const desktop=await browser.newPage({viewport:{width:1280,height:900}});
  desktop.on('pageerror',e=>errors.push(e.message));await desktop.goto(url.href);
  await desktop.waitForFunction(()=>document.title==='READY',null,{timeout:90000});
  await desktop.locator('[data-cam="free"]').click();await desktop.evaluate(()=>window.app.tick(120));
  const desktopState=()=>desktop.evaluate(()=>({yaw:window.app.rig.yaw,fov:window.app.camera.fov,p:window.app.camera.position.toArray()}));
  before=await desktopState();await desktop.mouse.move(300,200);await desktop.mouse.down();await desktop.mouse.move(360,230);await desktop.mouse.up();
  await desktop.mouse.wheel(0,-200);await desktop.keyboard.down('w');await desktop.evaluate(()=>window.app.tick(60));await desktop.keyboard.up('w');
  after=await desktopState();assert(after.yaw<before.yaw);assert(after.fov<before.fov);assert(distance(before.p,after.p)>.5);
  assert.deepEqual(errors,[]);console.log('Desktop: mouse look, wheel zoom and keyboard movement passed.');
} finally { await browser.close(); }
