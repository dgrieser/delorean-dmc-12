// Environment presets: studio / day / night. HDR lighting, grounded backdrop, sun,
// contact shadows, light-receiving ground (for the car's own lamps) and a glossy studio floor.
import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { fetchBinary } from './fetchbin.js';
import { HorizontalBlurShader } from 'three/addons/shaders/HorizontalBlurShader.js';
import { VerticalBlurShader } from 'three/addons/shaders/VerticalBlurShader.js';
import { GroundedSkybox } from 'three/addons/objects/GroundedSkybox.js';

// Day and night: photographic HDRIs (CC0, Poly Haven: driving_school, hansaplatz). The
// over-bright key light (sun / lamp) was clamped out of each map by tools/tex/prep_hdri.py; its
// measured direction and irradiance (assets/env/env.json) drive a shadow-casting DirectionalLight
// instead, and a ground-projected 4k backdrop shows the place. Studio: a procedural car studio
// (tools/tex/studio_env.py: overhead softbox, strip boxes, shaded floor) lights the car while a
// white cyclorama set is what the camera sees, as in the studio reference photos.
export const PRESETS = {
  studio: { hdr: 'studio.hdr', exposure: 0.62, envIntensity: 1.0, keyScale: 1.0, shadowRadius: 14, cyc: true, followCamera: true,
            ground: { kind: 'studio', color: [0.60, 0.60, 0.60], rough: 0.55, refl: 0.10, env: 1.0 }, bg: { color: [0.45, 0.45, 0.46] }, bloom: 0.12 },
  day: { hdr: 'day.hdr', exposure: 1.0, envIntensity: 1.0, keyScale: 1.0, shadowRadius: 2,
         backdrop: { jpg: 'day_bg.jpg', height: 1.65, radius: 140 },
         ground: { kind: 'asphalt', color: [0.62, 0.60, 0.58], rough: 0.92, refl: 0.0, env: 0.8 }, bg: { intensity: 1, blur: 0 }, bloom: 0.08, fog: [70, 480] },
  night: { hdr: 'night.hdr', exposure: 1.0, envIntensity: 1.0, keyScale: 0.8, shadowRadius: 5,
           backdrop: { jpg: 'night_bg.jpg', height: 1.65, radius: 90 },
           ground: { kind: 'asphalt', color: [0.34, 0.34, 0.35], rough: 0.55, refl: 0.0, env: 1.0 }, bg: { intensity: 1, blur: 0 }, bloom: 0.5, fog: [40, 380] },
};

// procedural asphalt (albedo detail + roughness variation), tiles every ASPH_TILE metres
const ASPH_TILE = 3.0;
function asphaltTextures() {
  const N = 1024;
  const c = document.createElement('canvas'); c.width = c.height = N;
  const g = c.getContext('2d');
  const img = g.createImageData(N, N);
  const r = document.createElement('canvas'); r.width = r.height = N;
  const gr = r.getContext('2d');
  const rimg = gr.createImageData(N, N);
  let s = 1234567;
  const rnd = () => ((s = (s * 1103515245 + 12345) >>> 0) / 4294967296);
  // value noise (periodic) for patches
  const P = 32, grid = new Float32Array(P * P).map(() => rnd());
  const vn = (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y), fx = x - xi, fy = y - yi;
    const a = grid[(yi % P) * P + (xi % P)], b = grid[(yi % P) * P + ((xi + 1) % P)];
    const cc = grid[((yi + 1) % P) * P + (xi % P)], d = grid[((yi + 1) % P) * P + ((xi + 1) % P)];
    const u = fx * fx * (3 - 2 * fx), v = fy * fy * (3 - 2 * fy);
    return a + (b - a) * u + (cc - a) * v + (a - b - cc + d) * u * v;
  };
  for (let y = 0; y < N; y++) for (let x = 0; x < N; x++) {
    const patch = vn(x / N * P, y / N * P) * 0.6 + vn(x / N * P * 0.25 % P, y / N * P * 0.25 % P) * 0.4;
    const grain = rnd();
    const stone = grain > 0.985 ? 1.6 : grain > 0.93 ? 1.25 : grain < 0.05 ? 0.55 : 1.0;
    const v = Math.min(255, (120 + patch * 50 - 25) * stone * (0.85 + rnd() * 0.3));
    const i = (y * N + x) * 4;
    img.data[i] = v; img.data[i + 1] = v; img.data[i + 2] = v * 1.03; img.data[i + 3] = 255;
    const rv = Math.min(255, 150 + (1 - patch) * 70 + (stone > 1.2 ? -60 : 0) + rnd() * 30);
    rimg.data[i] = rv; rimg.data[i + 1] = rv; rimg.data[i + 2] = rv; rimg.data[i + 3] = 255;
  }
  g.putImageData(img, 0, 0); gr.putImageData(rimg, 0, 0);
  const mk = (cv, srgb) => { const t = new THREE.CanvasTexture(cv); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace; return t; };
  return { map: mk(c, true), rough: mk(r, false) };
}

