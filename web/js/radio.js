// High-resolution reference-drawn cassette radio face and shallow physical controls.
import * as THREE from 'three';
import { FONT } from './instrument-face.js';

const W = .205, H = .056;
const X = x => (x / 1024 - .5) * W, Y = y => (.5 - y / 280) * H;
function label(c, s, x, y, size = 12, align = 'left') {
  c.font = `600 ${size}px ${FONT}`; c.textAlign = align; c.textBaseline = 'middle'; c.fillStyle = '#c4c8bf'; c.fillText(s, x, y);
}
function drawFace(c) {
  c.setTransform(2,0,0,2,0,0);
  const g = c.createLinearGradient(0,0,0,280); g.addColorStop(0,'#252928'); g.addColorStop(.5,'#171a19'); g.addColorStop(1,'#111413');
  c.fillStyle=g;c.fillRect(0,0,1024,280);
  // Fine paint grain, deterministic and below the contrast of the screen printing.
  let seed=31;
  for(let i=0;i<18000;i++){seed=(Math.imul(seed,1664525)+1013904223)>>>0;const x=seed%1024;seed=(Math.imul(seed,1664525)+1013904223)>>>0;c.fillStyle=i%2?'#ffffff05':'#0000000b';c.fillRect(x,seed%280,.6,.6);}
  c.strokeStyle='#535952';c.lineWidth=1;c.strokeRect(7,7,1010,266);
  c.strokeStyle='#060807';c.lineWidth=3;c.strokeRect(3,3,1018,274);
  c.fillStyle='#070908';c.fillRect(247,33,544,212);c.strokeStyle='#464c46';c.lineWidth=1;c.strokeRect(247,33,544,212);
  label(c,'STEREO CASSETTE',266,49,12);
  c.fillStyle='#020302';c.fillRect(270,61,423,12);c.fillStyle='#3d423d';c.fillRect(270,61,423,1);
  c.fillStyle='#484a40';c.fillRect(277,82,408,87);c.fillStyle='#090c09';c.fillRect(284,87,394,77);
  label(c,'▼ EJECT',70,51,13);
  label(c,'VOL–PWR (outer)',29,235,11);label(c,'TRE–BAL (push/pull)',29,250,11);
  label(c,'MANUAL TUNE',824,33,11);label(c,'AUTO SCAN (push)',824,47,11);label(c,'HOLD (push)',824,61,11);
  label(c,'UP',824,196,10);label(c,'TUNE',827,230,11);label(c,'FADER',827,244,11);
  for(const [s,y]of [['◁',91],['MTL',117],['▶',143]])label(c,s,705,y,11);
  for(const [s,x]of [['LOUD',312],['FM',404],['ST',491],['DX',579],['MEMO',715]]){
    label(c,s,x,182,12,'center');c.fillStyle='#160c08';c.beginPath();c.arc(x-29,182,3,0,Math.PI*2);c.fill();
  }
  for(let i=0;i<6;i++)label(c,String(i+1),305+i*82,215,11,'center');
  label(c,'◀◀',259,238,10,'center');label(c,'▶▶',780,238,10,'center');
}
export function createRadio(pivot, displayTexture) {
  const frame = new THREE.Group(); frame.name='DetailedRadio'; frame.rotation.x=-Math.PI/2; pivot.add(frame);
  const c=document.createElement('canvas');c.width=2048;c.height=560;drawFace(c.getContext('2d'));
  const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=8;
  const faceMat=new THREE.MeshStandardMaterial({map:texture,roughness:.62,metalness:.12});
  const plastic=new THREE.MeshStandardMaterial({color:0x151816,roughness:.48,metalness:.06});
  const trim=new THREE.MeshStandardMaterial({color:0x474b46,roughness:.32,metalness:.7});
  const box=(w,h,d,x,y,z,material=plastic)=>{const m=new THREE.Mesh(new THREE.BoxGeometry(w,h,d),material);m.position.set(x,y,z);frame.add(m);return m;};
  box(W,H,.004,0,0,-.001);
  const face=new THREE.Mesh(new THREE.PlaneGeometry(W,H),faceMat);face.position.z=.0012;face.name='RadioFaceMesh';frame.add(face);
  for(const x of [110,914]) {
    const group=new THREE.Group();group.position.set(X(x),Y(128),.002);frame.add(group);
    const cylinder=(r,depth,z,mat)=>{const m=new THREE.Mesh(new THREE.CylinderGeometry(r,r,depth,64),mat);m.rotation.x=Math.PI/2;m.position.z=z;group.add(m);};
    cylinder(.013,.003,.001,plastic);cylinder(.0115,.010,.007,plastic);
    const ribs = new THREE.InstancedMesh(new THREE.BoxGeometry(.00045,.0010,.009),plastic,48);
    const rib = new THREE.Object3D();
    for(let i=0;i<48;i++){
      const a=i*Math.PI/24;
      rib.position.set(Math.cos(a)*.0115,Math.sin(a)*.0115,.007);rib.rotation.z=a;rib.updateMatrix();
      ribs.setMatrixAt(i,rib.matrix);
    }
    group.add(ribs);
    const rim=new THREE.Mesh(new THREE.TorusGeometry(.0108,.00035,8,64),trim);rim.position.z=.0122;group.add(rim);
    cylinder(.0105,.0008,.0124,plastic);
  }
  const button=(x,y,w=65,h=10)=>{
    box(w/1024*W,h/280*H,.002,X(x),Y(y),.0025);
    box(w/1024*W,.0002,.0003,X(x),Y(y)+h/280*H/2,.0035,trim);
  };
  for(let i=0;i<6;i++)button(305+i*82,231,72,11);
  for(const x of [312,404,491,579,715])button(x,196,67,10);
  for(const y of [91,117,143])button(751,y,40,9);
  for(const x of [259,780])button(x,251,30,8);
  const screenMat=new THREE.MeshStandardMaterial({color:0x20180d,roughness:.24,metalness:.05,
    emissive:0xffffff,emissiveMap:displayTexture,emissiveIntensity:0});
  const screen=new THREE.Mesh(new THREE.PlaneGeometry(374/1024*W,66/280*H),screenMat);
  screen.name='RadioDisplayMesh';screen.position.set(X(481),Y(125),.0018);frame.add(screen);
  const ready=document.fonts.load('600 40px "Barlow Semi Condensed"').catch(() => {}).then(()=>{drawFace(c.getContext('2d'));texture.needsUpdate=true;});
  return {material:screenMat,faceTexture:texture,ready};
}

