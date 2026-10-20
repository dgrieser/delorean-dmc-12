// Car rig: finds the named pivots in the packed scene, places wheels, simulates hinged
// panels (torsion bar + gas strut + gravity), steering geometry, suspension body motion,
// pedals / shifter / handbrake and the windscreen wipers.
import * as THREE from 'three';

const DEG = Math.PI / 180;

// ---------------------------------------------------------------------------------------------
// Hinged panel dynamics. Angle 0 = closed. Torques in N*m, inertia in kg*m^2.
export class HingedPanel {
  constructor(node, axis, sign, p) {
    this.node = node;
    this.axis = axis.clone().normalize();
    this.sign = sign;
    this.base = node.quaternion.clone();
    this.p = Object.assign({ max: 1.2, I: 5, mgr: 80, phase: 0, spring: () => 0, damp: 20, handTorque: 160, latchAt: 0.035 }, p);
    this.theta = 0; this.omega = 0;
    this.latched = true;
    this.intent = 0;        // +1 open, -1 close, 0 none
    this.handTime = 0;
    this.onEvent = null;
    this.moving = false;
  }
  get open() { return !this.latched && this.theta > 0.05; }
  get amount() { return this.theta / this.p.max; }
  toggle() { (this.latched || this.intent < 0) ? this.openUp() : this.close(); }
  openUp() {
    if (this.latched) { this.latched = false; this.onEvent?.('unlatch'); }
    this.intent = 1; this.handTime = 0.55;
    this.omega = Math.max(this.omega, 0.4);
  }
  close() { this.intent = -1; this.handTime = 3.0; this.onEvent?.('pull'); }
  torque(th, w) {
    const p = this.p;
    let t = p.spring(th) - p.mgr * Math.cos(p.phase - th) - p.damp * w;
    if (this.handTime > 0) t += this.intent * p.handTorque;
    if (th > p.max) t -= 4000 * (th - p.max) + 60 * w;         // rubber end stop / strut end
    return t;
  }
  step(dt) {
    if (this.latched) return;
    const n = 6, h = dt / n;
    for (let i = 0; i < n; i++) {
      const a = this.torque(this.theta, this.omega) / this.p.I;
      this.omega += a * h;
      this.theta += this.omega * h;
      if (this.theta <= 0) {
        this.theta = 0;
        if (this.omega < -0.05 || this.intent <= 0) {
          const v = this.omega;
          this.omega = 0;
          this.latched = true; this.intent = 0; this.handTime = 0;
          this.onEvent?.('latch', -v);
          break;
        }
        this.omega = 0;
      }
    }
    this.handTime = Math.max(0, this.handTime - dt);
    if (this.intent < 0 && this.handTime <= 0 && this.theta > this.p.latchAt) this.handTime = 0.5;
    this.moving = Math.abs(this.omega) > 0.02;
    this.apply();
  }
  apply() {
    const q = new THREE.Quaternion().setFromAxisAngle(this.axis, this.sign * this.theta);
    this.node.quaternion.copy(this.base).multiply(q);
  }
}

// ---------------------------------------------------------------------------------------------
// The reference car (ref/studio) runs low-profile tyres on the stock 14/15 in. rims: its wheel
// centres stand 0.271 / 0.298 m above the floor. The tyre model is a 60-series pair (0.293 /
// 0.330 m), so its sidewalls are squashed radially, keeping the bead seated on the rim.
const TYRE_R = { F: 0.272, R: 0.299 };
const BEAD_R = { F: 0.178, R: 0.191 };