// painted parking-bay lines around the car (decal plane)
function bayLines() {
  const c = document.createElement('canvas'); c.width = 1024; c.height = 512;
  const g = c.getContext('2d');
  g.clearRect(0, 0, 1024, 512);
  g.fillStyle = 'rgba(236,232,220,0.92)';
  const L = 1024 / 7.0;          // px per metre (7 m x 3.5 m decal)
  g.fillRect(0.5 * L, 0.25 * L, 6.0 * L, 0.12 * L);           // side lines along the car
  g.fillRect(0.5 * L, 3.13 * L, 6.0 * L, 0.12 * L);
  g.fillRect(0.5 * L, 0.25 * L, 0.12 * L, 3.0 * L);            // front/back stop line
  const img = g.getImageData(0, 0, 1024, 512);
  for (let i = 0; i < img.data.length; i += 4) if (img.data[i + 3] > 0) img.data[i + 3] *= 0.75 + Math.random() * 0.25;
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(7, 3.5), new THREE.MeshStandardMaterial({ map: t, transparent: true, roughness: 0.7, depthWrite: false, polygonOffset: true, polygonOffsetFactor: -2 }));
  m.rotation.x = -Math.PI / 2;
  m.position.set(-0.4, 0.002, 0);
  m.receiveShadow = true;
  m.renderOrder = 1;
  return m;
}

