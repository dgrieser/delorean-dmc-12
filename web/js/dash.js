// Instrument cluster (Veglia-Borletti style layout of the DMC-12), console clock and radio.
// The dial face is drawn on a canvas (base map + separate illumination/lamp glow map).
import * as THREE from 'three';
import { thinGlass, enhance } from './materials.js';

const FACE_W = 0.536, FACE_H = 0.124;
const PX = 3820;                      // pixels per metre on the face canvas
const CW = Math.round(FACE_W * PX), CH = Math.round(FACE_H * PX);
const FONT = '"Barlow Semi Condensed", "Arial Narrow", "Helvetica Neue", Arial, sans-serif';

// gauge layout in face metres (x to driver's right, y up)
const G = {
  speedo: { x: -0.086, y: 0.000, r: 0.0565, min: 0, max: 85, a0: 225, a1: -30 },
  tach: { x: 0.042, y: 0.000, r: 0.0565, min: 0, max: 80, a0: 225, a1: -30 },
  volts: { x: -0.196, y: 0.0285, r: 0.0275, min: 8, max: 16, a0: 200, a1: 340 - 360 },
  temp: { x: -0.196, y: -0.0285, r: 0.0275, min: 100, max: 260, a0: 200, a1: -20 },
  oil: { x: 0.170, y: 0.0285, r: 0.0275, min: 0, max: 80, a0: 200, a1: -20 },
  fuel: { x: 0.170, y: -0.0285, r: 0.0275, min: 0, max: 1, a0: 200, a1: -20 },
};
G.volts.a1 = -20;
const LAMPS = {
  brake: { col: -1, row: 0, color: '#ff3b2e', text: 'BRAKE' },
  oil: { col: -1, row: 1, color: '#ff3b2e', icon: 'oil' },
  charge: { col: -1, row: 2, color: '#ff3b2e', icon: 'batt' },
  door: { col: -1, row: 3, color: '#ffb02e', text: 'DOOR' },
  turnL: { col: 1, row: 0, color: '#39ff6a', icon: 'left' },
  turnR: { col: 1, row: 1, color: '#39ff6a', icon: 'right' },
  high: { col: 1, row: 2, color: '#3d8bff', icon: 'beam' },
  fuel: { col: 1, row: 3, color: '#ffb02e', icon: 'pump' },
};

const ang = (g, v) => {
  const t = Math.min(1, Math.max(0, (v - g.min) / (g.max - g.min)));
  return (g.a0 + (g.a1 - g.a0) * t) * Math.PI / 180;
};

function px(x) { return (x + FACE_W / 2) * PX; }
function py(y) { return (FACE_H / 2 - y) * PX; }

