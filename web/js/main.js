import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { loadPacked } from './loader.js';
import { createLibrary, materialFor, setTrim, AO, KEY } from './materials.js';
import { Environment } from './env.js';
import { Car, Wipers } from './car.js';
import { Lamps } from './lamps.js';
import { Cluster, ConsoleDisplays } from './dash.js';
import { VehicleSim } from './sim.js';
import { CarAudio } from './audio.js';
import { CameraRig } from './cameras.js';
import { bindUI } from './ui.js';

const q = new URLSearchParams(location.search);
const STILL = q.has('still');
// phones / small GPUs: lower resolution, no planar reflection, smaller shadow maps
const LITE = q.has('lite') || (matchMedia('(pointer: coarse)').matches && Math.min(screen.width, screen.height) < 900);
const canvas = document.getElementById('view');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: false, powerPreference: 'high-performance', preserveDrawingBuffer: STILL });
const DPR = Math.min(devicePixelRatio || 1, STILL ? 1 : LITE ? 1.25 : 2);
renderer.setPixelRatio(DPR);
renderer.setSize(innerWidth, innerHeight);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.shadowMap.autoUpdate = false;
renderer.shadowMap.needsUpdate = true;
if ('transmissionResolutionScale' in renderer) renderer.transmissionResolutionScale = 0.6;

const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(35, innerWidth / innerHeight, 0.03, 600);
camera.position.set(5.4, 1.45, 4.5);

const lib = createLibrary();
window.lib = lib;
const env = new Environment(renderer, scene, { lite: LITE });

// --- post ---------------------------------------------------------------------------------
const rt = new THREE.WebGLRenderTarget(innerWidth * DPR, innerHeight * DPR, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, rt);
composer.setPixelRatio(DPR);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(innerWidth, innerHeight), 0.2, 0.55, 2.2);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// --- world ----------------------------------------------------------------------------------
const world = new THREE.Group();
scene.add(world);
const carRoot = new THREE.Group();
carRoot.name = 'CarRoot';
world.add(carRoot);
const road = makeRoad();
road.visible = false;

// black hide, as on the reference car (ref/studio)
const state = { env: 'studio', trim: 'black', drive: false, sound: false, cameraMode: 'orbit' };
let car, lamps, cluster, displays, rig, ui;
const sim = new VehicleSim();
const audio = new CarAudio();

function setLoad(p, msg) {
  document.getElementById('progress').style.setProperty('--p', p.toFixed(3));
  if (msg) document.getElementById('load-msg').textContent = msg;
}

