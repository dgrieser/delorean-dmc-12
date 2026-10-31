// Door caps must block views into the cavity at closed, half-open and open poses.
import { chromium } from 'playwright-core';
import assert from 'node:assert/strict';
const browser=await chromium.launch({executablePath:process.env.CHROME||'/usr/bin/google-chrome',args:['--headless=new','--enable-gpu','--ignore-gpu-blocklist','--use-angle=vulkan','--enable-features=Vulkan']});
try {
 const page=await browser.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
 const url=new URL(process.env.URL||'http://localhost:8123/web/');url.searchParams.set('still','1');url.searchParams.set('model','donor');
 await page.goto(url.href);await page.waitForFunction(()=>document.title==='READY',null,{timeout:90000});
 const checks=await page.evaluate(()=>{
  const a=window.app,T=window.THREE,results=[];
  let visors;a.car.root.traverse(o=>{if(o.isMesh&&o.name==='sunvisors')visors=o;});
  if(!visors)throw new Error('Missing fixed sun visors');
  a.car.root.updateMatrixWorld(true);
  const visorMatrix=visors.matrixWorld.clone();
  const dashEnd=a.car.root.getObjectByName('dash_end_cheeks');
  if(!dashEnd)throw new Error('Missing dashboard end trim');
  const dashMatrix=dashEnd.matrixWorld.clone();
  const gaugeLegend=a.car.root.getObjectByName('gauge_legend');
  if(!gaugeLegend)throw new Error('Missing fixed instrument printing');
  const gaugeMatrix=gaugeLegend.matrixWorld.clone();
  // Sightlines through the three background leaks in the reported cabin view.
  const headerCamera=new T.PerspectiveCamera(75,1500/1100,.01,100);
  headerCamera.position.set(-.40,1.05,-.35);headerCamera.lookAt(.55,.69,.02);
  headerCamera.updateMatrixWorld(true);
  for(const side of ['L','R']) {
   let box,jamb;a.car.root.traverse(o=>{
    if(o.isMesh&&o.name==='door_box_'+side)box=o;
    if(o.isMesh&&o.name==='jamb_shell_'+side)jamb=o;
   });
   if(!box)throw new Error('Missing door shell '+side);
   if(!jamb)throw new Error('Missing fixed jamb '+side);
   const header=a.car.root.getObjectByName('header_corner_'+side);
   if(!header)throw new Error('Missing header corner '+side);
   const headerMatrix=header.matrixWorld.clone();
   const panel=a.car[side==='L'?'doorL':'doorR'],sign=side==='L'?1:-1;
   const pull=a.car.root.getObjectByName('DoorPull_'+side+'_Pivot');
   if(!pull)throw new Error('Missing door pull '+side);
   panel.theta=0;panel.apply();a.car.root.updateMatrixWorld(true);
   const pullRest=pull.getWorldQuaternion(new T.Quaternion());
   for(const angle of [0,35,69]) {
    panel.theta=angle*Math.PI/180;panel.apply();a.car.root.updateMatrixWorld(true);
    if(!visors.matrixWorld.equals(visorMatrix))throw new Error('Sun visors moved with door');
    if(!dashEnd.matrixWorld.equals(dashMatrix))throw new Error('Dashboard end trim moved with door');
    if(!gaugeLegend.matrixWorld.equals(gaugeMatrix))throw new Error('Instrument printing became a floating door fragment');
    if(!header.matrixWorld.equals(headerMatrix))throw new Error('Header corner moved with door');
    for(const [x,y]of side==='L'?[[35,170],[31,207]]:[[1480,248]]) {
     const ray=new T.Raycaster();ray.setFromCamera(new T.Vector2(x/1500*2-1,1-y/1100*2),headerCamera);
     if(!ray.intersectObject(header,true).length)throw new Error(`Header leak ${side} at ${angle}°`);
    }
    if(pull.getWorldQuaternion(new T.Quaternion()).angleTo(pullRest)>1e-5)
     throw new Error(`Door pull stopped hanging ${side} at ${angle}°`);
    for(const [anchorName,ballName]of [['StrutBody_','strut_ball_body_'],['StrutDoor_','strut_ball_door_']]) {
     const anchor=a.car.root.getObjectByName(anchorName+side),ball=a.car.root.getObjectByName(ballName+side);
     if(!anchor||!ball)throw new Error('Missing strut mount '+side);
     if(anchor.getWorldPosition(new T.Vector3()).distanceTo(ball.getWorldPosition(new T.Vector3()))>.0001)
      throw new Error(`Detached strut ${side} at ${angle}°`);
    }
    for(const [name,start,direction]of [
     ['sill',[0,.78,.20],[0,0,1]],['rear jamb',[-.3,.78,.55],[-1,0,0]]]) {
     const convert=([x,y,z])=>new T.Vector3(x,z,-y*sign);
     const origin=convert(start).applyMatrix4(jamb.matrixWorld),dir=convert(direction).transformDirection(jamb.matrixWorld);
     results.push({side,angle,name,solid:true,hit:new T.Raycaster(origin,dir,0,.5).intersectObject(jamb,false).length>0});
    }
    for(const [name,start,direction,solid]of [
     ['front',[1,.855,.60],[-1,0,0],true],['rear',[-1,.84,.60],[1,0,0],true],
     ['bottom',[0,.845,.15],[0,0,1],true],['roof',[-.3,.33,1.0],[0,0,1],true],
     ['window',[-.2,.50,.95],[0,1,0],false]]) {
     const convert=([x,y,z])=>new T.Vector3(x,z,-y*sign);
     const origin=convert(start).applyMatrix4(box.matrixWorld),dir=convert(direction).transformDirection(box.matrixWorld);
     const ray=new T.Raycaster(origin,dir,0,1.2);const hits=ray.intersectObject(box,false);
     results.push({side,angle,name,solid,hit:hits.length>0});
    }
   }
  }
  return results;
 });
 for(const c of checks)assert.equal(c.hit,c.solid,`${c.side} ${c.angle}° ${c.name}: ${c.solid?'open cavity':'blocked window'}`);
 assert.deepEqual(errors,[]);console.log('Both doors at 0°, 35°, 69°: struts attached, pulls hanging, cavities and header corners closed, windows clear, visors and dashboard ends fixed.');
}finally{await browser.close();}
