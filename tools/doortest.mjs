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
  for(const side of ['L','R']) {
   let box;a.car.root.traverse(o=>{if(o.isMesh&&o.name==='door_box_'+side)box=o;});
   if(!box)throw new Error('Missing door shell '+side);
   const panel=a.car[side==='L'?'doorL':'doorR'],sign=side==='L'?1:-1;
   for(const angle of [0,35,69]) {
    panel.theta=angle*Math.PI/180;panel.apply();a.car.root.updateMatrixWorld(true);
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
 assert.deepEqual(errors,[]);console.log('Both doors: front/rear/bottom caps and roof backing block cavity rays at 0°, 35°, 69°; window openings remain clear.');
}finally{await browser.close();}