export class Cluster {
  constructor(pivotNode, lib, options = {}) {
    // glTF converts the pivot's local frame too: its local +Y is the face normal (toward the
    // driver) and local -Z is "up" on the dial. Work in a child frame with +Z = normal, +Y = up.
    const pivot = new THREE.Group();
    pivot.rotation.x = -Math.PI / 2;
    pivotNode.add(pivot);
    // centre the dial in the binnacle window (body coords: x 0.512, y 0.727, z -0.37)
    const body = pivotNode.parent;
    body.updateMatrixWorld(true);
    const want = body.localToWorld(new THREE.Vector3(...(options.center || [0.505, 0.727, -0.37])));
    pivot.position.copy(pivotNode.worldToLocal(want));
    pivot.scale.setScalar(options.scale ?? 1);
    pivot.scale.y *= options.heightScale ?? 1;
    this.pivot = pivot;
    this.base = document.createElement('canvas');
    this.glow = document.createElement('canvas');
    this.base.width = this.glow.width = CW;
    this.base.height = this.glow.height = CH;
    this.mapTex = new THREE.CanvasTexture(this.base);
    this.mapTex.colorSpace = THREE.SRGBColorSpace;
    this.mapTex.anisotropy = 8;
    this.glowTex = new THREE.CanvasTexture(this.glow);
    this.glowTex.colorSpace = THREE.SRGBColorSpace;
    this.mat = new THREE.MeshStandardMaterial({ map: this.mapTex, emissiveMap: this.glowTex, emissive: 0xffffff, emissiveIntensity: 0, roughness: 0.55, metalness: 0 });
    const face = new THREE.Mesh(new THREE.PlaneGeometry(FACE_W, FACE_H), this.mat);
    face.name = 'GaugeFaceMesh';
    pivot.add(face);
    // glass cover
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(FACE_W + 0.01, FACE_H + 0.01),
      thinGlass(new THREE.MeshPhysicalMaterial({ color: 0x222222, roughness: 0.04, metalness: 0 }), 0.05));
    enhance(glass.material);
    glass.position.z = 0.032;
    glass.rotation.x = -0.12;
    pivot.add(glass);
    // needles
    this.needleMat = new THREE.MeshStandardMaterial({ color: 0xff5a1f, emissive: 0xff4a12, emissiveIntensity: 0.15, roughness: 0.4 });
    this.hubMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 0.35, metalness: 0.2 });
    this.needles = {};
    for (const [k, g] of Object.entries(G)) {
      const n = new THREE.Group();
      n.position.set(g.x, g.y, 0.004);
      const L = g.r * 0.92, w0 = g.r > 0.04 ? 0.0024 : 0.0016, w1 = 0.0007;
      const shape = new THREE.Shape();
      shape.moveTo(-L * 0.18, -w0 * 0.9); shape.lineTo(L, -w1); shape.lineTo(L, w1); shape.lineTo(-L * 0.18, w0 * 0.9); shape.closePath();
      const m = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.0012, bevelEnabled: false }), this.needleMat);
      n.add(m);
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(g.r > 0.04 ? 0.0068 : 0.0045, g.r > 0.04 ? 0.0075 : 0.005, 0.004, 24), this.hubMat);
      hub.rotation.x = Math.PI / 2; hub.position.z = 0.003;
      n.add(hub);
      pivot.add(n);
      this.needles[k] = { node: n, g, v: g.min, w: 0 };
    }
    this.lampState = {};
    this.illum = 0;
    this.odo = -1;
    this.fontsReady = false;
    (document.fonts?.load ? document.fonts.load('600 40px "Barlow Semi Condensed"') : Promise.resolve()).finally(() => { this.fontsReady = true; this.drawBase(0, 0); this.drawGlow(); });
    this.drawBase(0, 0);
    this.drawGlow();
  }

  drawDial(c, key, g, opt) {
    const cx = px(g.x), cy = py(g.y), R = g.r * PX;
    c.save();
    // dial bezel ring + subtle depth
    const grd = c.createRadialGradient(cx, cy, R * 0.2, cx, cy, R * 1.08);
    grd.addColorStop(0, '#121314'); grd.addColorStop(1, '#060606');
    c.fillStyle = grd;
    c.beginPath(); c.arc(cx, cy, R * 1.04, 0, Math.PI * 2); c.fill();
    c.strokeStyle = 'rgba(160,165,170,0.25)'; c.lineWidth = R * 0.02;
    c.beginPath(); c.arc(cx, cy, R * 1.03, 0, Math.PI * 2); c.stroke();
    const col = opt.ink;
    const tick = (v, len, w, color = col) => {
      const a = ang(g, v);
      c.strokeStyle = color; c.lineWidth = w;
      c.beginPath();
      c.moveTo(cx + Math.cos(a) * R * 0.95, cy - Math.sin(a) * R * 0.95);
      c.lineTo(cx + Math.cos(a) * R * (0.95 - len), cy - Math.sin(a) * R * (0.95 - len));
      c.stroke();
    };
    const num = (v, txt, rr, size, color = col, weight = 600) => {
      const a = ang(g, v);
      c.fillStyle = color; c.font = `${weight} ${size}px ${FONT}`; c.textAlign = 'center'; c.textBaseline = 'middle';
      c.fillText(txt, cx + Math.cos(a) * R * rr, cy - Math.sin(a) * R * rr);
    };
    const big = g.r > 0.04;
    if (key === 'speedo') {
      for (let v = 0; v <= 85; v += 2.5) tick(v, v % 10 === 0 ? 0.13 : v % 5 === 0 ? 0.085 : 0.05, v % 10 === 0 ? R * 0.022 : R * 0.012);
      for (let v = 10; v <= 80; v += 10) num(v, String(v), 0.68, R * 0.17);
      // km/h inner scale (orange)
      for (let k = 20; k <= 140; k += 20) {
        const v = k / 1.609344;
        num(v, String(k), 0.45, R * 0.085, opt.ink2, 500);
      }
      c.fillStyle = col; c.font = `600 ${R * 0.10}px ${FONT}`; c.textAlign = 'center';
      c.fillText('MPH', cx, cy - R * 0.32);
      c.fillStyle = opt.ink2; c.font = `500 ${R * 0.075}px ${FONT}`;
      c.fillText('km/h', cx, cy - R * 0.20);
    } else if (key === 'tach') {
      for (let v = 0; v <= 80; v += 2.5) tick(v, v % 10 === 0 ? 0.13 : v % 5 === 0 ? 0.085 : 0.05, v % 10 === 0 ? R * 0.022 : R * 0.012, v >= 60 ? '#ff3b2e' : col);
      for (let v = 0; v <= 80; v += 10) num(v, String(v), 0.70, R * 0.17, v >= 60 ? '#ff3b2e' : col);
      // red arc
      c.strokeStyle = '#d81e14'; c.lineWidth = R * 0.05;
      c.beginPath(); c.arc(cx, cy, R * 0.97, -ang(g, 60), -ang(g, 80), false); c.stroke();
      c.fillStyle = col; c.font = `600 ${R * 0.09}px ${FONT}`; c.textAlign = 'center';
      c.fillText('RPM/100', cx, cy + R * 0.40);
    } else {
      const labels = { volts: ['8', '12', '16', 'VOLTS'], temp: ['100', '180', '260', 'TEMP'], oil: ['0', '40', '80', 'OIL'], fuel: ['E', '½', 'F', 'FUEL'] };
      const L = labels[key];
      const vals = [g.min, (g.min + g.max) / 2, g.max];
      for (let i = 0; i <= 8; i++) {
        const v = g.min + (g.max - g.min) * i / 8;
        const red = (key === 'temp' && i >= 7) || (key === 'fuel' && i === 0) || (key === 'volts' && (i <= 1 || i === 8));
        tick(v, i % 4 === 0 ? 0.20 : 0.12, R * (i % 4 === 0 ? 0.045 : 0.028), red ? '#ff3b2e' : col);
      }
      vals.forEach((v, i) => num(v, L[i], 0.56, R * 0.25));
      c.fillStyle = col; c.font = `600 ${R * 0.19}px ${FONT}`; c.textAlign = 'center';
      c.fillText(L[3], cx + R * 0.05, cy + R * 0.48);
      if (key === 'fuel') {
        c.font = `500 ${R * 0.10}px ${FONT}`; c.fillText('UNLEADED FUEL ONLY', cx + R * 0.05, cy + R * 0.74);
      }
      if (key === 'temp') { c.font = `500 ${R * 0.11}px ${FONT}`; c.fillText('°F', cx + R * 0.05, cy + R * 0.70); }
    }
    c.restore();
  }

  drawOdometer(c, opt, miles, trip) {
    const g = G.speedo;
    const cx = px(g.x), cy = py(g.y), R = g.r * PX;
    const drawDrum = (val, digits, x, y, cw, chh, last) => {
      for (let i = 0; i < digits; i++) {
        const p = Math.pow(10, digits - 1 - i);
        const dv = Math.floor(val / p) % 10;
        const roll = i === digits - 1 ? (val / p) % 1 : 0;
        const xx = x + i * cw;
        c.fillStyle = i === digits - 1 && last ? '#e9e5da' : '#0b0b0b';
        c.fillRect(xx, y, cw - 2, chh);
        c.save(); c.beginPath(); c.rect(xx, y, cw - 2, chh); c.clip();
        c.fillStyle = i === digits - 1 && last ? '#111' : opt.ink;
        c.font = `600 ${chh * 0.8}px ${FONT}`; c.textAlign = 'center'; c.textBaseline = 'middle';
        c.fillText(String(dv), xx + cw / 2 - 1, y + chh / 2 - roll * chh);
        c.fillText(String((dv + 1) % 10), xx + cw / 2 - 1, y + chh * 1.5 - roll * chh);
        c.restore();
      }
    };
    const cw = R * 0.105, chh = R * 0.15;
    drawDrum(miles * 10, 6, cx - cw * 3, cy + R * 0.18, cw, chh, true);
    drawDrum(trip * 10, 4, cx - cw * 2, cy + R * 0.40, cw * 0.85, chh * 0.85, true);
  }

  drawLampIcon(c, k, L, x, y, s, color) {
    c.save();
    c.fillStyle = color; c.strokeStyle = color; c.lineWidth = s * 0.09;
    c.textAlign = 'center'; c.textBaseline = 'middle';
    if (L.text) { c.font = `700 ${s * 0.36}px ${FONT}`; c.fillText(L.text, x, y); }
    else if (L.icon === 'left' || L.icon === 'right') {
      const d = L.icon === 'left' ? -1 : 1;
      c.beginPath(); c.moveTo(x + d * s * 0.42, y); c.lineTo(x + d * s * 0.02, y - s * 0.32); c.lineTo(x + d * s * 0.02, y - s * 0.12);
      c.lineTo(x - d * s * 0.40, y - s * 0.12); c.lineTo(x - d * s * 0.40, y + s * 0.12); c.lineTo(x + d * s * 0.02, y + s * 0.12);
      c.lineTo(x + d * s * 0.02, y + s * 0.32); c.closePath(); c.fill();
    } else if (L.icon === 'beam') {
      c.beginPath(); c.ellipse(x - s * 0.08, y, s * 0.2, s * 0.24, 0, -Math.PI / 2, Math.PI / 2, true); c.closePath(); c.fill();
      for (let i = -2; i <= 2; i++) { c.beginPath(); c.moveTo(x + s * 0.06, y + i * s * 0.1); c.lineTo(x + s * 0.42, y + i * s * 0.1); c.stroke(); }
    } else if (L.icon === 'oil') {
      c.beginPath(); c.moveTo(x - s * 0.40, y - s * 0.05); c.lineTo(x - s * 0.10, y - s * 0.05); c.lineTo(x + s * 0.05, y - s * 0.16);
      c.lineTo(x + s * 0.40, y - s * 0.02); c.lineTo(x + s * 0.18, y + s * 0.18); c.lineTo(x - s * 0.30, y + s * 0.18); c.closePath(); c.fill();
      c.beginPath(); c.arc(x + s * 0.44, y + s * 0.16, s * 0.05, 0, Math.PI * 2); c.fill();
    } else if (L.icon === 'batt') {
      c.fillRect(x - s * 0.36, y - s * 0.18, s * 0.72, s * 0.40);
      c.fillRect(x - s * 0.26, y - s * 0.26, s * 0.12, s * 0.08); c.fillRect(x + s * 0.14, y - s * 0.26, s * 0.12, s * 0.08);
      c.fillStyle = '#000'; c.font = `700 ${s * 0.26}px ${FONT}`; c.fillText('–  +', x, y + s * 0.03);
    } else if (L.icon === 'pump') {
      c.fillRect(x - s * 0.30, y - s * 0.28, s * 0.36, s * 0.56);
      c.fillStyle = '#000'; c.fillRect(x - s * 0.24, y - s * 0.22, s * 0.24, s * 0.16);
      c.fillStyle = color; c.beginPath(); c.moveTo(x + s * 0.06, y - s * 0.1); c.lineTo(x + s * 0.30, y - s * 0.02); c.lineTo(x + s * 0.30, y + s * 0.24); c.stroke();
    }
    c.restore();
  }

  lampPos(L) {
    const x = L.col < 0 ? -0.248 : 0.236;
    const y = 0.042 - L.row * 0.028;
    return [px(x), py(y), 0.022 * PX];
  }

  drawBase(miles, trip) {
    const c = this.base.getContext('2d');
    c.fillStyle = '#070707'; c.fillRect(0, 0, CW, CH);
    const opt = { ink: '#e8e8e2', ink2: '#ff9a3c' };
    for (const [k, g] of Object.entries(G)) this.drawDial(c, k, g, opt);
    this.drawOdometer(c, opt, miles, trip);
    for (const [k, L] of Object.entries(LAMPS)) {
      const [x, y, s] = this.lampPos(L);
      c.fillStyle = '#0d0d0d'; c.fillRect(x - s * 0.55, y - s * 0.45, s * 1.1, s * 0.9);
      this.drawLampIcon(c, k, L, x, y, s, 'rgba(120,120,120,0.35)');
    }
    // fine print
    c.fillStyle = 'rgba(200,200,195,0.55)'; c.font = `500 ${0.0028 * PX}px ${FONT}`; c.textAlign = 'center';
    c.fillText('DMC', px(-0.018), py(-0.054));
    this.mapTex.needsUpdate = true;
  }

  drawGlow() {
    const c = this.glow.getContext('2d');
    c.fillStyle = '#000'; c.fillRect(0, 0, CW, CH);
    // backlight: draw numerals/ticks in illumination tint (masked later by emissiveIntensity)
    if (this.illumOn) {
      const opt = { ink: '#b8ffd8', ink2: '#ff8a2a' };
      c.globalAlpha = 1;
      for (const [k, g] of Object.entries(G)) this.drawDialGlow(c, k, g, opt);
    }
    for (const [k, L] of Object.entries(LAMPS)) {
      if (!this.lampState[k]) continue;
      const [x, y, s] = this.lampPos(L);
      c.save(); c.shadowColor = L.color; c.shadowBlur = s * 0.3;
      this.drawLampIcon(c, k, L, x, y, s, L.color);
      c.restore();
    }
    this.glowTex.needsUpdate = true;
  }

  drawDialGlow(c, k, g, opt) {
    // same strokes as drawDial but without the dark fill
    const save = c.fillStyle;
    const fake = { ...g };
    const ctx = c;
    const fill = ctx.fill.bind(ctx);
    ctx.fill = () => {};
    this.drawDial(ctx, k, fake, opt);
    ctx.fill = fill;
    c.fillStyle = save;
  }

  setLamps(state, illumOn) {
    let dirty = illumOn !== this.illumOn;
    for (const k of Object.keys(LAMPS)) if (!!state[k] !== !!this.lampState[k]) dirty = true;
    if (!dirty) return;
    this.lampState = { ...state };
    this.illumOn = illumOn;
    this.drawGlow();
  }

  update(dt, sim, lights) {
    const on = sim.electrics;
    const tgt = {
      speedo: sim.speedMph,
      tach: sim.rpm / 100,
      volts: on ? sim.volts : 8,
      temp: on ? Math.max(100, sim.coolantF) : 100,
      oil: on ? sim.oilPsi : 0,
      fuel: on ? sim.fuel : 0,
    };
    for (const [k, n] of Object.entries(this.needles)) {
      const g = n.g;
      if (k === 'speedo' || k === 'tach') {
        // eddy-current / moving-magnet movements: 2nd-order, ~10 rad/s, damping 0.75
        const wn = k === 'tach' ? 14 : 9, z = 0.75;
        const a = wn * wn * (tgt[k] - n.v) - 2 * z * wn * n.w;
        n.w += a * dt; n.v += n.w * dt;
      } else {
        // bimetal / slow movements
        const tau = k === 'fuel' ? 7 : k === 'temp' ? 2.5 : 0.8;
        n.v += (tgt[k] - n.v) * Math.min(1, dt / tau);
      }
      n.node.rotation.z = ang(g, n.v);
    }
    const miles = sim.odometer / 1.609344, trip = sim.trip / 1.609344;
    const odoKey = Math.floor(miles * 10 * 20);
    if (odoKey !== this.odo) { this.odo = odoKey; this.drawBase(miles, trip); }
    const illum = lights.panel && on ? lights.dimmer : 0;
    this.mat.emissiveIntensity = Math.max(illum * 0.9, Object.values(this.lampState).some(Boolean) ? 1.6 : 0);
    this.needleMat.emissiveIntensity = 0.12 + illum * 2.2;
  }
}

