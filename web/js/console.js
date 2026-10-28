// Reference-drawn HVAC fascia and molded centre-console controls.
// Dimensions are metres in the donor rig; artwork uses a 1000 x 530 design grid.
import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';
import { FONT } from './instrument-face.js';

const INK = '#d4d2bd';
const texture = (w, h, draw) => {
  const c = document.createElement('canvas'); c.width=w; c.height=h;
  draw(c.getContext('2d'));
  const t = new THREE.CanvasTexture(c); t.colorSpace=THREE.SRGBColorSpace; t.anisotropy=8;
  return t;
};
function label(c, text, x, y, size=17, align='center') {
  c.fillStyle=INK; c.font=`500 ${size}px ${FONT}`; c.textAlign=align; c.textBaseline='middle'; c.fillText(text,x,y);
}
function line(c, points, width=2) {
  c.lineWidth=width; c.beginPath(); points.forEach(([x,y],i)=>i?c.lineTo(x,y):c.moveTo(x,y)); c.stroke();
}
function icon(c, name, x, y, size=24, color=INK) {
  c.save(); c.translate(x,y); c.scale(size/32,size/32); c.strokeStyle=color; c.fillStyle=color; c.lineJoin='round'; c.lineCap='round'; c.lineWidth=2;
  if(name==='hazard') {
    for(const r of [16,10]) { c.beginPath(); c.moveTo(0,-r); c.lineTo(r*.9,r*.7); c.lineTo(-r*.9,r*.7); c.closePath(); c.stroke(); }
  } else if(name==='headlamp') {
    c.beginPath(); c.moveTo(-3,-11); c.bezierCurveTo(18,-13,18,13,-3,11); c.closePath(); c.stroke();
    for(let y=-10;y<=10;y+=5)line(c,[[-15,y],[-7,y]]);
  } else if(name==='snow') {
    for(let i=0;i<6;i++) {c.rotate(Math.PI/3);line(c,[[0,0],[0,-13]],3);line(c,[[-4,-8],[0,-5],[4,-8]],2);}
  } else if(name==='defrost'||name==='rearDefrost') {
    line(c,name==='defrost'?[[-14,10],[-17,-10],[0,-14],[17,-10],[14,10],[-14,10]]:[[-16,11],[-16,-12],[16,-12],[16,11],[-16,11]]);
    for(const x of [-8,0,8]) {line(c,[[x,7],[x,-6]]);line(c,[[x-3,-2],[x,-6],[x+3,-2]]);}
  } else if(name==='window') {
    line(c,[[-13,9],[-12,-10],[12,-10],[13,9],[-13,9]]);
    line(c,[[-8,4],[8,4]]); line(c,[[0,-5],[0,1]]);line(c,[[-3,-2],[0,-5],[3,-2]]);
  } else if(name==='fan') {
    c.beginPath();c.arc(0,0,3,0,Math.PI*2);c.fill();
    for(let i=0;i<4;i++){c.rotate(Math.PI/2);c.beginPath();c.moveTo(2,-2);c.bezierCurveTo(18,-18,18,7,4,3);c.closePath();c.fill();}
  } else if(name==='air') {
    for(let y=-8;y<=8;y+=8){c.beginPath();c.moveTo(-14,y);c.bezierCurveTo(-4,y-6,4,y+6,10,y);c.stroke();}line(c,[[14,-12],[14,12]]);
  }
  c.restore();
}

