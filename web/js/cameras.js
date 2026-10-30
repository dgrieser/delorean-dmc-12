// Camera modes: orbit, free roam, driver, passenger, cinematic. Smooth transitions.
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const EYE = { driver: new THREE.Vector3(-0.44, 0.985, -0.37), passenger: new THREE.Vector3(-0.44, 0.975, 0.37) };

export class CameraRig {
  constructor(camera, dom, car) {
    this.camera = camera;
    this.dom = dom;
    this.car = car;
    this.mode = 'orbit';
    this.orbit = new OrbitControls(camera, dom);
    this.orbit.target.set(0, 0.6, 0);
    this.orbit.enableDamping = true;
    this.orbit.dampingFactor = 0.07;
    this.orbit.maxPolarAngle = Math.PI * 0.497;
    this.orbit.minDistance = 0.6;
    this.orbit.maxDistance = 18;
    this.orbit.zoomSpeed = 0.8;
    this.yaw = 0; this.pitch = 0; this.fov = 50;
    this.keys = {};
    this.vel = new THREE.Vector3();
    this.tween = null;
    this.pointers = new Map();
    this.cine = { t: 0 };
    this.headOffset = new THREE.Vector3();
    this.inside = false;
    const down = e => {
      if (this.mode === 'orbit' || this.mode === 'cinematic') return;
      if (e.button !== 0 && e.pointerType === 'mouse') return;
      this.tween = null;
      this.pointers.set(e.pointerId, [e.clientX, e.clientY]);
      dom.setPointerCapture?.(e.pointerId);
    };
    const move = e => {
      if (!this.pointers.has(e.pointerId)) return;
      const before = [...this.pointers.values()];
      const last = this.pointers.get(e.pointerId);
      const dx = e.clientX - last[0], dy = e.clientY - last[1];
      this.pointers.set(e.pointerId, [e.clientX, e.clientY]);
      if (this.pointers.size === 2) {
        const after = [...this.pointers.values()];
        const span = p => Math.hypot(p[0][0] - p[1][0], p[0][1] - p[1][1]);
        const oldSpan = span(before), newSpan = span(after);
        if (oldSpan < 8 || newSpan < 8) return;
        if (this.mode === 'free') {
          const cam = this.camera;
          const centre = this.car.body.getWorldPosition(new THREE.Vector3());
          const distance = this.inside ? .5 : THREE.MathUtils.clamp(cam.position.distanceTo(centre) - 1.3, .5, 8);
          const pixel = 2 * distance * Math.tan(THREE.MathUtils.degToRad(this.fov / 2)) / Math.max(1, dom.clientHeight);
          const panX = (after[0][0] + after[1][0] - before[0][0] - before[1][0]) / 2;
          const panY = (after[0][1] + after[1][1] - before[0][1] - before[1][1]) / 2;
          const offset = new THREE.Vector3(-panX * pixel, panY * pixel, -Math.log(newSpan / oldSpan) * distance);
          cam.position.add(offset.applyQuaternion(cam.quaternion));
          cam.position.y = Math.max(.12, cam.position.y);
          this.vel.set(0, 0, 0);
        } else {
          this.fov = THREE.MathUtils.clamp(this.fov * oldSpan / newSpan, 14, 80);
        }
        return;
      }
      if (this.pointers.size !== 1) return;
      const s = 0.0032 * (this.fov / 50);
      this.yaw -= dx * s; this.pitch -= dy * s;
      this.clampLook();
    };
    const up = e => { this.pointers.delete(e.pointerId); };
    dom.addEventListener('pointerdown', down);
    addEventListener('pointermove', move);
    addEventListener('pointerup', up);
    addEventListener('pointercancel', up);
    dom.addEventListener('lostpointercapture', up);
    dom.addEventListener('wheel', e => {
      if (this.mode === 'driver' || this.mode === 'passenger' || this.mode === 'free') {
        e.preventDefault();
        this.fov = Math.min(80, Math.max(14, this.fov * Math.exp(e.deltaY * 0.0012)));
      }
    }, { passive: false });
    addEventListener('keydown', e => { if (!e.target.closest?.('input,select,textarea')) this.keys[e.code] = true; });
    addEventListener('keyup', e => { this.keys[e.code] = false; });
    addEventListener('blur', () => { this.keys = {}; this.resetInput(); });
  }

  resetInput() {
    const ids = [...this.pointers.keys()];
    this.pointers.clear();
    for (const id of ids) if (this.dom.hasPointerCapture?.(id)) this.dom.releasePointerCapture(id);
    this.vel.set(0, 0, 0);
  }

  clampLook() {
    if (this.mode === 'driver' || this.mode === 'passenger') {
      this.yaw = Math.max(-2.3, Math.min(2.3, this.yaw));
      this.pitch = Math.max(-1.1, Math.min(0.9, this.pitch));
    } else this.pitch = Math.max(-1.5, Math.min(1.5, this.pitch));
  }

  // world transform of the car body (seat views ride with the sprung body)
  bodyMatrix() { this.car.body.updateMatrixWorld(); return this.car.body.matrixWorld; }

