// Instrument cluster (Veglia-Borletti style layout of the DMC-12), console clock and radio.
// The dial face is drawn on a canvas (base map + separate illumination/lamp glow map).
import * as THREE from 'three';
import { thinGlass, enhance } from './materials.js';
import { createRadio, drawRadioDisplay } from './radio.js';
import { drawClock } from './console.js';

import { FACE_W, FACE_H, CW, CH, GAUGES as G, LAMPS, angle as ang, setup,
  drawFace, drawDial, drawOdometer, drawLamp } from './instrument-face.js';

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
    pivot.scale.y *= options.heightScale ?? (.124 / FACE_H);
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
    this.glowTex.anisotropy = 8;
    this.mat = new THREE.MeshStandardMaterial({ map: this.mapTex, emissiveMap: this.glowTex, emissive: 0xffffff, emissiveIntensity: 0, roughness: 0.55, metalness: 0 });
    const face = new THREE.Mesh(new THREE.PlaneGeometry(FACE_W, FACE_H), this.mat);
    face.name = 'GaugeFaceMesh';
    pivot.add(face);
    // glass cover
    const glass = new THREE.Mesh(new THREE.PlaneGeometry(FACE_W + 0.01, FACE_H + 0.01),
      thinGlass(new THREE.MeshPhysicalMaterial({ color: 0x222222, roughness: 0.04, metalness: 0 }), 0.05));
    enhance(glass.material);
    glass.position.z = 0.009;
    glass.rotation.x = 0;
    pivot.add(glass);
    // needles
    this.needleMat = new THREE.MeshStandardMaterial({ color: 0xe8e7da, emissive: 0xd6e2c9, emissiveIntensity: 0.15, roughness: 0.4 });
    this.hubMat = new THREE.MeshStandardMaterial({ color: 0x050505, roughness: 0.35, metalness: 0.2 });
    this.needles = {};
    for (const [k, g] of Object.entries(G)) {
      const n = new THREE.Group();
      n.position.set(g.x, g.y, 0.004);
      n.rotation.z = ang(g, g.min);
      const L = g.r * 0.81, w0 = g.r > 0.04 ? 0.0024 : 0.0016, w1 = 0.0007;
      const shape = new THREE.Shape();
      shape.moveTo(-L * 0.18, -w0 * 0.9); shape.lineTo(L, -w1); shape.lineTo(L, w1); shape.lineTo(-L * 0.18, w0 * 0.9); shape.closePath();
      const m = new THREE.Mesh(new THREE.ExtrudeGeometry(shape, { depth: 0.0008, bevelEnabled: true, bevelThickness: .0002, bevelSize: .0002, bevelSegments: 2, steps: 1 }), this.needleMat);
      n.add(m);
      const hub = new THREE.Mesh(new THREE.CylinderGeometry(g.r > 0.04 ? 0.0048 : 0.0028, g.r > 0.04 ? 0.0053 : 0.0032, 0.004, 24), this.hubMat);
      hub.rotation.x = Math.PI / 2; hub.position.z = 0.003;
      n.add(hub);
      pivot.add(n);
      this.needles[k] = { node: n, g, v: g.min, w: 0 };
    }
    this.lampState = {};
    this.illum = 0;
    this.odo = -1;
    this.fontsReady = false;
    Promise.all([document.fonts.load('500 40px "Barlow Semi Condensed"'), document.fonts.load('600 40px "Barlow Semi Condensed"'), document.fonts.load('400 40px "IBM Plex Mono"')]).catch(() => {}).then(() => { this.fontsReady = true; this.drawBase(this.miles || 0, this.trip || 0); this.drawGlow(); });
    this.drawBase(0, 0);
    this.drawGlow();
  }

  drawBase(miles, trip) {
    this.miles = miles; this.trip = trip;
    drawFace(this.base.getContext('2d'), miles, trip);
    this.mapTex.needsUpdate = true;
  }

  drawGlow() {
    const c = this.glow.getContext('2d');
    setup(c); c.fillStyle = '#000'; c.fillRect(0, 0, 800, 221);
    if (this.illumOn) {
      for (const [k, g] of Object.entries(G)) drawDial(c, k, g, true);
      drawOdometer(c, this.miles || 0, this.trip || 0, true);
    }
    for (const k of Object.keys(LAMPS)) if (this.lampState[k]) {
      drawLamp(c, k, true);
      if (k === 'high') drawLamp(c, k, true, 438);
    }
    this.glowTex.needsUpdate = true;
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
    if (odoKey !== this.odo) { this.odo = odoKey; this.drawBase(miles, trip); if (this.illumOn) this.drawGlow(); }
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
  constructor(clockPivot, radioPivot, options = {}) {
    this.clock = segDisplay(1024, 400);
    this.clock.t.anisotropy = 8;
    const cm = new THREE.MeshStandardMaterial({ color: 0x050605, roughness: 0.15, emissive: 0xffffff, emissiveMap: this.clock.t, emissiveIntensity: 0 });
    const clk = new THREE.Mesh(new THREE.PlaneGeometry(0.052, 0.020), cm);
    clk.rotation.x = -Math.PI / 2; clk.rotation.z = -Math.PI / 2;
    clk.position.y = 0.0012;
    if (clockPivot) clockPivot.add(clk);
    this.clockMat = cm;
    this.radio = segDisplay(1024, 256);
    this.radio.t.anisotropy = 8;
    const rm = new THREE.MeshStandardMaterial({ color: 0x060504, roughness: 0.2, emissive: 0xffffff, emissiveMap: this.radio.t, emissiveIntensity: 0 });
    const rad = new THREE.Mesh(new THREE.PlaneGeometry(0.070, 0.016), rm);
    rad.position.z = 0.0015;
    const rf = new THREE.Group(); rf.rotation.x = -Math.PI / 2; rf.add(rad);
    if (radioPivot && options.detailed) {
      const radio = createRadio(radioPivot, this.radio.t);
      this.radioMat = radio.material; this.radioFaceTexture = radio.faceTexture;
      rad.geometry.dispose(); rm.dispose();
    } else {
      if (radioPivot) radioPivot.add(rf);
      this.radioMat = rm;
    }
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
    drawClock(this.clock.ctx, this.clock.c.width, this.clock.c.height, hh, d.getMinutes(), colon);
    this.clock.t.needsUpdate = true;
    drawRadioDisplay(this.radio.ctx, this.radio.c.width, this.radio.c.height);
    this.radio.t.needsUpdate = true;
  }
}