function hvacArtwork(c, glow=false) {
  c.setTransform(2,0,0,2,0,0); c.fillStyle=glow?'#000':'#151714';c.fillRect(0,0,1000,530);
  if(!glow) {
    let s=71;
    for(let i=0;i<26000;i++){s=(Math.imul(s,1664525)+1013904223)>>>0;const x=s%1000;s=(Math.imul(s,1664525)+1013904223)>>>0;c.fillStyle=i%2?'#ffffff05':'#0000000a';c.fillRect(x,s%530,.7,.7);}
    c.strokeStyle='#3c3f36'; c.lineWidth=1; c.strokeRect(2,2,996,526);
  }
  // Mode dial: the left-hand legends and right-hand pictograms are separate arcs.
  for(const [s,x,y] of [['DEFROST',382,179],['HEATER',383,218],['VENT',389,258],['BI-LEVEL',407,298],['NORM',437,333],['MAX',484,367],['OFF',543,367]]) {
    label(c,s,x-8,y,17,'right');c.fillStyle=INK;c.beginPath();c.arc(x,y,2.8,0,Math.PI*2);c.fill();
  }
  label(c,'0',499,62,23);icon(c,'snow',548,70,24,'#367aa3');icon(c,'snow',591,92,24);
  c.fillStyle='#367aa3';c.fillRect(614,119,24,8);c.fillStyle='#a33a2b';c.fillRect(614,130,24,8);
  icon(c,'air',644,169,26);c.fillStyle=INK;c.beginPath();c.moveTo(636,198);c.lineTo(661,198);c.lineTo(648,223);c.fill();
  icon(c,'defrost',643,254,27);
  // Temperature arc ends match the photographed physical knob, with an ivory outline.
  const arc=(r,color,start,end,width)=>{c.strokeStyle=color;c.lineWidth=width;c.beginPath();c.arc(207,395,r,start*Math.PI/180,end*Math.PI/180);c.stroke();};
  arc(121,INK,145,377,12);arc(121,'#a52f25',145,278,7);arc(121,'#326b99',278,377,7);
  label(c,'HEAT',99,482,16);label(c,'COOL',323,444,16);
  for(const [s,x,y]of [['0',790,270],['1',839,279],['2',882,309],['3',938,382],['4',921,447]])label(c,s,x,y,24);
  icon(c,'fan',922,333,27);
  // Unlit warning legends are muted red, not permanently glowing lamps.
  if(!glow) {
    c.fillStyle='#713b31';c.font=`500 16px ${FONT}`;c.textAlign='center';
    for(const [s,x,y]of [['COOLING',401,431],['FAN FAIL',401,450],['LOCK',639,431],['DOORS',639,450],['REAR DEF.',520,482]])c.fillText(s,x,y);
    c.fillStyle='#5e2d20';c.fillRect(493,421,54,34);icon(c,'rearDefrost',520,439,22);
  }
}

function helpers() {
  const plastic=new THREE.MeshStandardMaterial({color:0x20221e,roughness:.54,metalness:.03});
  const edge=new THREE.MeshStandardMaterial({color:0x353830,roughness:.42,metalness:.08});
  const recess=new THREE.MeshStandardMaterial({color:0x050605,roughness:.95});
  const ivory=new THREE.MeshStandardMaterial({color:0xc7c0a1,roughness:.65});
  const chrome=new THREE.MeshStandardMaterial({color:0x9da39e,roughness:.25,metalness:.88});
  const grain=texture(256,256,c=>{
    const p=c.createImageData(256,256);let s=47;
    for(let i=0;i<p.data.length;i+=4){s=(Math.imul(s,1664525)+1013904223)>>>0;const v=112+(s>>>27);p.data[i]=p.data[i+1]=p.data[i+2]=v;p.data[i+3]=255;}c.putImageData(p,0,0);
  });
  grain.colorSpace=THREE.NoColorSpace;
  plastic.bumpMap=grain;plastic.bumpScale=.00010;
  function mesh(parent,geometry,material,x=0,y=0,z=0) {const m=new THREE.Mesh(geometry,material);m.position.set(x,y,z);parent.add(m);return m;}
  function box(parent,w,h,d,x,y,z,material=plastic,r=.0008) {
    return mesh(parent,new RoundedBoxGeometry(w,h,d,2,Math.min(r,w/3,h/3,d/3)),material,x,y,z);
  }
  function cylinder(parent,r,d,x,y,z,material=plastic) {
    const m=mesh(parent,new THREE.CylinderGeometry(r,r,d,64),material,x,y,z);m.rotation.x=Math.PI/2;return m;
  }
  function torus(parent,r,t,x,y,z,material=edge) {return mesh(parent,new THREE.TorusGeometry(r,t,8,64),material,x,y,z);}
  function plane(parent,w,h,x,y,z,map,name,emissive=false) {
    const mat=new THREE.MeshStandardMaterial({map,roughness:.64,metalness:.03,transparent:true,depthWrite:false,
      emissive:emissive?0xffffff:0,emissiveMap:emissive?map:null,emissiveIntensity:0});
    const m=mesh(parent,new THREE.PlaneGeometry(w,h),mat,x,y,z);m.name=name;return m;
  }
  return {plastic,edge,recess,ivory,chrome,mesh,box,cylinder,torus,plane};
}