  setMode(mode, instant = false) {
    this.resetInput();
    this.tween = null;
    const cam = this.camera;
    const from = { p: cam.position.clone(), q: cam.quaternion.clone(), fov: cam.fov };
    this.mode = mode;
    this.orbit.enabled = mode === 'orbit';
    if (mode === 'driver' || mode === 'passenger') { this.yaw = 0; this.pitch = -0.12; this.fov = 52; }
    if (mode === 'free') {
      const e = new THREE.Euler().setFromQuaternion(cam.quaternion, 'YXZ');
      this.yaw = e.y; this.pitch = e.x; this.fov = cam.fov;
    }
    if (mode === 'orbit') {
      const fwd = new THREE.Vector3(0, 0, -1).applyQuaternion(cam.quaternion);
      const p = cam.position.clone();
      if (p.length() < 2.5) { cam.position.set(5.2, 1.5, 4.4); }
      this.orbit.target.set(0, 0.6, 0);
      this.fov = 35;
    }
    if (mode === 'cinematic') { this.cine.t = 0; this.fov = 32; }
    if (!instant) this.tween = { from, t: 0, dur: 1.1 };
  }

  goto(pos, target, fov = 35) {
    this.resetInput();
    // orbit preset shots (engine bay, trunk, wheel, dash...)
    const cam = this.camera;
    const from = { p: cam.position.clone(), q: cam.quaternion.clone(), fov: cam.fov };
    this.mode = 'orbit'; this.orbit.enabled = true;
    this.orbit.target.copy(target);
    cam.position.copy(pos);
    this.fov = fov;
    this.tween = { from, t: 0, dur: 1.3 };
  }

  update(dt) {
    const cam = this.camera;
    const k = this.keys;
    if (this.mode === 'orbit') {
      this.orbit.update();
      cam.fov += (this.fov - cam.fov) * Math.min(1, dt * 6);
    } else if (this.mode === 'free') {
      const sp = (k.ShiftLeft || k.ShiftRight ? 5 : 1.4);
      const f = new THREE.Vector3(-Math.sin(this.yaw), 0, -Math.cos(this.yaw));
      const r = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));
      const want = new THREE.Vector3();
      if (k.KeyW) want.add(f); if (k.KeyS) want.sub(f);
      if (k.KeyD) want.add(r); if (k.KeyA) want.sub(r);
      if (k.KeyE || k.Space) want.y += 1; if (k.KeyQ || k.KeyC) want.y -= 1;
      if (want.lengthSq() > 0) want.normalize().multiplyScalar(sp);
      this.vel.lerp(want, Math.min(1, dt * 8));
      cam.position.addScaledVector(this.vel, dt);
      cam.position.y = Math.max(0.12, cam.position.y);
      cam.quaternion.setFromEuler(new THREE.Euler(this.pitch, this.yaw, 0, 'YXZ'));
      cam.fov += (this.fov - cam.fov) * Math.min(1, dt * 8);
    } else if (this.mode === 'driver' || this.mode === 'passenger') {
      const M = this.bodyMatrix();
      const eye = EYE[this.mode].clone().add(this.headOffset).applyMatrix4(M);
      cam.position.copy(eye);
      const bq = new THREE.Quaternion().setFromRotationMatrix(M);
      // base look direction: forward (+X) => camera yaw -90deg
      const look = new THREE.Quaternion().setFromEuler(new THREE.Euler(this.pitch, -Math.PI / 2 + this.yaw, 0, 'YXZ'));
      cam.quaternion.copy(bq).multiply(look);
      cam.fov += (this.fov - cam.fov) * Math.min(1, dt * 8);
    } else if (this.mode === 'cinematic') {
      this.cine.t += dt;
      const t = this.cine.t;
      const a = t * 0.085 + 0.6;
      const r = 6.2 + Math.sin(t * 0.13) * 1.6;
      const h = 0.75 + (Math.sin(t * 0.07) * 0.5 + 0.5) * 1.3;
      cam.position.set(Math.cos(a) * r, h, Math.sin(a) * r);
      cam.lookAt(0, 0.55 + Math.sin(t * 0.11) * 0.08, 0);
      this.fov = 30 + Math.sin(t * 0.05) * 6;
      cam.fov += (this.fov - cam.fov) * Math.min(1, dt * 2);
    }
    // blend from the previous pose
    if (this.tween) {
      this.tween.t += dt / this.tween.dur;
      const e = this.tween.t >= 1 ? 1 : 1 - Math.pow(1 - this.tween.t, 3);
      const p = cam.position.clone(), q = cam.quaternion.clone();
      cam.position.lerpVectors(this.tween.from.p, p, e);
      cam.quaternion.slerpQuaternions(this.tween.from.q, q, e);
      cam.fov = this.tween.from.fov + (cam.fov - this.tween.from.fov) * e;
      if (this.tween.t >= 1) this.tween = null;
    }
    cam.updateProjectionMatrix();
    // inside the cabin? (for audio muffling and near plane)
    const local = this.car.body.worldToLocal(cam.position.clone());
    this.inside = local.x > -0.8 && local.x < 0.9 && Math.abs(local.z) < 0.78 && local.y > 0.25 && local.y < 1.1;
    cam.near = this.inside || this.mode === 'driver' || this.mode === 'passenger' ? 0.01 : 0.05;
  }
}