// ---------------------------------------------------------------------------------------------
// 7-segment style green VFD clock on the console and an amber radio display
function segDisplay(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return { c, t, ctx: c.getContext('2d') };
}

export class ConsoleDisplays {
  constructor(clockPivot, radioPivot) {
    this.clock = segDisplay(512, 200);
    const cm = new THREE.MeshStandardMaterial({ color: 0x050605, roughness: 0.15, emissive: 0xffffff, emissiveMap: this.clock.t, emissiveIntensity: 0 });
    const clk = new THREE.Mesh(new THREE.PlaneGeometry(0.052, 0.020), cm);
    clk.rotation.x = -Math.PI / 2; clk.rotation.z = -Math.PI / 2;
    clk.position.y = 0.0012;
    if (clockPivot) clockPivot.add(clk);
    this.clockMat = cm;
    this.radio = segDisplay(512, 128);
    const rm = new THREE.MeshStandardMaterial({ color: 0x060504, roughness: 0.2, emissive: 0xffffff, emissiveMap: this.radio.t, emissiveIntensity: 0 });
    const rad = new THREE.Mesh(new THREE.PlaneGeometry(0.070, 0.016), rm);
    rad.position.z = 0.0015;
    const rf = new THREE.Group(); rf.rotation.x = -Math.PI / 2; rf.add(rad);
    if (radioPivot) radioPivot.add(rf);
    this.radioMat = rm;
    this.last = '';
  }
  update(sim, radioOn) {
    const d = new Date();
    let hh = d.getHours() % 12; if (hh === 0) hh = 12;
    const colon = d.getMilliseconds() < 500;
    const txt = `${String(hh).padStart(2, ' ')}${colon ? ':' : ' '}${String(d.getMinutes()).padStart(2, '0')}|${radioOn}`;
    const live = sim.ignition >= 1;
    this.clockMat.emissiveIntensity = live ? 2.2 : 0;
    this.radioMat.emissiveIntensity = live && radioOn ? 1.6 : 0;
    if (txt === this.last) return;
    this.last = txt;
    const g = this.clock.ctx;
    g.fillStyle = '#000'; g.fillRect(0, 0, 512, 200);
    g.font = `400 150px "DSEG7", "Share Tech Mono", ${FONT}`;
    g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillStyle = 'rgba(40,255,140,0.12)'; g.fillText('88:88', 256, 104);
    g.fillStyle = '#3dff9a'; g.shadowColor = '#3dff9a'; g.shadowBlur = 18;
    g.fillText(`${String(hh).padStart(2, ' ')}${colon ? ':' : ' '}${String(d.getMinutes()).padStart(2, '0')}`, 256, 104);
    g.shadowBlur = 0;
    this.clock.t.needsUpdate = true;
    const r = this.radio.ctx;
    r.fillStyle = '#000'; r.fillRect(0, 0, 512, 128);
    r.fillStyle = '#ffae3d'; r.shadowColor = '#ffae3d'; r.shadowBlur = 10;
    r.font = `600 84px ${FONT}`; r.textAlign = 'center'; r.textBaseline = 'middle';
    r.fillText('FM  98.5', 256, 66);
    this.radio.t.needsUpdate = true;
  }
}