async function init() {
  setLoad(0.02, 'Loading environment…');
  state.env = q.get('env') || 'studio';
  const envReady = env.set(state.env);
  const make = name => materialFor(lib, name);
  const body = await loadPacked('assets/car', make, p => setLoad(0.05 + p * 0.75, 'Loading body shell & cabin…'));
  setLoad(0.82, 'Loading wheels…');
  const wheels = await loadPacked('assets/wheels', make, p => setLoad(0.82 + p * 0.1));
  carRoot.add(body);
  const manifest = { windshield: { bx: 0.700, bz: 0.858, nx: 0.35754824, nz: 0.93389467, wrap: 0.15 } };  // tools/model/body.py WS_*
  car = new Car(body, wheels, manifest, lib);
  car.wipers = new Wipers(car.body, manifest.windshield, lib);
  const INTERIOR = /^(seat|dash|stack|end_vents|console|column|door_card|door_liner|body_trim|carpet|sills|sill_plates|parcel|bulkhead|rear_mirror|visor|buckles|belt|door_strap|steering|pedal|shift|handbrake|rear_window)/;
  carRoot.traverse(o => {
    if (o.isMesh && INTERIOR.test(o.name)) o.userData.interior = true;
    if (o.isMesh) {
      const tr = o.material.transparent || o.material.transmission > 0;
      // Tiny plate housings use baked contact shadows; shadow-map texels turn them into
      // oversized black blocks across the lettering.
      o.castShadow = !tr && !(o.material.name || '').startsWith('Lamp') && o.name !== 'plate_lights';
      o.receiveShadow = true;
    }
  });
  // Open gull-wing doors expose both sides of their glass; keep the inner face visible.
  const doorGlass = lib.Glass.clone();
  doorGlass.side = THREE.DoubleSide;
  doorGlass.onBeforeCompile = lib.Glass.onBeforeCompile;
  doorGlass.customProgramCacheKey = lib.Glass.customProgramCacheKey;
  body.traverse(o => { if (o.isMesh && /^(glass_door_|glass_toll_)/.test(o.name)) o.material = doorGlass; });
  // decals: normalise their (metre) box UVs into 0..1
  for (const nm of ['eng_decal', 'bay_panel', 'plate']) {
    let mesh = null; body.traverse(o => { if (o.isMesh && o.name === nm) mesh = o; });
    const uv = mesh?.geometry.attributes.uv;
    if (!uv) continue;
    if (nm === 'plate') {
      // the plate's box UVs mix in its thin edge faces: project it straight from behind instead
      // (glTF frame: z = car right, y = up; reads left to right seen from behind)
      const P = mesh.geometry.attributes.position;
      for (let i = 0; i < uv.count; i++) uv.setXY(i, P.getZ(i), P.getY(i));
    }
    let u0 = Infinity, u1 = -Infinity, v0 = Infinity, v1 = -Infinity;
    for (let i = 0; i < uv.count; i++) { u0 = Math.min(u0, uv.getX(i)); u1 = Math.max(u1, uv.getX(i)); v0 = Math.min(v0, uv.getY(i)); v1 = Math.max(v1, uv.getY(i)); }
    for (let i = 0; i < uv.count; i++) uv.setXY(i, (uv.getX(i) - u0) / (u1 - u0), (uv.getY(i) - v0) / (v1 - v0));
    uv.needsUpdate = true;
  }
  // brushed stainless: U and the tangent follow the car's length (DMC panels are brushed
  // front-to-back), V runs round the body's section (the angle about a line along the car at
  // mid height, scaled to about metres; the seam lies under the car). Its lines stay level on
  // faces that also lean forward or back, like the sail panels, where a plain height + width
  // coordinate tilts the grain. Faces that look forward or back (nose, tail, lamp surrounds) are
  // brushed across the car instead.
  body.updateMatrixWorld(true);
  body.traverse(o => {
    if (!o.isMesh || !['Stainless', 'BadgeAlu'].includes(o.material.name)) return;
    const g = o.geometry, P = g.attributes.position, N = g.attributes.normal, n = P.count;
    const M = o.matrixWorld, Mi = new THREE.Matrix4().copy(M).invert();
    const ax = new THREE.Vector3(1, 0, 0).transformDirection(Mi), az = new THREE.Vector3(0, 0, 1).transformDirection(Mi);
    // The nose uses a finish mask; the rear fascia has its own smooth painted material.
    const fascia = new Float32Array(n).fill(o.name === 'nose' ? 1 : 0);
    const uv = new Float32Array(n * 2), tan = new Float32Array(n * 4);
    const p = new THREE.Vector3(), nn = new THREE.Vector3(), nw = new THREE.Vector3(), t = new THREE.Vector3();
    for (let i = 0; i < n; i++) {
      p.fromBufferAttribute(P, i).applyMatrix4(M);
      nn.fromBufferAttribute(N, i);
      nw.copy(nn).transformDirection(M);
      const across = Math.abs(nw.x) > 0.72;
      uv[i * 2] = across ? p.z : p.x; uv[i * 2 + 1] = across ? p.y : 0.8 * Math.atan2(p.z, p.y - 0.55);
      t.copy(across ? az : ax).addScaledVector(nn, -nn.dot(across ? az : ax));
      if (t.lengthSq() < 1e-6) t.set(0, 1, 0).addScaledVector(nn, -nn.y);
      t.normalize();
      tan[i * 4] = t.x; tan[i * 4 + 1] = t.y; tan[i * 4 + 2] = t.z; tan[i * 4 + 3] = 1;
    }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.setAttribute('tangent', new THREE.BufferAttribute(tan, 4));
    g.setAttribute('fascia', new THREE.BufferAttribute(fascia, 1));
  });
  // meshes without baked AO get neutral attributes (the AO shader patch reads `ao`/`ao2`)
  carRoot.traverse(o => {
    if (!o.isMesh) return;
    const g = o.geometry, n = g.attributes.position.count;
    if (!g.attributes.ao) g.setAttribute('ao', new THREE.BufferAttribute(new Uint8Array(n).fill(255), 1, true));
    if (!g.attributes.ao2) g.setAttribute('ao2', g.attributes.ao);
  });
  lamps = new Lamps(car, scene);
  cluster = new Cluster(car.nodes.gauge, lib);
  displays = new ConsoleDisplays(car.nodes.clock, car.nodes.radio);
  rig = new CameraRig(camera, canvas, car);
  env.contact.attach(carRoot);
  wirePanelEvents();
  lamps.onTick = on => audio.relay(on);
  await envReady;
  setLoad(0.96, 'Compiling shaders…');
  await new Promise(r => {
    const M = THREE.DefaultLoadingManager;
    const t = setTimeout(r, 15000);
    if (!M.itemsTotal || M.itemsTotal <= M.itemsLoaded) { clearTimeout(t); r(); } else M.onLoad = () => { clearTimeout(t); r(); };
  });
  setTrimColor(state.trim);
  ui = bindUI({ car, sim, lamps, audio, rig, env, state, setEnv, setTrimColor, setDrive, toggleSound });
  applyEnvPreset();
  env.contact.update(scene, carRoot);
  renderer.compile(scene, camera);
  setLoad(1, 'Ready');
  document.getElementById('loader').classList.add('done');
  setTimeout(() => { document.title = 'READY'; }, 200);
}

