// Exterior + interior lamps. Incandescent bulbs get thermal rise/fall times.
import * as THREE from 'three';

// split a mesh whose geometry contains both sides into L (three -Z) / R (+Z) meshes
export function splitBySide(mesh) {
  const g = mesh.geometry;
  const pos = g.attributes.position, idx = g.index.array;
  const make = (sel) => {
    const keep = [];
    for (let i = 0; i < idx.length; i += 3) {
      const z = (pos.getZ(idx[i]) + pos.getZ(idx[i + 1]) + pos.getZ(idx[i + 2])) / 3;
      if (sel(z)) keep.push(idx[i], idx[i + 1], idx[i + 2]);
    }
    const ng = g.clone();
    ng.setIndex(keep);
    return ng;
  };
  const parent = mesh.parent;
  const L = new THREE.Mesh(make(z => z < 0), mesh.material.clone());
  const R = new THREE.Mesh(make(z => z >= 0), mesh.material.clone());
  for (const [m, s] of [[L, '_L'], [R, '_R']]) {
    m.name = mesh.name + s; m.material.name = mesh.material.name + s;
    m.position.copy(mesh.position); m.quaternion.copy(mesh.quaternion); m.scale.copy(mesh.scale);
    m.castShadow = mesh.castShadow; m.receiveShadow = mesh.receiveShadow;
    m.userData = { ...mesh.userData };
    parent.add(m);
  }
  parent.remove(mesh);
  return [L, R];
}

class Bulb {
  constructor(rise = 0.06, fall = 0.10) { this.v = 0; this.rise = rise; this.fall = fall; }
  step(target, dt) { const tau = target > this.v ? this.rise : this.fall; this.v += (target - this.v) * Math.min(1, dt / tau); return this.v; }
}