export class Environment {
  get presets() { return PRESETS; }
  constructor(renderer, scene, opts = {}) {
    this.lite = !!opts.lite;
    this.renderer = renderer;
    this.scene = scene;
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.cache = {};
    this.group = new THREE.Group();
    scene.add(this.group);
    this.meta = fetch('assets/env/env.json').then(r => r.json()).catch(() => ({}));
    this.meta.then(m => { this.metaCache = m; });

    // key light (sun / lamp / softbox), shadow casting
    this.sun = new THREE.DirectionalLight(0xffffff, 3);
    this.sun.castShadow = true;
    const s = this.sun.shadow;
    s.mapSize.set(opts.lite ? 2048 : 4096, opts.lite ? 2048 : 4096);
    s.camera.left = -3.6; s.camera.right = 3.6; s.camera.top = 3.6; s.camera.bottom = -3.6;
    s.camera.near = 0.5; s.camera.far = 40;
    s.bias = -0.00015; s.normalBias = 0.015; s.radius = 3;
    this.sunTarget = new THREE.Object3D();
    this.sun.target = this.sunTarget;
    scene.add(this.sun, this.sunTarget);

    // studio floor / drive-mode asphalt: lit ground with optional planar reflection
    this.asphalt = asphaltTextures();
    this.floor = makeGlossFloor(renderer);
    this.group.add(this.floor.mesh);
    this.cyc = makeCyc();
    this.group.add(this.cyc);
    this.bay = bayLines();
    this.bay.visible = false;
    this.group.add(this.bay);

    // projected backdrop scenes: shadow catcher + a ground that only the car's own lamps light
    const cm = new THREE.ShadowMaterial({ opacity: 0.6, color: 0x000000, depthWrite: false });
    cm.onBeforeCompile = sh => {
      // only the key light's shadow: the headlight spots' maps must not darken the photo ground
      sh.fragmentShader = sh.fragmentShader.replace('#include <shadowmask_pars_fragment>',
        THREE.ShaderChunk.shadowmask_pars_fragment.replace('#if NUM_SPOT_LIGHT_SHADOWS > 0', '#if 0').replace('#if NUM_POINT_LIGHT_SHADOWS > 0', '#if 0'));
    };
    this.catcher = new THREE.Mesh(new THREE.CircleGeometry(30, 64), cm);
    this.catcher.rotation.x = -Math.PI / 2;
    this.catcher.position.y = 0.001;
    this.catcher.receiveShadow = true;
    this.catcher.renderOrder = 1;
    this.group.add(this.catcher);
    const lg = new THREE.MeshStandardMaterial({ color: new THREE.Color().setRGB(0.09, 0.09, 0.095, THREE.LinearSRGBColorSpace), roughness: 0.5,
      envMapIntensity: 0, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false });
    lg.onBeforeCompile = sh => {
      // directional (sun / lamp) light is already in the photo: only spot + point lights add
      sh.fragmentShader = sh.fragmentShader.replace('#include <lights_fragment_begin>',
        THREE.ShaderChunk.lights_fragment_begin.replace('#if ( NUM_DIR_LIGHTS > 0 ) && defined( RE_Direct )', '#if 0'));
    };
    this.lampGround = new THREE.Mesh(new THREE.CircleGeometry(40, 64), lg);
    this.lampGround.rotation.x = -Math.PI / 2;
    this.lampGround.position.y = 0.0015;
    this.lampGround.renderOrder = 2;
    this.group.add(this.lampGround);
    this.shadowPlane = this.catcher;

    this.contact = new ContactShadow(renderer, 6.0, 3.2, 1024);
    this.group.add(this.contact.mesh);
    this.skybox = null;
    this.current = null;
    this.driving = false;
  }

  async load(name) {
    if (this.cache[name]) return this.cache[name];
    const P = PRESETS[name];
    const buf = await fetchBinary('assets/env/' + P.hdr);
    const d = new RGBELoader().setDataType(THREE.HalfFloatType).parse(buf);
    const hdr = new THREE.DataTexture(d.data, d.width, d.height, THREE.RGBAFormat, d.type);
    hdr.colorSpace = THREE.LinearSRGBColorSpace;
    hdr.minFilter = hdr.magFilter = THREE.LinearFilter;
    hdr.generateMipmaps = false;
    hdr.flipY = true;
    hdr.needsUpdate = true;
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    const env = this.pmrem.fromEquirectangular(hdr).texture;
    let bg = null;
    if (P.backdrop) {
      bg = await new THREE.TextureLoader().loadAsync('assets/env/' + P.backdrop.jpg);
      bg.colorSpace = THREE.SRGBColorSpace;
      bg.mapping = THREE.EquirectangularReflectionMapping;
      bg.anisotropy = 8;
    }
    this.cache[name] = { hdr, env, bg };
    return this.cache[name];
  }