// Freeze only geometry sharing one material. The console adds a handful of draw
// calls rather than one per vent slat, rib or molded edge. Live materials stay live.
function batch(group) {
  group.updateMatrixWorld(true); const inv=group.matrixWorld.clone().invert(), buckets=new Map();
  group.traverse(o=>{
    if(!o.isMesh)return;
    const g=o.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv,o.matrixWorld));
    const key=o.material; if(!buckets.has(key))buckets.set(key,[]);buckets.get(key).push(g);
  });
  group.traverse(o=>{if(o.isMesh)o.geometry.dispose();});group.clear();
  for(const [mat,geos]of buckets) {
    const flat=geos.map(g=>g.index?g.toNonIndexed():g);
    const geometry=mergeGeometries(flat);
    const m=new THREE.Mesh(geometry,mat);m.name=group.name+'Surface';group.add(m);
    flat.forEach((g,i)=>{if(g!==geos[i])g.dispose();});
    geos.forEach(g=>g.dispose());
  }
}

function mount(body,name,x,y,z,tilted=true) {
  const g=new THREE.Group();g.name=name;g.position.set(x,z,-y);
  g.quaternion.setFromRotationMatrix(new THREE.Matrix4().makeBasis(
    new THREE.Vector3(0,0,1),new THREE.Vector3(tilted ? .224 : 1,tilted ? .97459 : 0,0).normalize(),
    new THREE.Vector3(tilted ? -.97459 : 0,tilted ? .224 : 1,0).normalize()));
  body.add(g);return g;
}