function beamCookie(high) {
  // light cookie: low beam has a sharp horizontal cut-off with a 15 deg step on the kerb side
  const c = document.createElement('canvas');
  c.width = c.height = 256;
  const g = c.getContext('2d');
  const img = g.createImageData(256, 256);
  for (let y = 0; y < 256; y++) for (let x = 0; x < 256; x++) {
    const u = x / 255 * 2 - 1, v = 1 - y / 255 * 2;
    const r = Math.hypot(u * 0.8, v * 1.6);
    let a;
    if (high) a = Math.exp(-r * r * 2.2);
    else {
      const cut = -0.04 + (u > 0.05 ? Math.min(0.22, (u - 0.05) * 0.6) : 0);
      const edge = 1 - Math.min(1, Math.max(0, (v - cut) / 0.02));
      a = Math.exp(-(u * u) * 1.5 - (v + 0.25) * (v + 0.25) * 4) * edge + 0.06 * Math.exp(-r * r) * edge;
      a += 0.05 * Math.exp(-r * r * 0.8);
    }
    const i = (y * 256 + x) * 4;
    const w = Math.min(255, a * 255);
    img.data[i] = w; img.data[i + 1] = w * 0.97; img.data[i + 2] = w * 0.90; img.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

export class Lamps {
  constructor(car, scene) {
    this.car = car;
    const root = car.root;
    const find = n => { let r = null; root.traverse(o => { if (!r && o.isMesh && o.name === n) r = o; }); return r || root.getObjectByName(n); };
    // split shared-material meshes into sides
    this.mats = {};
    for (const name of ['turn_front', 'marker_front', 'tl_turn', 'marker_rear', 'hl_bulb_Lo', 'hl_bulb_Hi', 'tl_tail', 'tl_rev', 'plate_lenses', 'courtesy_L', 'courtesy_R', 'courtesy_rear_L', 'courtesy_rear_R']) {
      const m = find(name);
      if (!m || !m.isMesh) continue;
      if (name.startsWith('courtesy')) { m.material = m.material.clone(); this.mats[name] = m.material; continue; }
      const [L, R] = splitBySide(m);
      this.mats[name + '_L'] = L.material; this.mats[name + '_R'] = R.material;
    }
    const posOf = n => { const o = find(n); return o ? o.getWorldPosition(new THREE.Vector3()) : new THREE.Vector3(); };
    this.lights = {};
    const body = car.body;
    const addSpot = (key, marker, high) => {
      const s = new THREE.SpotLight(0xfff1dd, 0, 60, high ? 0.28 : 0.52, high ? 0.45 : 0.35, 1.6);
      s.map = beamCookie(high);
      const p = body.worldToLocal(posOf(marker).add(new THREE.Vector3(-0.03, 0, 0)));
      s.position.copy(p);
      s.target.position.copy(p).add(new THREE.Vector3(20, high ? -0.15 : -0.65, 0));
      body.add(s, s.target);
      this.lights[key] = s;
    };
    addSpot('lowL', 'LP_HeadLo_L', false); addSpot('lowR', 'LP_HeadLo_R', false);
    addSpot('highL', 'LP_HeadHi_L', true); addSpot('highR', 'LP_HeadHi_R', true);
    // the cookie (beam pattern) needs a shadow camera; only the low beams cast shadows
    for (const k of ['lowL', 'lowR']) {
      const L = this.lights[k];
      L.castShadow = true;
      L.shadow.mapSize.set(1024, 1024);
      L.shadow.bias = -0.0004;
      L.shadow.camera.near = 0.25; L.shadow.camera.far = 45;
      L.shadow.autoUpdate = false;
    }
    const addPoint = (key, marker, color, dist, offset) => {
      const l = new THREE.PointLight(color, 0, dist, 2);
      const p = body.worldToLocal(posOf(marker).add(offset));
      l.position.copy(p);
      body.add(l);
      this.lights[key] = l;
    };
    const back = new THREE.Vector3(-0.12, -0.05, 0), fwd = new THREE.Vector3(0.12, -0.05, 0);
    addPoint('tailL', 'LP_Tail_L', 0xff1405, 5, back); addPoint('tailR', 'LP_Tail_R', 0xff1405, 5, back);
    addPoint('revL', 'LP_Rev_L', 0xfff4e8, 7, back); addPoint('revR', 'LP_Rev_R', 0xfff4e8, 7, back);
    addPoint('turnFL', 'LP_TurnF_L', 0xff8a14, 4, fwd); addPoint('turnFR', 'LP_TurnF_R', 0xff8a14, 4, fwd);
    addPoint('turnRL', 'LP_TurnR_L', 0xff8a14, 4, back); addPoint('turnRR', 'LP_TurnR_R', 0xff8a14, 4, back);
    // cabin courtesy light (roof spine) + door edge lamps
    const cab = new THREE.PointLight(0xfff0d8, 0, 2.2, 2);
    cab.position.set(-0.1, 1.04, 0);
    body.add(cab);
    this.lights.cabin = cab;
    // dashboard illumination spill onto the wheel / driver
    const dashGlow = new THREE.PointLight(0x9dffd0, 0, 0.9, 2);
    dashGlow.position.set(0.32, 0.70, -0.37);
    body.add(dashGlow);
    this.lights.dash = dashGlow;

    this.b = {};
    for (const k of ['low', 'high', 'park', 'tail', 'brake', 'rev', 'tL', 'tR', 'cab', 'courtL', 'courtR']) this.b[k] = new Bulb(k === 'low' || k === 'high' ? 0.09 : 0.05, k === 'low' || k === 'high' ? 0.18 : 0.09);
    this.state = { headlights: 0, flash: false, turn: 0, hazard: false, brake: false, reverse: false, interior: 'door', dimmer: 0.8 };
    this.flasher = { t: 0, on: false };
    this.onTick = null;
  }

  get lampsOn() { return this.state.headlights >= 1; }

  // electrical load in amps (for voltage sag)
  load() {
    const s = this.state;
    return (s.headlights >= 2 ? 10 : 0) + (s.headlights === 3 || s.flash ? 9 : 0) + (s.headlights >= 1 ? 3.5 : 0) + (s.brake ? 4 : 0);
  }

  update(dt, sim) {
    const s = this.state, b = this.b;
    const ign = sim.electrics;
    const batt = sim.ignition >= 0;       // lighting circuit is live without ignition on the DMC-12
    const vScale = Math.min(1.15, Math.max(0.55, (sim.ignition >= 2 ? sim.volts : 12.4) / 13.5)) ** 1.6;
    // flasher relay ~ 85 flashes / min, 50% duty; hazards run without ignition
    const flashing = s.hazard || (ign && s.turn !== 0);
    if (flashing) {
      this.flasher.t += dt;
      const period = 60 / 85;
      const on = (this.flasher.t % period) < period * 0.5;
      if (on !== this.flasher.on) { this.flasher.on = on; this.onTick?.(on); }
    } else { if (this.flasher.on) this.onTick?.(false); this.flasher.t = 0; this.flasher.on = false; }
    const fl = this.flasher.on;
    const lowOn = batt && s.headlights >= 2;
    const highOn = batt && (s.headlights === 3 || (s.flash && ign));
    const parkOn = batt && s.headlights >= 1;
    const low = b.low.step(lowOn ? vScale : 0, dt);
    const high = b.high.step(highOn ? vScale : 0, dt);
    const park = b.park.step(parkOn ? 1 : 0, dt);
    const brk = b.brake.step(ign && s.brake ? 1 : 0, dt);
    const rev = b.rev.step(ign && s.reverse ? 1 : 0, dt);
    const tL = b.tL.step(fl && (s.hazard || s.turn < 0) ? 1 : 0, dt);
    const tR = b.tR.step(fl && (s.hazard || s.turn > 0) ? 1 : 0, dt);
    const M = this.mats;
    const set = (k, v) => { if (M[k]) M[k].emissiveIntensity = v; };
    // headlamp filaments (seen through the fluted lens) + beams
    set('hl_bulb_Lo_L', low * 60); set('hl_bulb_Lo_R', low * 60);
    set('hl_bulb_Hi_L', high * 60 + low * 4); set('hl_bulb_Hi_R', high * 60 + low * 4);
    this.lights.lowL.intensity = this.lights.lowR.intensity = low * 2600;
    this.lights.lowL.shadow.autoUpdate = this.lights.lowR.shadow.autoUpdate = low > 0.01;
    this.lights.highL.intensity = this.lights.highR.intensity = high * 7000;
    // front amber: parking (dim) + turn (bright) share the bulb (dual filament)
    set('turn_front_L', Math.max(park * 0.6, tL * 4)); set('turn_front_R', Math.max(park * 0.6, tR * 4));
    set('marker_front_L', Math.max(park * 1.2, tL * 4)); set('marker_front_R', Math.max(park * 1.2, tR * 4));
    set('marker_rear_L', park * 2.0); set('marker_rear_R', park * 2.0);
    set('tl_turn_L', tL * 4); set('tl_turn_R', tR * 4);
    const tail = park * 0.7 + brk * 3.2;
    set('tl_tail_L', tail); set('tl_tail_R', tail);
    set('tl_rev_L', rev * 4); set('tl_rev_R', rev * 4);
    set('plate_lenses_L', park * 3); set('plate_lenses_R', park * 3);
    this.lights.tailL.intensity = this.lights.tailR.intensity = park * 0.25 + brk * 1.6;
    this.lights.revL.intensity = this.lights.revR.intensity = rev * 3.5;
    this.lights.turnFL.intensity = tL * 1.6 + park * 0.08; this.lights.turnFR.intensity = tR * 1.6 + park * 0.08;
    this.lights.turnRL.intensity = tL * 1.4; this.lights.turnRR.intensity = tR * 1.4;
    // interior: courtesy light follows doors (or forced on / off)
    const doorOpen = this.car.doorL.theta > 0.05 || this.car.doorR.theta > 0.05;
    const cabOn = s.interior === 'on' || (s.interior === 'door' && doorOpen);
    this.lights.cabin.intensity = b.cab.step(cabOn ? 1 : 0, dt) * 0.8;
    set('courtesy_L', b.courtL.step(this.car.doorL.theta > 0.05 ? 1 : 0, dt) * 5);
    set('courtesy_R', b.courtR.step(this.car.doorR.theta > 0.05 ? 1 : 0, dt) * 5);
    set('courtesy_rear_L', this.car.doorL.theta > 0.05 ? 3 : 0);
    set('courtesy_rear_R', this.car.doorR.theta > 0.05 ? 3 : 0);
    this.lights.dash.intensity = parkOn && ign ? 0.004 * s.dimmer : 0;
    return { panel: parkOn, dimmer: s.dimmer, turnL: tL > 0.5, turnR: tR > 0.5, high: highOn };
  }
}