  async set(name, extras = {}) {
    const P = PRESETS[name];
    const [{ hdr, env, bg }, meta] = await Promise.all([this.load(name), this.meta]);
    const M = P.metaOverride || meta[name] || {};
    const scene = this.scene;
    scene.environment = env;
    scene.environmentIntensity = P.envIntensity;
    this.renderer.toneMappingExposure = P.exposure * (extras.exposureScale || 1);
    // key light from the measured HDR data
    let kd = new THREE.Vector3(...(M.keyDir || [0.3, 0.9, 0.3])).normalize();
    // optionally turn the panorama so the key light falls on the default view (studio)
    let rot = 0;
    if (P.keyAzimuth !== undefined) rot = Math.atan2(kd.z, kd.x) - P.keyAzimuth * Math.PI / 180;
    scene.environmentRotation.set(0, rot, 0);
    scene.backgroundRotation.set(0, rot, 0);
    kd.applyAxisAngle(new THREE.Vector3(0, 1, 0), rot);
    kd = kd.toArray();
    const E = M.keyIrradiance || [3, 3, 3];
    const lumE = E[0] * 0.2126 + E[1] * 0.7152 + E[2] * 0.0722;
    P.sun = { dir: kd };
    this.sun.color.setRGB(E[0] / lumE, E[1] / lumE, E[2] / lumE, THREE.LinearSRGBColorSpace);
    this.sun.intensity = lumE * P.keyScale;
    this.sun.shadow.radius = P.shadowRadius;
    this.sun.position.copy(new THREE.Vector3(...kd)).multiplyScalar(15);
    this.current = name;
    this.preset = P;
    this.bgTex = bg;
    this.hdrTex = hdr;
    this.applyGround();
    return P;
  }

  setDriving(on) { this.driving = on; if (this.preset) this.applyGround(); }

  // The studio rig is authored relative to the camera (+X of the map = towards the camera), as
  // on a turntable shoot: turn the reflections with the camera's azimuth round the car.
  follow(camera, target) {
    if (!this.preset?.followCamera || this.driving) return;
    const dx = camera.position.x - target.x, dz = camera.position.z - target.z;
    if (dx * dx + dz * dz < 1e-6) return;
    this.scene.environmentRotation.y = Math.atan2(-dz, dx);
  }

  applyGround() {
    const P = this.preset, scene = this.scene;
    const projected = !!(P.backdrop && this.bgTex && !this.driving);
    if (this.skybox) { this.group.remove(this.skybox); this.skybox.geometry.dispose(); this.skybox.material.dispose(); this.skybox = null; }
    if (projected) {
      const B = P.backdrop;
      this.skybox = new GroundedSkybox(this.bgTex, B.height, B.radius, 96);
      this.skybox.position.y = B.height - 0.001;
      // the jpeg holds srgb(L * k): scale back to scene radiance so exposure / tone mapping match
      const k = 1 / ((P.metaOverride?.backdropScale) || (this.metaCache?.[this.current]?.backdropScale) || (this.current === 'day' ? 0.32 : 1.6));
      this.skybox.material.color.setScalar(k);
      this.skybox.renderOrder = -1;
      this.group.add(this.skybox);
      scene.background = null;
      scene.fog = null;
    } else if (P.cyc && !this.driving) {
      scene.background = new THREE.Color().setRGB(...P.bg.color, THREE.LinearSRGBColorSpace);
      scene.fog = null;
    } else {
      scene.background = this.hdrTex;
      scene.backgroundBlurriness = P.bg.blur ?? 0;
      scene.backgroundIntensity = P.bg.intensity ?? 1;
      if (P.fog && this.driving) {
        const hc = horizonColor(this.hdrTex);
        scene.fog = new THREE.Fog(new THREE.Color().setRGB(hc[0], hc[1], hc[2], THREE.LinearSRGBColorSpace), P.fog[0], P.fog[1]);
      } else scene.fog = null;
    }
    // floor: studio gloss always; asphalt only while driving through a projected scene
    const G = P.ground, fm = this.floor.mesh.material;
    const showFloor = G.kind === 'studio' || !projected;
    this.floor.mesh.visible = showFloor;
    fm.color.setRGB(...G.color, THREE.LinearSRGBColorSpace);
    fm.roughness = G.rough;
    fm.envMapIntensity = G.env;
    const asph = G.kind === 'asphalt';
    fm.map = asph ? this.asphalt.map : null;
    fm.roughnessMap = asph ? this.asphalt.rough : null;
    fm.needsUpdate = true;
    this.floor.uniforms.uReflStrength.value = this.lite ? 0 : G.refl;
    this.floor.uniforms.uWorldUV.value = asph ? 1 / ASPH_TILE : 0;
    this.cyc.visible = !!P.cyc && !this.driving;
    this.catcher.visible = projected;
    this.catcher.material.opacity = this.current === 'night' ? 0.45 : 0.62;
    this.lampGround.visible = projected && this.current === 'night';
    this.bay.visible = false;
  }
}