function lowProfile(obj, R, bead) {
  obj?.traverse(o => {
    if (!o.isMesh || o.geometry.userData.lowProfile) return;
    const g = o.geometry, P = g.attributes.position, n = P.count;
    g.computeBoundingBox();
    const s = g.boundingBox.getSize(new THREE.Vector3()), c = g.boundingBox.getCenter(new THREE.Vector3());
    const ax = s.x < s.y && s.x < s.z ? 0 : s.y < s.z ? 1 : 2;        // axle = the thin dimension
    const [i, j] = [0, 1, 2].filter(a => a !== ax);
    const v = [0, 0, 0];
    let rmax = 0;
    for (let q = 0; q < n; q++) rmax = Math.max(rmax, Math.hypot(P.getComponent(q, i) - c.getComponent(i), P.getComponent(q, j) - c.getComponent(j)));
    const k = (R - bead) / (rmax - bead);
    const N = g.attributes.normal;
    for (let q = 0; q < n; q++) {
      for (let a = 0; a < 3; a++) v[a] = P.getComponent(q, a);
      const du = v[i] - c.getComponent(i), dv = v[j] - c.getComponent(j), r = Math.hypot(du, dv);
      if (r <= bead) continue;
      const f = (bead + (r - bead) * k) / r;
      P.setComponent(q, i, c.getComponent(i) + du * f);
      P.setComponent(q, j, c.getComponent(j) + dv * f);
      if (!N) continue;
      // normals take the inverse transpose of the map: radial stretch k, tangential stretch f
      const ur = du / r, vr = dv / r, ni = N.getComponent(q, i), nj = N.getComponent(q, j), na = N.getComponent(q, ax);
      const nr = (ni * ur + nj * vr) / k, nt = (-ni * vr + nj * ur) / f;
      const mi = nr * ur - nt * vr, mj = nr * vr + nt * ur, l = Math.hypot(mi, mj, na) || 1;
      N.setComponent(q, i, mi / l); N.setComponent(q, j, mj / l); N.setComponent(q, ax, na / l);
    }
    P.needsUpdate = true;
    if (N) N.needsUpdate = true;
    g.computeBoundingSphere();
    g.userData.lowProfile = true;
  });
}

export class Car {
  constructor(root, wheels, manifest, lib) {
    this.root = root;
    this.lib = lib;
    const get = n => root.getObjectByName(n);
    this.body = get('Body');
    this.bodyBase = { p: this.body.position.clone(), q: this.body.quaternion.clone() };
    this.nodes = {
      doorL: get('Door_L_Pivot'), doorR: get('Door_R_Pivot'), hood: get('Hood_Pivot'),
      lid: get('EngineLid_Pivot'), wheel: get('SteeringWheel_Pivot'),
      shifter: get('Shifter_Pivot'), handbrake: get('Handbrake_Pivot'),
      clutch: get('Pedal_Clutch_Pivot'), brake: get('Pedal_Brake_Pivot'), gas: get('Pedal_Gas_Pivot'),
      gauge: get('GaugeFace_Pivot'), clock: get('ClockFace_Pivot'), radio: get('RadioFace_Pivot'),
    };
    for (const k of ['wheel', 'shifter', 'handbrake', 'clutch', 'brake', 'gas']) {
      const n = this.nodes[k];
      if (n) n.userData.base = n.quaternion.clone();
    }
    // --- hinged panels (masses and spring rates are estimates for a DMC-12)
    const X = new THREE.Vector3(1, 0, 0), Z = new THREE.Vector3(0, 0, 1);
    // gull-wing: cryogenically treated torsion bar (preloaded, falls with angle) + gas strut
    const doorSpring = th => 121 * (1 - 0.36 * th) + 46 * smooth(0.35, 0.9, th);
    const doorP = { max: 69 * DEG, I: 6.5, mgr: 108, phase: 40 * DEG, spring: doorSpring, damp: 58, handTorque: 95 };
    this.doorL = new HingedPanel(this.nodes.doorL, X, +1, doorP);
    this.doorR = new HingedPanel(this.nodes.doorR, X, -1, doorP);
    // front-hinged bonnet on gas struts
    this.hood = new HingedPanel(this.nodes.hood, Z, +1, { max: 58 * DEG, I: 4.2, mgr: 62, phase: 4 * DEG,
      spring: th => 66 * smooth(0.0, 0.25, th) + 12, damp: 18, handTorque: 120 });
    // louvred engine cover on gas struts
    this.lid = new HingedPanel(this.nodes.lid, Z, -1, { max: 52 * DEG, I: 3.6, mgr: 54, phase: 8 * DEG,
      spring: th => 58 * smooth(0.0, 0.3, th) + 10, damp: 16, handTorque: 110 });
    this.panels = { doorL: this.doorL, doorR: this.doorR, hood: this.hood, lid: this.lid };

    // --- wheels
    this.wheels = {};
    const asmF = wheels.getObjectByName('WheelAsm_F'), asmR = wheels.getObjectByName('WheelAsm_R');
    for (const [k, R] of Object.entries(TYRE_R)) lowProfile(wheels.getObjectByName('Tyre_' + k), R, BEAD_R[k]);
    for (const [k, asm] of [['FL', asmF], ['FR', asmF], ['RL', asmR], ['RR', asmR]]) {
      const pos = get('WheelPos_' + k);
      const steer = new THREE.Group();
      steer.name = 'Steer_' + k;
      pos.add(steer);
      const w = asm.clone(true);
      w.name = 'Wheel_' + k;
      // right side: the same wheel turned round (not mirrored, so the sidewall lettering reads
      // correctly); its spin axis then points the other way. The caliper is mirrored back so it
      // stays behind the axle.
      const right = k.endsWith('R');
      if (right) {
        w.rotation.y = Math.PI;
        const cal = w.getObjectByName('Caliper_' + k[0]);
        if (cal) cal.scale.x = -1;
      }
      steer.add(w);
      const spin = w.getObjectByName(k[0] === 'F' ? 'Wheel_F' : 'Wheel_R');
      this.wheels[k] = { pos, steer, spin, dir: right ? -1 : 1, radius: TYRE_R[k[0]], angle: 0 };
    }
    this.track = 1.59; this.wheelbase = 2.413;

    // --- state
    this.steerWheelAngle = 0;     // steering wheel angle (rad), + = left
    this.steerRatio = 13.0;
    this.pedal = { clutch: 0, brake: 0, gas: 0 };
    this.gear = 'N';
    this.handbrake = 1;
    this.susp = { pitch: 0, pitchV: 0, roll: 0, rollV: 0, heave: 0, heaveV: 0 };
    this.engineShake = 0;
    this.wipers = null;
    this.windshield = manifest?.windshield;

    // toll windows: small power panes in the lower door glass, sliding down along the glass plane
    const c50 = Math.cos(50 * DEG), s50 = Math.sin(50 * DEG);
    this.toll = {};
    for (const [k, dir] of [['L', new THREE.Vector3(0, -c50, -s50)], ['R', new THREE.Vector3(0, -c50, s50)]]) {
      let mesh = null;
      root.traverse(o => { if (!mesh && o.isMesh && o.name === 'glass_toll_' + k) mesh = o; });
      if (mesh) this.toll[k] = { mesh, base: mesh.position.clone(), dir, pos: 0, target: 0, travel: 0.085 };
    }
  }