function wirePanelEvents() {
  for (const p of Object.values(car.panels)) {
    p.onEvent = (ev, v) => {
      if (ev === 'unlatch') audio.unlatch();
      if (ev === 'latch') { audio.latch(Math.min(1, (v || 0) / 1.5)); contactDirty = true; }
      ui?.refresh();
    };
  }
}

async function setEnv(name) {
  state.env = name;
  await env.set(name);
  shadowFrames = 4;
  applyEnvPreset();
  contactDirty = true;
}
function applyEnvPreset() {
  const P = env.preset;
  bloom.strength = P.bloom;
  bloom.threshold = state.env === 'night' ? 1.4 : 2.4;
  KEY.spec.value = P.keySpec ?? 1;
}
function setTrimColor(name) { state.trim = name; setTrim(lib, name); }
function setDrive(on) {
  state.drive = on;
  sim.drive = on;
  env.setDriving(on);
  if (on && state.env === 'studio') { setEnv('day').then(() => ui?.refresh()); }
  if (!on) { sim.x = sim.z = sim.yaw = 0; sim.speed = 0; }
}
async function toggleSound(on) {
  state.sound = on;
  if (on) await audio.start(); else audio.stop();
}

// --- road for drive mode: world-fixed texture, recentred under the car -----------------------
function makeRoad() {
  const c = document.createElement('canvas');
  c.width = c.height = 1024;
  const g = c.getContext('2d');
  const img = g.createImageData(1024, 1024);
  let seed = 7;
  const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647;
  for (let i = 0; i < 1024 * 1024; i++) {
    const v = 52 + rnd() * 26 + (rnd() < 0.02 ? 30 : 0);
    img.data[i * 4] = v; img.data[i * 4 + 1] = v; img.data[i * 4 + 2] = v * 1.02; img.data[i * 4 + 3] = 255;
  }
  g.putImageData(img, 0, 0);
  g.fillStyle = 'rgba(235,225,190,0.85)';
  for (let x = 0; x < 1024; x += 128) g.fillRect(x, 508, 64, 8);
  g.fillStyle = 'rgba(240,240,240,0.8)';
  g.fillRect(0, 300, 1024, 6); g.fillRect(0, 718, 1024, 6);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(10, 10);
  t.anisotropy = 8;
  const m = new THREE.MeshStandardMaterial({ map: t, roughness: 0.9, metalness: 0, transparent: true, depthWrite: false });
  m.onBeforeCompile = sh => {
    sh.uniforms.uCenter = { value: new THREE.Vector2() };
    m.userData.uCenter = sh.uniforms.uCenter;
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP;')
      .replace('#include <worldpos_vertex>', '#include <worldpos_vertex>\nvWP = (modelMatrix * vec4(transformed,1.)).xyz;');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying vec3 vWP; uniform vec2 uCenter;')
      .replace('#include <opaque_fragment>', '#include <opaque_fragment>\ngl_FragColor.a *= 1.0 - smoothstep(22.0, 60.0, length(vWP.xz - uCenter));');
  };
  const mesh = new THREE.Mesh(new THREE.PlaneGeometry(240, 240), m);
  mesh.rotation.x = -Math.PI / 2;
  mesh.position.y = 0.0008;
  mesh.receiveShadow = true;
  return mesh;
}

// --- loop -------------------------------------------------------------------------------------
let contactDirty = true, lastContact = 0, shadowFrames = 8;
const clock = new THREE.Clock();
const sunDir = new THREE.Vector3();
function frame() {
  // keep real time on slow GPUs: sub-step long frames (up to 0.25 s per rendered frame)
  const total = Math.min(Math.max(clock.getDelta(), 1 / 240), 0.25);
  const n = Math.ceil(total / 0.034);
  update.skipRender = true;
  for (let i = 0; i < n - 1; i++) update(total / n);
  update.skipRender = false;
  update(total / n);
  env.follow(camera, carRoot);
  composer.render();
}

