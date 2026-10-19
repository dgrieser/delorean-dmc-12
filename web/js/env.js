// Environment presets: studio / day / night. HDR lighting, grounded backdrop, sun,
// contact shadows, light-receiving ground (for the car's own lamps) and a glossy studio floor.
import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { HorizontalBlurShader } from 'three/addons/shaders/HorizontalBlurShader.js';
import { VerticalBlurShader } from 'three/addons/shaders/VerticalBlurShader.js';

export const PRESETS = {
  studio: { hdr: 'studio.hdr', exposure: 0.9, envIntensity: 1.0, sun: { dir: [0.15, 1, 0.25], color: 0xfff6ee, intensity: 1.2, radius: 6 },
            ground: { kind: 'studio', color: [0.012, 0.013, 0.015], rough: 0.3, refl: 0.55, env: 0.22 }, bg: { intensity: 0.3, blur: 0.45 }, bloom: 0.18, fog: null },
  day: { hdr: 'day.hdr', exposure: 0.78, envIntensity: 1.0, sun: { dir: [0.6275, 0.5736, 0.5265], color: 0xfff0dc, intensity: 3.6, radius: 2 },
         ground: { kind: 'asphalt', color: [0.78, 0.75, 0.72], rough: 0.92, refl: 0.0, env: 0.8 }, bg: { intensity: 1, blur: 0 }, bloom: 0.10, fog: [60, 420] },
  night: { hdr: 'night.hdr', exposure: 1.05, envIntensity: 1.3, sun: { dir: [-0.3, 0.8, -0.5], color: 0x9fb4ff, intensity: 0.06, radius: 4 },
           ground: { kind: 'asphalt', color: [0.32, 0.32, 0.33], rough: 0.38, refl: 0.42, env: 1.0 }, bg: { intensity: 1, blur: 0 }, bloom: 0.55, fog: [40, 380] },
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
  constructor(renderer, scene, opts = {}) {
    this.lite = !!opts.lite;
    this.renderer = renderer;
    this.scene = scene;
    this.pmrem = new THREE.PMREMGenerator(renderer);
    this.cache = {};
    this.group = new THREE.Group();
    scene.add(this.group);

    // sun
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

    // one ground for every scene: lit by the sun and the car's lamps, planar reflection when wet/polished
    this.asphalt = asphaltTextures();
    this.floor = makeGlossFloor(renderer);
    this.group.add(this.floor.mesh);
    this.bay = bayLines();
    this.group.add(this.bay);
    // compatibility handles used by main.js
    this.shadowPlane = this.floor.mesh;
    this.lampGround = this.floor.mesh;

    this.contact = new ContactShadow(renderer, 6.0, 3.2, 1024);
    this.group.add(this.contact.mesh);
    this.skybox = null;
    this.current = null;
  }

  async load(name) {
    if (this.cache[name]) return this.cache[name];
    const hdr = await new RGBELoader().loadAsync('assets/env/' + PRESETS[name].hdr);
    hdr.mapping = THREE.EquirectangularReflectionMapping;
    const env = this.pmrem.fromEquirectangular(hdr).texture;
    this.cache[name] = { hdr, env };
    return this.cache[name];
  }

  async set(name, extras = {}) {
    const P = PRESETS[name];
    const { hdr, env } = await this.load(name);
    const scene = this.scene;
    scene.environment = env;
    scene.environmentIntensity = P.envIntensity;
    this.renderer.toneMappingExposure = P.exposure * (extras.exposureScale || 1);
    scene.background = hdr;
    scene.backgroundBlurriness = P.bg.blur;
    scene.backgroundIntensity = P.bg.intensity;
    // ground material
    const G = P.ground, fm = this.floor.mesh.material;
    fm.color.setRGB(...G.color, THREE.LinearSRGBColorSpace);
    fm.roughness = G.rough;
    fm.envMapIntensity = G.env;
    const asph = G.kind === 'asphalt';
    fm.map = asph ? this.asphalt.map : null;
    fm.roughnessMap = asph ? this.asphalt.rough : null;
    fm.needsUpdate = true;
    this.floor.uniforms.uReflStrength.value = this.lite ? 0 : G.refl;
    this.floor.uniforms.uWorldUV.value = asph ? 1 / ASPH_TILE : 0;
    this.bay.visible = asph;
    // fog blends the ground into the horizon colour of the panorama
    if (P.fog) {
      const hc = horizonColor(hdr);
      scene.fog = new THREE.Fog(new THREE.Color().setRGB(hc[0], hc[1], hc[2], THREE.LinearSRGBColorSpace), P.fog[0], P.fog[1]);
    } else scene.fog = null;
    const d = new THREE.Vector3(...P.sun.dir).normalize();
    this.sun.position.copy(d).multiplyScalar(15);
    this.sun.color.set(P.sun.color);
    this.sun.intensity = P.sun.intensity;
    this.sun.shadow.radius = P.sun.radius;
    this.current = name;
    this.preset = P;
    return P;
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
// Glossy floor: dark polished concrete + blurred planar reflection of the scene
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