  setToll(side, down) { const t = this.toll[side]; if (t) t.target = down ? 1 : 0; }
  get tollMoving() { return Object.values(this.toll).some(t => Math.abs(t.target - t.pos) > 1e-3); }

  // three.js frame helpers: Blender (x, y, z) -> three (x, z, -y)
  static b2t(x, y, z) { return new THREE.Vector3(x, z, -y); }

  roadWheelAngles() {
    const d = this.steerWheelAngle / this.steerRatio;
    if (Math.abs(d) < 1e-4) return [d, d];
    const R = this.wheelbase / Math.tan(Math.abs(d));
    const inner = Math.atan(this.wheelbase / (R - this.track / 2));
    const outer = Math.atan(this.wheelbase / (R + this.track / 2));
    // + = turning left: left wheel is inner
    return d > 0 ? [inner, outer] : [-outer, -inner];
  }

  update(dt, sim) {
    for (const p of Object.values(this.panels)) p.step(dt);
    // window motors run only with the ignition on (~2.4 s for the full travel)
    const powered = !sim || sim.ignition >= 2;
    for (const t of Object.values(this.toll)) {
      if (powered) t.pos += Math.sign(t.target - t.pos) * Math.min(Math.abs(t.target - t.pos), dt / 2.4);
      t.mesh.position.copy(t.base).addScaledVector(t.dir, t.pos * t.travel);
    }
    // steering + wheel spin
    const [aL, aR] = this.roadWheelAngles();
    this.wheels.FL.steer.rotation.y = aL;
    this.wheels.FR.steer.rotation.y = aR;
    const v = sim ? sim.speed : 0;
    for (const w of Object.values(this.wheels)) {
      w.angle -= (v / w.radius) * dt;
      if (w.spin) w.spin.rotation.z = w.angle * w.dir;
    }
    const sw = this.nodes.wheel;
    if (sw) sw.quaternion.copy(sw.userData.base).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 1, 0), this.steerWheelAngle));
    // pedals (rotate about local z, pads move forward)
    const ped = (n, a) => { if (n) n.quaternion.copy(n.userData.base).multiply(new THREE.Quaternion().setFromAxisAngle(new THREE.Vector3(0, 0, 1), a)); };
    ped(this.nodes.clutch, this.pedal.clutch * 0.42);
    ped(this.nodes.brake, this.pedal.brake * 0.30);
    ped(this.nodes.gas, this.pedal.gas * 0.32);
    // handbrake lever
    ped(this.nodes.handbrake, this.handbrake * 0.42);
    // shifter H-pattern: [lateral, fore-aft]
    const G = { N: [0, 0], 1: [-1, 1], 2: [-1, -1], 3: [0, 1], 4: [0, -1], 5: [1, 1], R: [1, -1] };
    const g = G[this.gear] || [0, 0];
    this._sh = this._sh || [0, 0];
    this._sh[0] += (g[0] - this._sh[0]) * Math.min(1, dt * 14);
    this._sh[1] += (g[1] - this._sh[1]) * Math.min(1, dt * 14);
    const shn = this.nodes.shifter;
    if (shn) {
      const q = new THREE.Quaternion().setFromEuler(new THREE.Euler(this._sh[0] * 0.16, 0, -this._sh[1] * 0.26, 'XYZ'));
      shn.quaternion.copy(shn.userData.base).multiply(q);
    }
    // suspension: body pitch/roll/heave as damped springs driven by accelerations
    const s = this.susp;
    const ax = sim ? sim.accel : 0, ay = sim ? sim.latAccel : 0;
    const kP = 38, cP = 7.5;          // pitch natural freq ~1 Hz, ~0.6 damping
    const tP = -ax * 0.0042, tR = ay * 0.0062;
    s.pitchV += (kP * (tP - s.pitch) - cP * s.pitchV) * dt; s.pitch += s.pitchV * dt;
    s.rollV += (kP * (tR - s.roll) - cP * s.rollV) * dt; s.roll += s.rollV * dt;
    const shake = sim ? sim.shake : 0;
    const t = performance.now() / 1000;
    const jitter = shake * 0.0007 * (Math.sin(t * 2 * Math.PI * (sim ? sim.firingHz : 20)) + 0.4 * Math.sin(t * 61.0));
    this.body.position.copy(this.bodyBase.p);
    this.body.position.y += s.heave + jitter;
    this.body.quaternion.copy(this.bodyBase.q).multiply(new THREE.Quaternion().setFromEuler(new THREE.Euler(s.roll + jitter * 0.6, 0, s.pitch, 'XYZ')));
    if (this.wipers) this.wipers.update(dt);
  }
}