// average radiance in a thin band just below the horizon of an equirect HDR texture
function horizonColor(hdr) {
  const { data, width, height } = hdr.image;
  const half = hdr.type === THREE.HalfFloatType;
  const get = i => half ? THREE.DataUtils.fromHalfFloat(data[i]) : data[i];
  const acc = [0, 0, 0];
  let n = 0;
  for (let y = Math.floor(height * 0.505); y < Math.floor(height * 0.53); y++) {
    for (let x = 0; x < width; x += 4) {
      const i = (y * width + x) * 4;
      acc[0] += get(i); acc[1] += get(i + 1); acc[2] += get(i + 2); n++;
    }
  }
  return acc.map(v => v / n);
}

// ----------------------------------------------------------------------------------------------
// Contact shadow: orthographic depth render of the car from below, blurred, multiplied on ground
class ContactShadow {
  constructor(renderer, w, h, res) {
    this.renderer = renderer;
    this.rt = new THREE.WebGLRenderTarget(res, res / 2);
    this.rt.texture.generateMipmaps = false;
    this.rtB = new THREE.WebGLRenderTarget(res, res / 2);
    this.cam = new THREE.OrthographicCamera(-w / 2, w / 2, h / 2, -h / 2, 0, 0.9);
    this.cam.rotation.x = Math.PI / 2;
    this.cam.position.y = 0.0;
    this.depthMat = new THREE.ShaderMaterial({
      uniforms: { uDark: { value: 1.0 } },
      vertexShader: 'varying float vH; void main(){ vec4 w = modelMatrix*vec4(position,1.); vH = w.y; gl_Position = projectionMatrix*viewMatrix*w; }',
      fragmentShader: 'varying float vH; uniform float uDark; void main(){ float a = clamp(1.0 - vH/0.55, 0., 1.); a = a*a; gl_FragColor = vec4(0.,0.,0., a*uDark); }',
      side: THREE.DoubleSide, depthTest: false, transparent: true, blending: THREE.CustomBlending,
      blendEquation: THREE.MaxEquation, blendSrc: THREE.OneFactor, blendDst: THREE.OneFactor,
    });
    this.hBlur = new THREE.ShaderMaterial(HorizontalBlurShader);
    this.vBlur = new THREE.ShaderMaterial(VerticalBlurShader);
    this.hBlur.depthTest = this.vBlur.depthTest = false;
    this.quad = new THREE.Mesh(new THREE.PlaneGeometry(2, 2));
    this.quadScene = new THREE.Scene();
    this.quadScene.add(this.quad);
    this.quadCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
    const mat = new THREE.MeshBasicMaterial({ map: this.rt.texture, transparent: true, opacity: 0.9, depthWrite: false, color: 0x000000 });
    mat.onBeforeCompile = sh => {
      sh.fragmentShader = sh.fragmentShader.replace('#include <map_fragment>',
        'vec4 sampledDiffuseColor = texture2D( map, vMapUv ); diffuseColor = vec4(0.0,0.0,0.0, sampledDiffuseColor.a);');
    };
    this.mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), mat);
    this.mesh.rotation.x = -Math.PI / 2;
    this.mesh.position.y = 0.0025;
    this.mesh.renderOrder = 2;
    this.strength = 1;
  }

  update(scene, target) {
    const r = this.renderer;
    const prevRT = r.getRenderTarget(), prevBG = scene.background, prevOv = scene.overrideMaterial;
    const prevClear = r.getClearAlpha();
    const vis = [];
    scene.traverse(o => { if (o.visible && o.isMesh && !o.userData.castsContact) { vis.push(o); } });
    for (const o of vis) o.visible = false;
    target.traverse(o => { if (o.isMesh && o.userData.contact !== false && !o.material.transparent && !o.material.transmission) o.visible = true; });
    scene.background = null;
    scene.overrideMaterial = this.depthMat;
    r.setClearColor(0x000000, 0);
    this.cam.updateMatrixWorld();
    r.setRenderTarget(this.rt);
    r.clear();
    r.render(scene, this.cam);
    scene.overrideMaterial = prevOv;
    scene.background = prevBG;
    target.traverse(o => { if (o.isMesh) o.visible = false; });
    for (const o of vis) o.visible = true;
    // blur passes
    for (let i = 0; i < 3; i++) {
      this.quad.material = this.hBlur; this.hBlur.uniforms.tDiffuse.value = this.rt.texture; this.hBlur.uniforms.h.value = (1.5 + i) / 1024;
      r.setRenderTarget(this.rtB); r.render(this.quadScene, this.quadCam);
      this.quad.material = this.vBlur; this.vBlur.uniforms.tDiffuse.value = this.rtB.texture; this.vBlur.uniforms.v.value = (1.5 + i) / 512;
      r.setRenderTarget(this.rt); r.render(this.quadScene, this.quadCam);
    }
    r.setRenderTarget(prevRT);
    r.setClearAlpha(prevClear);
  }

  // ride along with the car: the footprint only changes when a panel moves
  attach(carRoot) { carRoot.add(this.mesh, this.cam); }
}