export function createConsole(body, shifter) {
  const h=helpers(), {plastic,edge,recess,ivory,chrome,box,cylinder,torus,plane,mesh}=h;
  const vinyl=texture(128,128,c=>{
    const p=c.createImageData(128,128);let s=109;
    for(let i=0;i<p.data.length;i+=4){s=(Math.imul(s,1664525)+1013904223)>>>0;const v=80+(s>>>25);p.data[i]=p.data[i+1]=p.data[i+2]=v;p.data[i+3]=255;}c.putImageData(p,0,0);
  });
  vinyl.colorSpace=THREE.NoColorSpace;vinyl.wrapS=vinyl.wrapT=THREE.RepeatWrapping;
  body.traverse(o=>{
    if(!o.isMesh||o.material.name!=='Donor_ConsoleTrim')return;
    // The retained deck has no printed atlas anymore. Give its grain a physical
    // scale instead of stretching a tiny atlas island over the whole console.
    const p=o.geometry.attributes.position,uv=new Float32Array(p.count*2);
    for(let i=0;i<p.count;i++){uv[i*2]=p.getX(i)*28;uv[i*2+1]=p.getZ(i)*28;}
    o.geometry.setAttribute('uv',new THREE.BufferAttribute(uv,2));
    o.material.bumpMap=vinyl;o.material.bumpScale=.00045;o.material.needsUpdate=true;
  });
  const fascia=mount(body,'DetailedHVAC',.354,.0107,.5635);
  const map=texture(2000,1060,c=>hvacArtwork(c));
  const glow=texture(2000,1060,c=>hvacArtwork(c,true));
  box(fascia,.200,.106,.005,0,0,-.0025);
  const faceMaterial=new THREE.MeshStandardMaterial({map,roughness:.77,emissive:0xffe6b8,emissiveMap:glow,emissiveIntensity:0});
  mesh(fascia,new THREE.PlaneGeometry(.200,.106),faceMaterial,0,0,.0003);
  const px=x=>(x-500)*.0002, py=y=>(265-y)*.0002;
  function dial(x,y,angle) {
    const g=new THREE.Group();g.position.set(px(x),py(y),0);g.rotation.z=angle;fascia.add(g);
    cylinder(g,.0218,.002,0,0,.0005,recess);torus(g,.0207,.0006,0,0,.002,edge);
    // Lathed dish gives a rounded rim, recessed face and soft inward shoulder.
    const points=[[0,.002],[.013,.002],[.017,.003],[.0193,.005],[.020,.007],[.0197,.008],[.019,.0084],[.018,.006],[.015,.004],[0,.0035]].map(p=>new THREE.Vector2(...p));
    const bowl=mesh(g,new THREE.LatheGeometry(points,64),plastic);
    // Lathe +Y becomes local +Z, towards the cabin.
    bowl.rotation.x=Math.PI/2;
    box(g,.0058,.034,.008,0,0,.009,plastic,.002);
    box(g,.0018,.010,.0007,0,.0105,.0133,ivory,.0003);
    box(g,.0013,.005,.0006,0,-.0115,.0132,ivory,.0003);
  }
  dial(500,220,0);dial(207,395,1.12);dial(802,390,-.42);
  for(const [name,x,y]of [['headlamp',178,130],['hazard',814,130]]) {
    cylinder(fascia,.017,.002,px(x),py(y),.001,recess);
    const shape=[[0,.001],[.011,.001],[.014,.003],[.0155,.007],[.0147,.011],[.011,.013],[.0095,.011],[0,.011]].map(p=>new THREE.Vector2(...p));
    const m=mesh(fascia,new THREE.LatheGeometry(shape,64),plastic,px(x),py(y),0);m.rotation.x=Math.PI/2;
    cylinder(fascia,.0093,.0003,px(x),py(y),.0111,recess);
    const t=texture(256,256,c=>{c.clearRect(0,0,256,256);icon(c,name,128,128,158);});
    plane(fascia,.016,.016,px(x),py(y),.0115,t,name+'Icon');
  }
  batch(fascia);

  const vents=mount(body,'DetailedCentreVents',.378,.0107,.6995);
  box(vents,.204,.060,.008,0,0,-.004,recess,.002);
  for(const x of [-.051,.051]) {
    box(vents,.099,.057,.004,x,0,0,edge,.002);
    box(vents,.095,.053,.004,x,0,.001,plastic,.002);
    box(vents,.085,.048,.002,x,0,.003,recess,.002);
    for(const dx of [-.023,0,.023])box(vents,.0011,.046,.004,x+dx,0,.001,plastic);
    for(let j=0;j<5;j++) {
      const slat=box(vents,.083,.002,.007,x,(j-2)*.0085,.0065,plastic,.0006);slat.rotation.x=-.14;
    }
    box(vents,.013,.0045,.003,x,0,.011,plastic);
    for(let j=0;j<12;j++)box(vents,.00035,.0035,.0007,x+(j-5.5)*.00095,0,.0128,edge,.0001);
    const side=x+Math.sign(x)*.046;
    box(vents,.005,.037,.004,side,0,.004,plastic);
    for(let j=0;j<20;j++)box(vents,.004,.0006,.001,side,(j-9.5)*.0015,.0065,edge,.0002);
  }
  batch(vents);

  const lower=mount(body,'DetailedLowerConsole',0,0,0,false);
  // In the horizontal frame: u=-sourceY, v=sourceX, depth=sourceZ.
  cylinder(lower,.022,.003,-.063,.263,.518,recess);
  torus(lower,.020,.0008,-.063,.263,.520,chrome);
  const lighterProfile=[[0,0],[.018,0],[.020,.004],[.020,.007],[.019,.010],[.018,.010],[.016,.007],[0,.006]].map(p=>new THREE.Vector2(...p));
  const lighter=mesh(lower,new THREE.LatheGeometry(lighterProfile,64),plastic,-.063,.263,.520);lighter.rotation.x=Math.PI/2;
  torus(lower,.0188,.0004,-.063,.263,.530,edge);
  box(lower,.0045,.031,.006,-.063,.263,.531,plastic,.0015);
  // Smoked clock lens in the recess alongside the lighter; live digits attach
  // to ClockFace_Pivot, so time and ignition behavior remain in ConsoleDisplays.
  box(lower,.070,.038,.005,.036,.273,.516,recess,.002);
  box(lower,.065,.033,.002,.036,.273,.519,edge,.002);
  box(lower,.061,.029,.001,.036,.273,.520,recess,.001);
  for(const x of [.016,.056])cylinder(lower,.0016,.001,x,.260,.521,plastic);
  // Five fitted rockers: window switches flank the heated rear-window switch;
  // the outer two locations are blanking plates, as on the donor console.
  box(lower,.190,.060,.014,-.012,-.055,.521,recess,.002);
  for(let i=0;i<5;i++) {
    const x=-(.0847-i*.0366);
    box(lower,.0345,.054,.004,x,-.055,.529,edge,.001);
    const rocker=box(lower,.030,.048,.008,x,-.055,.535,plastic,.002);rocker.rotation.x=.075;
    for(const dy of [-.020,.020])box(lower,.024,.0008,.0005,x,-.055+dy,.539,edge,.0002);
    if(i===1||i===2||i===3) {
      const t=texture(256,256,c=>{c.clearRect(0,0,256,256);icon(c,i===2?'rearDefrost':'window',128,128,126);});
      const p=plane(lower,.017,.017,x,-.054,.5397,t,'ConsoleSwitchIcon');p.rotation.x=.075;
    }
  }
  // Recessed mirror joystick with raised arrows and L/R selector legend.
  box(lower,.049,.039,.005,.049,.017,.532,recess,.002);
  box(lower,.039,.031,.004,.049,.017,.535,plastic,.002);
  cylinder(lower,.010,.004,.049,.020,.539,plastic);
  box(lower,.008,.011,.004,.049,.020,.543,plastic,.002);
  const arrows=texture(512,384,c=>{
    c.clearRect(0,0,512,384);label(c,'L',110,325,36);label(c,'R',398,325,36);
    c.fillStyle=INK;
    for(const [x,y,a]of [[256,45,0],[256,265,Math.PI],[70,155,-Math.PI/2],[442,155,Math.PI/2]]) {
      c.save();c.translate(x,y);c.rotate(a);c.beginPath();c.moveTo(0,-12);c.lineTo(10,7);c.lineTo(-10,7);c.fill();c.restore();
    }
  });
  plane(lower,.039,.029,.049,.017,.5372,arrows,'MirrorControlLegend');
  // Ashtray: actual recessed lid, narrow border and a ribbed finger grip.
  box(lower,.091,.164,.003,.0333,-.1903,.5465,recess,.003);
  box(lower,.086,.159,.002,.0333,-.1903,.548,edge,.003);
  box(lower,.082,.155,.002,.0333,-.1903,.549,plastic,.002);
  for(let i=0;i<10;i++)box(lower,.072,.0012,.0008,.0333,-.254+i*.008,.5504,edge,.0003);
  box(lower,.073,.015,.004,.0333,-.130,.552,plastic,.0015);
  for(let i=0;i<5;i++)box(lower,.001,.012,.0007,.0333+(i-2)*.011,-.130,.5543,edge,.0003);
  batch(lower);

  if(shifter) {
    const knob=new THREE.Group();knob.name='DetailedGearKnob';knob.position.set(-.0046,.1024,.0013);shifter.add(knob);
    const ball=mesh(knob,new THREE.SphereGeometry(.0232,48,32),plastic);ball.scale.y=.90;
    const pattern=texture(512,512,c=>{
      c.clearRect(0,0,512,512);c.strokeStyle=INK;
      line(c,[[126,202],[126,346]],8);line(c,[[256,202],[256,346]],8);line(c,[[386,202],[386,346]],8);line(c,[[126,274],[386,274]],8);
      for(const [s,x,y]of [['1',126,157],['3',256,157],['5',386,157],['2',126,397],['4',256,397],['R',386,397]])label(c,s,x,y,64);
    });
    // Conform the white engraving to the crown rather than floating a flat card.
    const cap=new THREE.SphereGeometry(.02324,48,12,0,Math.PI*2,0,.42);
    const p=cap.attributes.position,uv=cap.attributes.uv;
    for(let i=0;i<p.count;i++)uv.setXY(i,.5+p.getZ(i)/.019,.5+p.getX(i)/.019);
    const marking=mesh(knob,cap,new THREE.MeshStandardMaterial({map:pattern,transparent:true,depthWrite:false,roughness:.54}));marking.scale.y=.90;
  }

  const ready=document.fonts.load('500 40px "Barlow Semi Condensed"').catch(()=>{}).then(()=>{
    hvacArtwork(map.image.getContext('2d'));hvacArtwork(glow.image.getContext('2d'),true);map.needsUpdate=true;glow.needsUpdate=true;
  });
  return {faceTexture:map,glowTexture:glow,faceMaterial,ready,
    update(sim,lights) {faceMaterial.emissiveIntensity=sim.electrics&&lights.panel ? lights.dimmer*.7 : 0;}};
}

