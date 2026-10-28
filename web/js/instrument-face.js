// Reference-drawn US instrument face. Coordinates follow the supplied 800 × 221
// cluster photograph; textures are rasterized at 4096 pixels, not enlarged photos.
export const FACE_W = .536, FACE_H = .148;
export const CW = 4096, CH = Math.round(CW * FACE_H / FACE_W);
export const FONT = '"Barlow Semi Condensed", "Arial Narrow", Arial, sans-serif';
const gauge = (cx, cy, R, min, max, a0, a1) => ({ cx, cy, R, min, max, a0, a1,
  x: (cx / 800 - .5) * FACE_W, y: (.5 - cy / 221) * FACE_H, r: R / 800 * FACE_W });
export const GAUGES = {
  speedo: gauge(301, 115, 82, 0, 85, 235, -35),
  tach: gauge(506, 115, 84, 0, 80, 220, -40),
  volts: gauge(179, 52, 48, 8, 18, 245, 135),
  temp: gauge(179, 162, 55, 100, 260, 225, 145),
  oil: gauge(631, 49, 48, 0, 80, -50, 50),
  fuel: gauge(637, 153, 49, 0, 1, -50, 50),
};
export const LAMPS = {
  brake: { x: 751, y: 198, color: '#f64c35', text: 'BRAKE' },
  oil: { x: 751, y: 77, color: '#f64c35', icon: 'oil' },
  charge: { x: 751, y: 117, color: '#f64c35', icon: 'batt' },
  door: { x: 53, y: 187, color: '#f64c35', icon: 'door' },
  turnL: { x: 246, y: 18, color: '#71ed86', icon: 'left', small: true },
  turnR: { x: 568, y: 18, color: '#71ed86', icon: 'right', small: true },
  high: { x: 374, y: 18, color: '#5a9eff', icon: 'beam', small: true },
  fuel: { x: 751, y: 157, color: '#ffbd45', icon: 'pump' },
};
export const angle = (g, v) => (g.a0 + (g.a1 - g.a0) * Math.min(1, Math.max(0, (v-g.min)/(g.max-g.min)))) * Math.PI / 180;
function text(c, s, x, y, size, color = '#e0e2db', weight = 500) {
  c.fillStyle = color; c.font = `${weight} ${size}px ${FONT}`;
  c.textAlign = 'center'; c.textBaseline = 'middle'; c.fillText(s, x, y);
}
function line(c, x, y, xx, yy, color, width = 1) {
  c.strokeStyle = color; c.lineWidth = width; c.beginPath(); c.moveTo(x,y); c.lineTo(xx,yy); c.stroke();
}
export function setup(c) { c.setTransform(CW/800, 0, 0, CH/221, 0, 0); }
export function icon(c, type, x, y, size, color) {
  c.save(); c.translate(x,y); c.scale(size/24,size/24);
  c.fillStyle = c.strokeStyle = color; c.lineWidth = 1.5; c.lineJoin = 'round';
  if (type === 'left' || type === 'right') {
    c.scale(type === 'left' ? 1 : -1, 1);
    c.beginPath(); c.moveTo(-10,0); c.lineTo(-2,-6); c.lineTo(-2,-2); c.lineTo(10,-2); c.lineTo(10,2); c.lineTo(-2,2); c.lineTo(-2,6); c.closePath(); c.stroke();
  } else if (type === 'batt') {
    c.strokeRect(-10,-5,20,12); c.fillRect(-8,-8,4,3); c.fillRect(4,-8,4,3);
    line(c,-7,1,-3,1,color); line(c,3,1,7,1,color); line(c,5,-1,5,3,color);
  } else if (type === 'oil') {
    c.beginPath(); c.moveTo(-10,-2); c.lineTo(-7,5); c.lineTo(3,5); c.lineTo(10,-5); c.lineTo(3,-1); c.lineTo(0,-4); c.lineTo(-5,-4); c.lineTo(-5,-7); c.lineTo(-1,-7); c.stroke();
    c.beginPath(); c.arc(10,5,1.4,0,Math.PI*2); c.fill();
  } else if (type === 'pump') {
    c.strokeRect(-8,-9,10,18); c.strokeRect(-6,-7,6,6);
    line(c,-10,10,4,10,color,2);
    c.beginPath(); c.moveTo(2,-2); c.lineTo(7,0); c.lineTo(7,7); c.quadraticCurveTo(11,12,11,5); c.lineTo(11,-5); c.lineTo(7,-9); c.stroke();
  } else if (type === 'beam') {
    c.beginPath(); c.moveTo(0,-7); c.bezierCurveTo(14,-7,14,7,0,7); c.closePath(); c.stroke();
    for(let i=-2;i<=2;i++)line(c,-11,i*3,-3,i*3,color);
  } else if (type === 'temp') {
    c.beginPath(); c.roundRect(-3,-10,6,14,2); c.stroke();
    c.beginPath(); c.arc(0,5,4,0,Math.PI*2); c.fill();
    for(let i=0;i<2;i++) { c.beginPath(); c.moveTo(-12,9+i*4); c.bezierCurveTo(-7,5+i*4,-5,13+i*4,0,9+i*4); c.bezierCurveTo(5,5+i*4,7,13+i*4,12,9+i*4); c.stroke(); }
  } else if(type === 'door') {
    c.beginPath(); c.moveTo(-11,7); c.lineTo(-10,0); c.lineTo(-6,-5); c.lineTo(5,-5); c.lineTo(10,0); c.lineTo(11,7); c.closePath(); c.stroke();
    line(c,-7,-8,-11,-12,color); line(c,-5,-8,5,-8,color); line(c,-8,1,8,1,color);
  } else if(type === 'belt') {
    c.beginPath(); c.arc(0,-7,3,0,Math.PI*2); c.fill();
    line(c,0,-3,0,7,color,4); line(c,-6,9,0,3,color,3); line(c,0,3,6,9,color,3); line(c,-7,4,6,-4,color,2);
  }
  c.restore();
}
export function drawDial(c, key, g, glow = false) {
  const {cx,cy,R} = g, white = glow ? '#b6c4b6' : '#e4e5de', orange = '#e97132', blue = glow ? '#7ec2c4' : '#72a7b8';
  const tick = (v, outer, length, width, color=white) => {
    const a=angle(g,v), x=Math.cos(a),y=-Math.sin(a);
    line(c,cx+x*R*outer,cy+y*R*outer,cx+x*R*(outer-length),cy+y*R*(outer-length),color,width);
  };
  const num=(v,s,rr,size,col=white)=>{const a=angle(g,v);text(c,s,cx+Math.cos(a)*R*rr,cy-Math.sin(a)*R*rr,size,col,500);};
  if(key==='speedo') {
    for(let v=0;v<=85;v+=5)tick(v,.85,v%10===5?.13:.085,v%10===5?3.2:1.8);
    for(let v=5;v<=85;v+=10)num(v,String(v),1.04,18,v===55?orange:white);
    for(let k=20;k<=140;k+=20){tick(k/1.609344,.63,.045,2.6,blue);num(k/1.609344,String(k),.51,10,blue);}
    text(c,'km/h',cx,182,11,blue);text(c,'MPH',cx,197,14,white,600);
  } else if(key==='tach') {
    for(let v=0;v<=80;v+=5)tick(v,.86,v%10===0?.13:.075,v%10===0?3.2:1.8,v>=65?orange:white);
    for(let v=0;v<=80;v+=10)num(v,String(v),1.05,18,v>=70?orange:white);
    text(c,'RPM/100',cx,186,14,white,600);
  } else {
    if(key==='volts') {
      for(const v of [8,10.5,13,15.5,18])tick(v,.83,v===13?.17:.13,3,v===13?white:orange);
      for(const v of [8,13,18])num(v,String(v),1.07,10,v===13?white:orange);
      text(c,'VOLTS',169,19,13,white);icon(c,'batt',177,38,15,white);
    } else if(key==='temp') {
      for(const v of [100,140,180,220,260])tick(v,.80,.15,3,v>=240?orange:white);
      for(const v of [100,220,260])num(v,String(v),1.02,11,v===260?orange:white);
      text(c,'TEMP',171,125,13,white);text(c,'°F',171,203,11,white);icon(c,'temp',177,147,14,white);
    } else if(key==='oil') {
      for(const v of [0,20,40,60,80])tick(v,.77,.14,2.4);
      num(0,'0',1.01,10);num(80,'80',1.01,10);
      text(c,'OIL',627,22,12,white);icon(c,'oil',632,40,16,white);text(c,'PSI',627,88,11,white);
    } else {
      for(const v of [0,.25,.5,.75,1])tick(v,.77,.15,2.4);
      num(0,'0',1.02,10);num(.5,'½',1.02,13);num(1,'4/4',1.02,12);
      text(c,'FUEL',627,130,13,white);icon(c,'pump',635,147,14,white);
      text(c,'UNLEADED',632,198,10,white);text(c,'FUEL ONLY',632,211,10,white);
    }
  }
}
export function drawOdometer(c, miles, trip, glow = false) {
  const drum=(value,digits,x,y,w,h)=>{
    c.fillStyle='#020303';c.fillRect(x-2,y-2,w*digits+3,h+4);
    for(let i=0;i<digits;i++){
      const v=value/10**(digits-1-i),digit=Math.floor(v)%10,roll=i===digits-1?v%1:0;
      const xx=x+i*w,last=i===digits-1;
      c.save();c.beginPath();c.rect(xx,y,w-1,h);c.clip();
      const grad=c.createLinearGradient(0,y,0,y+h);grad.addColorStop(0,last?'#66665d':'#070808');grad.addColorStop(.5,last?'#d5d3c1':'#191b1a');grad.addColorStop(1,last?'#737369':'#050606');
      c.fillStyle=glow?'#000':grad;c.fillRect(xx,y,w-1,h);
      c.font=`400 ${h*.92}px "IBM Plex Mono", monospace`;c.textAlign='center';c.textBaseline='middle';c.fillStyle=last?(glow?'#222':'#20231f'):(glow?'#b6c4b6':'#deded1');
      c.fillText(String(digit),xx+w/2,y+h/2-roll*h);c.fillText(String((digit+1)%10),xx+w/2,y+h*1.5-roll*h);c.restore();
    }
  };
  drum(miles*10,6,277,84,8,14);drum(trip*10,4,285,137,8,13);
}
export function drawFace(c,miles,trip) {
  setup(c);c.fillStyle='#0b0d0d';c.fillRect(0,0,800,221);
  // Individual satin-black face panels, with recessed joins instead of circular bezels.
  for(const [x,y,w,h]of [[0,0,104,221],[105,0,99,109],[105,110,99,111],[205,0,199,221],[405,0,199,221],[605,0,99,109],[605,110,99,111],[705,0,95,221]]) {
    const grad=c.createLinearGradient(x,y,x+w,y+h);grad.addColorStop(0,'#222525');grad.addColorStop(.5,'#171919');grad.addColorStop(1,'#101212');c.fillStyle=grad;c.fillRect(x+1,y+1,w-2,h-2);
    line(c,x+1,y+1,x+w-2,y+1,'#303232',.65);
  }
  // Same vector logotype used by the procedural car's grille badge.
  const logo = [
    [[-.5,.13],[-.21,.13],[-.18,.1],[-.18,-.1],[-.21,-.13],[-.5,-.13],[-.5,-.055],[-.265,-.055],[-.265,.055],[-.5,.055]],
    [[-.155,.13],[.135,.13],[.165,.1],[.165,-.13],[.085,-.13],[.085,.06],[.045,.06],[.045,-.13],[-.035,-.13],[-.035,.06],[-.075,.06],[-.075,-.13],[-.155,-.13]],
    [[.5,.13],[.22,.13],[.19,.1],[.19,-.1],[.22,-.13],[.5,-.13],[.5,-.055],[.275,-.055],[.275,.055],[.5,.055]],
  ];
  c.fillStyle='#c8cdcd';
  for(const p of logo){c.beginPath();p.forEach(([x,y],i)=>c[i?'lineTo':'moveTo'](53+x*66,55-y*50));c.closePath();c.fill();}
  text(c,'LAMBDA',751,37,8,'#93988d',600);
  for(const [k,g]of Object.entries(GAUGES))drawDial(c,k,g);
  drawOdometer(c,miles,trip);
  for(const [k,L]of Object.entries(LAMPS))drawLamp(c,k,false);
  drawLamp(c,'high',false,438);
  c.fillStyle='#1f1818';c.fillRect(26,132,55,26);icon(c,'belt',53,145,19,'#655e56');
  // Mechanical trip reset, below and left of the speedometer spindle.
  c.fillStyle='#050606';c.beginPath();c.ellipse(244,174,7,6,0,0,Math.PI*2);c.fill();
  c.strokeStyle='#424545';c.lineWidth=1;c.stroke();
}
export function drawLamp(c,key,on,xOverride) {
  const L=LAMPS[key],x=xOverride??L.x,y=L.y;
  if(!on){c.fillStyle=L.small?'#0b0e0d':'#211819';c.fillRect(x-(L.small?14:28),y-(L.small?7:13),L.small?28:56,L.small?14:26);}
  const color=on?L.color:'#666c62';
  if(L.text)text(c,L.text,x,y,9,color,600);else icon(c,L.icon,x,y,L.small?17:22,color);
}