// ----------------------------------------------------------------------------------------------
// White cyclorama: floor-to-wall cove all round the car (a lathe profile), matte, lit by the
// studio environment like a real one. The reflective floor inside it stays the gloss floor.
function makeCyc() {
  const pts = [];
  const R0 = 16, cove = 4.0, top = 34;     // wall beyond the orbit camera's reach
  pts.push(new THREE.Vector2(R0 - 0.5, 0.0005));
  for (let i = 0; i <= 16; i++) {
    const a = (i / 16) * Math.PI / 2;
    pts.push(new THREE.Vector2(R0 + Math.sin(a) * cove, cove - Math.cos(a) * cove + 0.0005));
  }
  pts.push(new THREE.Vector2(R0 + cove, top));
  const geo = new THREE.LatheGeometry(pts, 96);
  const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color().setRGB(0.60, 0.60, 0.60, THREE.LinearSRGBColorSpace), roughness: 0.95, side: THREE.DoubleSide, envMapIntensity: 1.0 });
  const m = new THREE.Mesh(geo, mat);
  m.visible = false;
  return m;
}

// Floor with a blurred planar reflection of the scene (white cyc floor in the studio, asphalt
// while driving)
function makeGlossFloor(renderer) {
  const size = 60;
  const rtSize = new THREE.Vector2(768, 768);
  const rt = new THREE.WebGLRenderTarget(rtSize.x, rtSize.y, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
  const mat = new THREE.MeshStandardMaterial({ color: new THREE.Color().setRGB(0.012, 0.013, 0.015, THREE.LinearSRGBColorSpace), roughness: 0.3, metalness: 0, envMapIntensity: 0.22 });
  const uniforms = { tReflect: { value: rt.texture }, uReflMatrix: { value: new THREE.Matrix4() }, uReflStrength: { value: 0.55 }, uWorldUV: { value: 0 } };
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform mat4 uReflMatrix; varying vec4 vReflUv; uniform float uWorldUV;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvReflUv = uReflMatrix * modelMatrix * vec4( transformed, 1.0 );')
      .replace('#include <uv_vertex>', '#include <uv_vertex>\n#if defined( USE_MAP ) || defined( USE_ROUGHNESSMAP )\n{ vec3 wp = (modelMatrix * vec4(position, 1.0)).xyz; vec2 wuv = wp.xz * uWorldUV;\n#ifdef USE_MAP\nvMapUv = wuv;\n#endif\n#ifdef USE_ROUGHNESSMAP\nvRoughnessMapUv = wuv;\n#endif\n}\n#endif');
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', '#include <common>\nuniform sampler2D tReflect; uniform float uReflStrength; varying vec4 vReflUv;')
      .replace('#include <opaque_fragment>', `
        vec2 ruv = vReflUv.xy / vReflUv.w;
        vec3 refl = vec3(0.0);
        float lod = 2.2;
        refl += textureLod(tReflect, ruv, lod).rgb * 0.4;
        refl += textureLod(tReflect, ruv + vec2(0.0, 0.006), lod + 0.6).rgb * 0.3;
        refl += textureLod(tReflect, ruv + vec2(0.0, 0.014), lod + 1.2).rgb * 0.3;
        float fres = 0.04 + 0.96 * pow(1.0 - clamp(dot(normalize(vViewPosition), -normal) * -1.0, 0.0, 1.0), 5.0);
        float dist = length(vReflUv.xy / vReflUv.w - 0.5);
        outgoingLight += refl * uReflStrength * mix(0.12, 1.0, fres) * (1.0 - roughnessFactor * 0.6);
        #include <opaque_fragment>`);
  };
  const mesh = new THREE.Mesh(new THREE.CircleGeometry(450, 128), mat);
  mesh.rotation.x = -Math.PI / 2;
  mesh.receiveShadow = true;
  const mirrorCam = new THREE.PerspectiveCamera();
  const tmp = new THREE.Vector3();
  const bias = new THREE.Matrix4().set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);
  function update(scene, camera) {
    if (!mesh.visible || uniforms.uReflStrength.value <= 0) return;
    mirrorCam.copy(camera);
    // reflect camera about y=0
    mirrorCam.position.set(camera.position.x, -camera.position.y, camera.position.z);
    const look = camera.getWorldDirection(tmp);
    mirrorCam.up.set(0, -1, 0);
    mirrorCam.lookAt(mirrorCam.position.x + look.x, mirrorCam.position.y - look.y, mirrorCam.position.z + look.z);
    mirrorCam.updateMatrixWorld();
    mirrorCam.projectionMatrix.copy(camera.projectionMatrix);
    // oblique clip plane at y=0 so nothing below the floor leaks in
    const plane = new THREE.Plane(new THREE.Vector3(0, 1, 0), 0).applyMatrix4(mirrorCam.matrixWorldInverse);
    const clip = new THREE.Vector4(plane.normal.x, plane.normal.y, plane.normal.z, plane.constant);
    const P = mirrorCam.projectionMatrix, q = new THREE.Vector4();
    q.x = (Math.sign(clip.x) + P.elements[8]) / P.elements[0];
    q.y = (Math.sign(clip.y) + P.elements[9]) / P.elements[5];
    q.z = -1.0; q.w = (1.0 + P.elements[10]) / P.elements[14];
    clip.multiplyScalar(2.0 / clip.dot(q));
    P.elements[2] = clip.x; P.elements[6] = clip.y; P.elements[10] = clip.z + 1.0; P.elements[14] = clip.w;
    uniforms.uReflMatrix.value.copy(bias).multiply(mirrorCam.projectionMatrix).multiply(mirrorCam.matrixWorldInverse);
    mesh.visible = false;
    const hidden = [];
    scene.traverse(o => { if (o.userData.interior && o.visible) { o.visible = false; hidden.push(o); } });
    const prev = renderer.getRenderTarget();
    const sm = renderer.shadowMap.needsUpdate;
    renderer.shadowMap.needsUpdate = false;
    renderer.setRenderTarget(rt);
    renderer.clear();
    renderer.render(scene, mirrorCam);
    renderer.setRenderTarget(prev);
    renderer.shadowMap.needsUpdate = sm;
    for (const o of hidden) o.visible = true;
    mesh.visible = true;
  }
  return { mesh, update, uniforms };
}