// Real segmented digits, independent of whether a seven-segment font is installed.
const DIGITS = {0:'abcedf',1:'bc',2:'abged',3:'abgcd',4:'fgbc',5:'afgcd',6:'afgecd',7:'abc',8:'abcdefg',9:'abfgcd'};
export function drawRadioDisplay(c,w,h) {
  c.setTransform(w/1024,0,0,h/256,0,0);c.fillStyle='#000';c.fillRect(0,0,1024,256);
  const segment=(x,y,horizontal,on)=>{
    c.fillStyle=on?'#cd8f46':'#140e06';
    c.beginPath();
    if(horizontal){c.moveTo(x+8,y);c.lineTo(x+77,y);c.lineTo(x+85,y+7);c.lineTo(x+77,y+14);c.lineTo(x+8,y+14);c.lineTo(x,y+7);}
    else{c.moveTo(x+7,y);c.lineTo(x+14,y+8);c.lineTo(x+14,y+77);c.lineTo(x+7,y+85);c.lineTo(x,y+77);c.lineTo(x,y+8);}
    c.closePath();c.fill();
  };
  for(const [digit,x]of [['9',310],['8',470],['5',665]]) {
    const on=DIGITS[digit];
    for(const [id,dx,dy,horiz]of [['a',15,30,true],['b',101,41,false],['c',101,130,false],['d',15,208,true],['e',0,130,false],['f',0,41,false],['g',15,119,true]])segment(x+dx,dy,horiz,on.includes(id));
  }
  c.fillStyle='#cd8f46';c.fillRect(629,207,15,15);
  c.font=`500 43px ${FONT}`;c.textAlign='left';c.textBaseline='middle';c.fillText('FM',66,127);
  c.font=`500 23px ${FONT}`;c.fillText('STEREO',72,195);c.fillText('MHz',823,195);
}