function smooth(a, b, x) { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); }

// ---------------------------------------------------------------------------------------------
// Wipers: tandem LHD pattern. Pivots on the cowl, blades park pointing to the passenger side.
// Each blade is rebuilt every frame so it follows the curved windscreen.
export class Wipers {
  constructor(parent, ws, lib) {
    this.ws = ws;
    this.group = new THREE.Group();
    this.group.name = 'Wipers';
    parent.add(this.group);
    this.mode = 'off';        // off | int | low | high
    this.phase = 0;           // 0..1 within a wipe cycle (0 = parked)
    this.running = false;
    this.intDelay = 4;
    this.wait = 0;
    this.washing = 0;
    this.motorLoad = 0;
    const armMat = new THREE.MeshPhysicalMaterial({ color: 0x050505, roughness: 0.45, clearcoat: 0.3 });
    const rubber = new THREE.MeshStandardMaterial({ color: 0x080808, roughness: 0.8 });
    // pivot positions in Blender coords (y left)
    this.units = [
      { pivotY: 0.58, armL: 0.31, bladeL: 0.405, sweep: 84 * DEG, park: 2.0 * DEG },
      { pivotY: 0.02, armL: 0.31, bladeL: 0.405, sweep: 82 * DEG, park: 1.5 * DEG },
    ].map(u => {
      const segs = 24;
      const bladeGeo = new THREE.BufferGeometry();
      bladeGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(segs * 2 * 4 * 3), 3));
      const idx = [];
      for (let i = 0; i < segs - 1; i++) {
        for (let k = 0; k < 4; k++) {
          const a = i * 4 + k, b = i * 4 + ((k + 1) % 4), c = (i + 1) * 4 + k, d = (i + 1) * 4 + ((k + 1) % 4);
          idx.push(a, c, b, b, c, d);
        }
      }
      bladeGeo.setIndex(idx);
      const blade = new THREE.Mesh(bladeGeo, rubber);
      const armGeo = bladeGeo.clone();
      armGeo.setAttribute('position', new THREE.BufferAttribute(new Float32Array(segs * 2 * 4 * 3), 3));
      const arm = new THREE.Mesh(armGeo, armMat);
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.016, 0.019, 0.03, 20), armMat);
      blade.frustumCulled = arm.frustumCulled = false;
      blade.castShadow = arm.castShadow = cap.castShadow = true;
      this.group.add(blade, arm, cap);
      return Object.assign(u, { blade, arm, cap, segs });
    });
    this.update(0);
  }

  // windscreen surface: Blender coords. glass param (yy lateral, s up-slope from the base)
  surf(yLeft, s, lift = 0) {
    const w = this.ws;
    const slope = Math.atan2(w.nx, w.nz);           // glass angle from horizontal
    const z = w.bz + 0.022 + s * Math.sin(slope);
    const yy = Math.abs(yLeft);
    const x = w.bx - w.wrap * yy * yy - (z - w.bz) * w.nz / w.nx;
    const n = new THREE.Vector3(w.nx, 0, w.nz).normalize();
    // wrap tilts the normal sideways a little
    n.y = -2 * w.wrap * yLeft * w.nx; n.normalize();
    return { p: new THREE.Vector3(x + n.x * lift, yLeft + n.y * lift, z + n.z * lift), n };
  }

  setMode(m) {
    this.mode = m;
    if (m !== 'off') { this.running = true; this.wait = 0; }
  }
  wash(on) { this.washing = on ? 1 : 0; if (on) { this.running = true; this.washCycles = 3; } }

  update(dt) {
    const speed = this.mode === 'high' ? 62 / 60 : 44 / 60;    // wipe cycles per second
    if (this.running) {
      if (this.wait > 0) this.wait -= dt;
      else {
        const prev = this.phase;
        this.phase += dt * speed;
        if (this.phase >= 1) {
          this.phase = 0;
          if (this.washCycles > 0) this.washCycles--;
          if (this.mode === 'off' && !(this.washCycles > 0)) this.running = false;
          else if (this.mode === 'int' && !(this.washCycles > 0)) this.wait = this.intDelay;
        }
        if (prev === 0 && this.mode === 'off' && !(this.washCycles > 0) && !this.washing) this.running = false;
      }
    }
    this.motorLoad = this.running && this.wait <= 0 ? 1 : 0;
    // crank-rocker linkage: smooth reversal at each end
    const a = (1 - Math.cos(this.phase * 2 * Math.PI)) / 2;
    for (const u of this.units) this.pose(u, u.park + a * u.sweep);
  }

  pose(u, ang) {
    // 2D unrolled glass coords: (lat, up). Park direction points to the passenger side (-y).
    const piv = { lat: u.pivotY, up: 0 };
    const dir = { lat: -Math.cos(ang), up: Math.sin(ang) };
    const nrm = { lat: -dir.up, up: dir.lat };
    const tip = { lat: piv.lat + dir.lat * u.armL, up: piv.up + dir.up * u.armL };
    const fill = (mesh, along, w0, w1, h0, h1, lift0) => {
      const pos = mesh.geometry.attributes.position;
      for (let i = 0; i < u.segs; i++) {
        const t = i / (u.segs - 1);
        const c = along(t);
        const S = this.surf(c.lat, c.up, lift0);
        const S2 = this.surf(c.lat + c.wl, c.up + c.wu, lift0);
        const side = new THREE.Vector3().subVectors(S2.p, S.p).normalize();
        const w = w0 + (w1 - w0) * t, h = h0 + (h1 - h0) * t;
        const corners = [[-w, 0], [w, 0], [w, h], [-w, h]];
        corners.forEach(([sx, hy], k) => {
          const P = S.p.clone().addScaledVector(side, sx).addScaledVector(S.n, hy);
          pos.setXYZ(i * 4 + k, P.x, P.z, -P.y);
        });
      }
      pos.needsUpdate = true;
      mesh.geometry.computeVertexNormals();
      mesh.geometry.computeBoundingSphere();
    };
    // arm: from the pivot to the tip, rising off the glass near the pivot
    fill(u.arm, t => ({ lat: piv.lat + dir.lat * u.armL * t, up: piv.up + dir.up * u.armL * t, wl: nrm.lat * 0.01, wu: nrm.up * 0.01 }),
      0.009, 0.006, 0.010, 0.006, 0.02);
    // blade: centred on the arm tip, lying along the arm direction rotated slightly
    fill(u.blade, t => {
      return { lat: tip.lat - dir.lat * u.bladeL * 0.5 + dir.lat * u.bladeL * t, up: tip.up - dir.up * u.bladeL * 0.5 + dir.up * u.bladeL * t,
        wl: nrm.lat * 0.01, wu: nrm.up * 0.01 };
    }, 0.006, 0.006, 0.014, 0.014, 0.001);
    const P = this.surf(piv.lat, piv.up, 0.012).p;
    u.cap.position.set(P.x, P.z, -P.y);
    const n = this.surf(piv.lat, piv.up).n;
    u.cap.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), new THREE.Vector3(n.x, n.z, -n.y));
  }
}