// Green VFD clock, using polygons rather than a font that may not be installed.
export function drawClock(c,w,h,hours,minutes,colon) {
  c.setTransform(w/512,0,0,h/200,0,0);c.fillStyle='#000';c.fillRect(0,0,512,200);
  const digits=['abcdef','bc','abged','abgcd','fgbc','afgcd','afgecd','abc','abcdefg','abfgcd'];
  const value=String(hours).padStart(2,' ')+String(minutes).padStart(2,'0');
  for(let i=0;i<4;i++) {
    const x=40+i*106+(i>1?14:0), on=digits[Number(value[i])]||'';
    for(const [id,dx,dy,vertical]of [['a',8,20,0],['b',68,28,1],['c',68,103,1],['d',8,172,0],['e',0,103,1],['f',0,28,1],['g',8,96,0]]) {
      c.save();c.translate(x+dx,dy);if(vertical)c.rotate(Math.PI/2);
      c.fillStyle=value[i]!==' '&&on.includes(id)?'#71dfa5':'#06140c';
      c.beginPath();c.moveTo(6,0);c.lineTo(54,0);c.lineTo(60,5);c.lineTo(54,10);c.lineTo(6,10);c.lineTo(0,5);c.closePath();c.fill();c.restore();
    }
  }
  c.fillStyle=colon?'#71dfa5':'#06140c';c.fillRect(245,64,8,8);c.fillRect(245,128,8,8);
}