function update(dt) {
  if (car && ui) {
    ui.input(dt);
    sim.loadAmps = lamps.load();
    sim.step(dt);
    car.steerWheelAngle = ui.steer;
    sim.steer = car.steerWheelAngle / car.steerRatio;
    car.gear = sim.gear; car.handbrake = sim.handbrake;
    car.pedal.gas = sim.throttle; car.pedal.brake = sim.brake; car.pedal.clutch = sim.clutch;
    car.update(dt, sim);
    AO.open.value = Math.max(car.doorL.amount, car.doorR.amount);
    // drive mode: move the car; keep backdrop helpers centred on it
    carRoot.position.set(sim.x, 0, sim.z);
    carRoot.rotation.y = sim.yaw;
    env.floor.mesh.position.set(sim.x, 0, sim.z);
    env.catcher.position.set(sim.x, 0.001, sim.z);
    env.lampGround.position.set(sim.x, 0.0015, sim.z);
    env.sunTarget.position.set(sim.x, 0, sim.z);
    sunDir.set(...env.preset.sun.dir).normalize();
    env.sun.position.copy(env.sunTarget.position).addScaledVector(sunDir, 15);
    if (road.visible) {
      const P = 24;
      road.position.x = Math.round(sim.x / P) * P; road.position.z = Math.round(sim.z / P) * P;
      road.material.userData.uCenter?.value.set(sim.x, sim.z);
    }
    if (rig.mode === 'orbit' && state.drive) {
      const d = new THREE.Vector3(sim.x, 0.6, sim.z).sub(rig.orbit.target);
      rig.orbit.target.add(d); camera.position.add(d);
    }
    const lst = lamps.update(dt, sim);
    const beamsOn = lamps.lights.lowL.intensity > 1 || lamps.lights.highL.intensity > 1;
    if (beamsOn !== update.beamsOn) { update.beamsOn = beamsOn; shadowFrames = Math.max(shadowFrames, 3); }
    const doorAjar = car.doorL.theta > 0.02 || car.doorR.theta > 0.02 || !car.hood.latched || !car.lid.latched;
    const bulb = sim.bulbCheck > 0;
    const on = sim.electrics;
    cluster.setLamps({
      brake: on && (bulb || sim.handbrake > 0.5), oil: on && (bulb || sim.oil < 0.35), charge: on && (bulb || !sim.running),
      door: on && (bulb || doorAjar), turnL: lst.turnL, turnR: lst.turnR, high: lst.high, fuel: on && (bulb || sim.fuel < 0.12),
    }, lst.panel && on);
    cluster.update(dt, sim, lst);
    displays.update(sim, true);
    rig.update(dt);
    const strut = Object.values(car.panels).reduce((a, p) => a + (p.moving ? Math.min(1, Math.abs(p.omega)) : 0), 0);
    const doorOpen = Math.max(car.doorL.amount, car.doorR.amount);
    audio.update(sim, { inside: rig.inside, doorOpen, wiper: car.wipers.motorLoad, strut, engineDistance: 1 });
    for (const e of sim.events.splice(0)) { if (e === 'crank') audio.key(); if (e === 'ignOn') audio.switchClick(); }
    const panelsMoving = Object.values(car.panels).some(p => p.moving) || car.tollMoving;
    const moving = panelsMoving || Math.abs(sim.speed) > 0.01;
    // shadows only re-render when something moves (or a few frames after)
    if (moving || shadowFrames > 0 || car.wipers.running) renderer.shadowMap.needsUpdate = true;
    shadowFrames = moving ? 4 : Math.max(0, shadowFrames - 1);
    const now = performance.now();
    if ((panelsMoving || contactDirty) && now - lastContact > 120 && !update.skipRender) { env.contact.update(scene, carRoot); lastContact = now; contactDirty = panelsMoving; }
    if (!update.skipRender) env.floor.update(scene, camera);
    ui.hud();
  }
}
// advance the simulation without rendering (used by tests / screenshots)
function tick(n = 1, dt = 1 / 60) { update.skipRender = true; for (let i = 0; i < n; i++) update(dt); update.skipRender = false; }

window.view = (c, t, f, mode) => {
  if (mode && rig) rig.setMode(mode, true);
  if (rig && rig.mode === 'orbit') { rig.orbit.target.set(...t); camera.position.set(...c); rig.fov = f; camera.fov = f; rig.tween = null; }
  camera.updateProjectionMatrix();
  frame();
};
window.THREE = THREE;
window.app = { tick, get cluster() { return cluster; }, get displays() { return displays; }, composer, rt, bloom, get car() { return car; }, sim, get lamps() { return lamps; }, get rig() { return rig; }, get ui() { return ui; }, setEnv, frame, state, setTrimColor, setDrive, env, scene, camera, renderer };

addEventListener('resize', () => {
  camera.aspect = innerWidth / innerHeight; camera.updateProjectionMatrix();
  renderer.setSize(innerWidth, innerHeight); composer.setSize(innerWidth, innerHeight);
  bloom.resolution.set(innerWidth, innerHeight);
});

init().catch(e => { console.error(e); document.getElementById('err').textContent = 'Could not load the car: ' + e.message; });
if (!STILL) renderer.setAnimationLoop(frame);
