// PBR material library for the DMC-12. Materials are looked up by the names written
// by the asset pipeline (tools/model/manifest.py) and by the wheel/interior builds.
import * as THREE from 'three';

const loader = new THREE.TextureLoader();
const cache = {};

function tex(path, { srgb = false, repeat = 1, aniso = 8 } = {}) {
  const key = path + repeat + srgb;
  if (cache[key]) return cache[key];
  const t = loader.load(path);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat, repeat);
  t.anisotropy = aniso;
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  cache[key] = t;
  return t;
}

// Procedural lens textures (canvas) -------------------------------------------------------
function canvasTex(w, h, draw, { srgb = false, repeat = [1, 1] } = {}) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c);
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  t.repeat.set(repeat[0], repeat[1]);
  t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
  t.anisotropy = 8;
  return t;
}

// sealed-beam lens: vertical cylindrical flutes + horizontal bands (tangent-space normal map)
function fluteNormal() {
  return canvasTex(512, 512, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const fx = (x / w) * 24 % 1, fy = (y / h) * 6 % 1;
      const nx = Math.sin((fx - 0.5) * Math.PI) * 0.55;
      const ny = Math.sin((fy - 0.5) * Math.PI) * 0.18;
      const i = (y * w + x) * 4;
      img.data[i] = (nx * 0.5 + 0.5) * 255; img.data[i + 1] = (ny * 0.5 + 0.5) * 255;
      img.data[i + 2] = 255; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, { repeat: [6, 6] });
}

// tail-lamp lens: small pyramid prisms
function prismNormal() {
  return canvasTex(256, 256, (g, w, h) => {
    const img = g.createImageData(w, h);
    const n = 16;
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const fx = (x / w) * n % 1 - 0.5, fy = (y / h) * n % 1 - 0.5;
      let nx = 0, ny = 0;
      if (Math.abs(fx) > Math.abs(fy)) nx = Math.sign(fx) * 0.7; else ny = Math.sign(fy) * 0.7;
      const i = (y * w + x) * 4;
      img.data[i] = (nx * 0.5 + 0.5) * 255; img.data[i + 1] = (ny * 0.5 + 0.5) * 255;
      img.data[i + 2] = 230; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, { repeat: [40, 40] });
}

function decalCanvas(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}
const DFONT = '"Barlow Semi Condensed", "Arial Narrow", Arial, sans-serif';
// DMC wordmark drawn from the same blocky letter geometry as the grille badge
function dmcMark(g, x, y, h, color) {
  const u = h / 0.26;
  const P = [
    [[-0.50, 0.13], [-0.21, 0.13], [-0.18, 0.10], [-0.18, -0.10], [-0.21, -0.13], [-0.50, -0.13], [-0.50, -0.055], [-0.265, -0.055], [-0.265, 0.055], [-0.50, 0.055]],
    [[-0.155, 0.13], [0.135, 0.13], [0.165, 0.10], [0.165, -0.13], [0.085, -0.13], [0.085, 0.06], [0.045, 0.06], [0.045, -0.13], [-0.035, -0.13], [-0.035, 0.06], [-0.075, 0.06], [-0.075, -0.13], [-0.155, -0.13]],
    [[0.50, 0.13], [0.22, 0.13], [0.19, 0.10], [0.19, -0.10], [0.22, -0.13], [0.50, -0.13], [0.50, -0.055], [0.275, -0.055], [0.275, 0.055], [0.50, 0.055]],
  ];
  g.fillStyle = color;
  for (const poly of P) { g.beginPath(); poly.forEach(([px, py], i) => (i ? g.lineTo : g.moveTo).call(g, x + px * u, y - py * u)); g.closePath(); g.fill(); }
}
function decalAirbox() {
  return decalCanvas(1024, 1280, (g, w, h) => {
    g.fillStyle = '#0b0b0b'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#c9a85a'; g.lineWidth = 10; g.strokeRect(40, 40, w - 80, h - 80);
    g.save(); g.translate(w / 2, h / 2); g.rotate(-Math.PI / 2); g.translate(-h / 2, -w / 2);
    dmcMark(g, h / 2, w * 0.42, w * 0.36, '#d8bd6e');
    g.fillStyle = '#d8bd6e'; g.font = `600 ${w * 0.07}px ${DFONT}`; g.textAlign = 'center';
    g.fillText('DE LOREAN MOTOR COMPANY', h / 2, w * 0.70);
    g.font = `500 ${w * 0.03}px ${DFONT}`; g.fillStyle = '#9c8a55';
    g.fillText('IMPORTANT: Change element at intervals specified in maintenance schedule chart', h / 2, w * 0.82);
    g.restore();
  });
}
function decalJump() {
  return decalCanvas(1024, 768, (g, w, h) => {
    g.fillStyle = '#e8d9a0'; g.fillRect(0, 0, w, h);
    g.fillStyle = '#1a1a1a'; g.font = `700 ${h * 0.12}px ${DFONT}`; g.textAlign = 'center';
    g.fillText('JUMP LEAD STARTING', w / 2, h * 0.17);
    g.lineWidth = 8; g.strokeStyle = '#1a1a1a';
    g.strokeRect(w * 0.18, h * 0.32, w * 0.30, h * 0.36);
    g.beginPath(); g.moveTo(w * 0.60, h * 0.40); g.lineTo(w * 0.82, h * 0.40); g.lineTo(w * 0.76, h * 0.34); g.moveTo(w * 0.82, h * 0.40); g.lineTo(w * 0.76, h * 0.46); g.stroke();
    g.font = `600 ${h * 0.06}px ${DFONT}`; g.fillText('NEGATIVE GROUND', w / 2, h * 0.82);
    g.font = `500 ${h * 0.045}px ${DFONT}`; g.fillText('Connect positive first. See owner\'s handbook.', w / 2, h * 0.92);
  });
}

const lin = (r, g, b) => new THREE.Color().setRGB(r, g, b, THREE.LinearSRGBColorSpace);

// Shared uniforms for baked AO: blend between the doors-closed and doors-open bakes.
export const AO = { open: { value: 0 }, strength: { value: 1 } };

// One onBeforeCompile per material: optional triplanar texturing (object space, for meshes
// without UVs) + baked per-vertex ambient occlusion (attributes `ao`, `ao2`).
export function enhance(mat, tri = null) {
  if (tri) mat.userData.tri = tri;
  const T = mat.userData.tri;
  mat.onBeforeCompile = sh => {
    sh.uniforms.uAOOpen = AO.open;
    sh.uniforms.uAOStr = mat.userData.aoStr || AO.strength;
    let v = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float ao; attribute float ao2; varying float vAO; uniform float uAOOpen;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvAO = mix(ao, ao2, uAOOpen);');
    let f = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vAO; uniform float uAOStr;')
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>
      {
        float ambientOcclusion = mix(1.0, clamp(vAO * 1.06, 0.0, 1.0), uAOStr);
        reflectedLight.indirectDiffuse *= ambientOcclusion;
        #if defined( USE_CLEARCOAT )
          clearcoatSpecularIndirect *= ambientOcclusion;
        #endif
        #if defined( USE_SHEEN )
          sheenSpecularIndirect *= ambientOcclusion;
        #endif
        #if defined( USE_ENVMAP ) && defined( STANDARD )
          float dotNVao = saturate( dot( geometryNormal, geometryViewDir ) );
          reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNVao, ambientOcclusion, material.roughness );
        #endif
      }`);
    if (T) {
      const { normal, rough, color, scale, normalScale, roughMul = 1 } = T;
      sh.uniforms.tTriN = { value: normal || null };
      sh.uniforms.tTriR = { value: rough || null };
      sh.uniforms.tTriC = { value: color || null };
      sh.uniforms.uTriScale = { value: scale };
      sh.uniforms.uTriNS = { value: normalScale };
      sh.uniforms.uTriRM = { value: roughMul };
      v = v.replace('#include <common>', '#include <common>\nvarying vec3 vTriP; varying vec3 vTriN; varying vec3 vNM0; varying vec3 vNM1; varying vec3 vNM2;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvTriP = position; vTriN = normal; vNM0 = normalMatrix[0]; vNM1 = normalMatrix[1]; vNM2 = normalMatrix[2];');
      f = f.replace('#include <common>', `#include <common>
        varying vec3 vTriP; varying vec3 vTriN; varying vec3 vNM0; varying vec3 vNM1; varying vec3 vNM2;
        uniform sampler2D tTriN; uniform sampler2D tTriR; uniform sampler2D tTriC;
        uniform float uTriScale; uniform float uTriNS; uniform float uTriRM;
        vec3 triW(vec3 n) { vec3 w = pow(abs(n), vec3(4.0)); return w / (w.x + w.y + w.z); }
        vec4 triSample(sampler2D t, vec3 p, vec3 w) {
          return texture2D(t, p.zy) * w.x + texture2D(t, p.xz) * w.y + texture2D(t, p.xy) * w.z; }`);
      if (color) f = f.replace('#include <map_fragment>', `#include <map_fragment>
        { vec3 nO = normalize(vTriN); vec3 w = triW(nO); diffuseColor.rgb *= triSample(tTriC, vTriP * uTriScale, w).rgb * 1.6; }`);
      if (rough) f = f.replace('#include <roughnessmap_fragment>', `#include <roughnessmap_fragment>
        { vec3 nO = normalize(vTriN); vec3 w = triW(nO); roughnessFactor = clamp(roughnessFactor * triSample(tTriR, vTriP * uTriScale, w).g * 2.0 * uTriRM, 0.04, 1.0); }`);
      if (normal) f = f.replace('#include <normal_fragment_maps>', `#include <normal_fragment_maps>
        {
          vec3 nO = normalize(vTriN);
          vec3 w = triW(nO);
          vec3 p = vTriP * uTriScale;
          vec3 tX = texture2D(tTriN, p.zy).xyz * 2.0 - 1.0;
          vec3 tY = texture2D(tTriN, p.xz).xyz * 2.0 - 1.0;
          vec3 tZ = texture2D(tTriN, p.xy).xyz * 2.0 - 1.0;
          tX.xy *= uTriNS; tY.xy *= uTriNS; tZ.xy *= uTriNS;
          tX = vec3(tX.xy + nO.zy, abs(tX.z) * nO.x);
          tY = vec3(tY.xy + nO.xz, abs(tY.z) * nO.y);
          tZ = vec3(tZ.xy + nO.xy, abs(tZ.z) * nO.z);
          vec3 nB = normalize(tX.zyx * w.x + tY.xzy * w.y + tZ.xyz * w.z);
          vec3 nV = normalize(mat3(vNM0, vNM1, vNM2) * nB);
          normal = gl_FrontFacing ? nV : -nV;
        }`);
    }
    // guard: a NaN pixel would be smeared over the whole frame by the bloom mip chain
    f = f.replace(/}\s*$/, '  if (any(isnan(gl_FragColor)) || any(isinf(gl_FragColor))) gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);\n}');
    if (mat.userData.thin) {
      // thin glass: keep full Fresnel reflection, let the background show through (premultiplied)
      f = f.replace('#include <opaque_fragment>', `
        #ifdef OPAQUE
        diffuseColor.a = 1.0;
        #endif
        gl_FragColor = vec4( outgoingLight - totalDiffuse * ( 1.0 - diffuseColor.a ), diffuseColor.a );`);
    }
    sh.vertexShader = v;
    sh.fragmentShader = f;
  };
  const key = (mat.userData.thin ? 'thin' : '') + 'enh' + (T ? 't' + (T.normal ? 'n' : '') + (T.rough ? 'r' : '') + (T.color ? 'c' : '') : '');
  mat.customProgramCacheKey = () => key;
  return mat;
}

export function thinGlass(mat, alpha) {
  mat.userData.thin = true;
  mat.transmission = 0;
  mat.transparent = true;
  mat.opacity = alpha;
  mat.depthWrite = false;
  mat.blending = THREE.CustomBlending;
  mat.blendSrc = THREE.OneFactor;
  mat.blendDst = THREE.OneMinusSrcAlphaFactor;
  mat.blendSrcAlpha = THREE.ZeroFactor;
  mat.blendDstAlpha = THREE.OneFactor;
  return mat;
}

export function triplanar(mat, opts) { return enhance(mat, { scale: 6, normalScale: 0.6, roughMul: 1, ...opts }); }

export const TRIM = {
  grey: { leather: [0.165, 0.170, 0.178], vinyl: [0.150, 0.155, 0.162], carpet: [0.105, 0.108, 0.112], head: [0.30, 0.30, 0.29] },
  black: { leather: [0.020, 0.020, 0.021], vinyl: [0.024, 0.024, 0.026], carpet: [0.016, 0.016, 0.018], head: [0.20, 0.20, 0.20] },
};
export function setTrim(lib, name) {
  const t = TRIM[name];
  lib.Leather.color.setRGB(...t.leather, THREE.LinearSRGBColorSpace);
  lib.Vinyl.color.setRGB(...t.vinyl, THREE.LinearSRGBColorSpace);
  lib.Carpet.color.setRGB(...t.carpet, THREE.LinearSRGBColorSpace);
  lib.Headliner.color.setRGB(...t.head, THREE.LinearSRGBColorSpace);
}

export function createLibrary(opts = {}) {
  const T = 'assets/tex/';
  const brushedN = tex(T + 'brushed_n.png', { repeat: 1.6 });
  brushedN.repeat.set(1.2, 7.0);
  const brushedR = tex(T + 'brushed_r_soft.png', { repeat: 1.6 });
  brushedR.repeat.set(0.9, 5.0);
  const grainN = tex(T + 'plastic_grain_n.png', { repeat: 6 });
  const flute = fluteNormal();
  const prism = prismNormal();
  const lib = {};

  lib.Stainless = new THREE.MeshPhysicalMaterial({
    name: 'Stainless', color: lin(0.58, 0.58, 0.59), metalness: 1, roughness: 0.50,
    roughnessMap: brushedR, normalMap: brushedN, normalScale: new THREE.Vector2(0.08, 0.08),
    anisotropy: 0.4, anisotropyRotation: Math.PI / 2, side: THREE.DoubleSide, envMapIntensity: 1.0,
  });
  lib.Urethane = new THREE.MeshPhysicalMaterial({
    name: 'Urethane', color: lin(0.030, 0.032, 0.035), metalness: 0, roughness: 0.52,
    normalMap: grainN, normalScale: new THREE.Vector2(0.25, 0.25), clearcoat: 0.08, clearcoatRoughness: 0.5,
  });
  lib.Rubber = new THREE.MeshStandardMaterial({ name: 'Rubber', color: lin(0.010, 0.010, 0.011), roughness: 0.78 });
  lib.PlasticBlack = new THREE.MeshPhysicalMaterial({ name: 'PlasticBlack', color: lin(0.012, 0.012, 0.013), roughness: 0.42, clearcoat: 0.15, clearcoatRoughness: 0.4, side: THREE.DoubleSide });
  lib.PlasticMatte = new THREE.MeshStandardMaterial({ name: 'PlasticMatte', color: lin(0.016, 0.016, 0.017), roughness: 0.9, side: THREE.DoubleSide });
  lib.Glass = new THREE.MeshPhysicalMaterial({
    name: 'Glass', color: lin(0.86, 0.90, 0.88), metalness: 0, roughness: 0.0, transmission: 1, thickness: 0.0,
    ior: 1.52, specularIntensity: 1, side: THREE.DoubleSide, envMapIntensity: 1.2,
  });
  lib.GlassDark = new THREE.MeshPhysicalMaterial({ name: 'GlassDark', color: lin(0.006, 0.006, 0.007), roughness: 0.04, clearcoat: 1, clearcoatRoughness: 0.03 });
  lib.Chrome = new THREE.MeshStandardMaterial({ name: 'Chrome', color: lin(0.92, 0.92, 0.92), metalness: 1, roughness: 0.06, side: THREE.DoubleSide });
  lib.MirrorGlass = new THREE.MeshStandardMaterial({ name: 'MirrorGlass', color: lin(0.88, 0.89, 0.9), metalness: 1, roughness: 0.0 });
  lib.BadgeAlu = new THREE.MeshPhysicalMaterial({ name: 'BadgeAlu', color: lin(0.80, 0.80, 0.82), metalness: 1, roughness: 0.26, clearcoat: 0.4 });
  lib.Exhaust = new THREE.MeshStandardMaterial({ name: 'Exhaust', color: lin(0.5, 0.48, 0.46), metalness: 1, roughness: 0.38 });

  // lamps: emissiveIntensity is driven by the lighting system
  const lens = (name, col, emis, extra = {}) => new THREE.MeshPhysicalMaterial({
    name, color: lin(...col), metalness: 0, roughness: 0.12, transmission: 0.55, thickness: 0.006, ior: 1.49,
    attenuationColor: lin(...col), attenuationDistance: 0.02, normalMap: prism, normalScale: new THREE.Vector2(0.35, 0.35),
    emissive: lin(...emis), emissiveIntensity: 0, ...extra,
  });
  lib.Lamp_HeadLens = new THREE.MeshPhysicalMaterial({
    name: 'Lamp_HeadLens', color: lin(0.95, 0.96, 0.97), roughness: 0.02, transmission: 1, thickness: 0.004, ior: 1.5,
    normalMap: flute, normalScale: new THREE.Vector2(0.6, 0.6), side: THREE.DoubleSide,
  });
  lib.Lamp_Bulb_Hi = new THREE.MeshStandardMaterial({ name: 'Lamp_Bulb_Hi', color: lin(0.8, 0.8, 0.78), roughness: 0.3, emissive: lin(1.0, 0.92, 0.80), emissiveIntensity: 0 });
  lib.Lamp_Bulb_Lo = lib.Lamp_Bulb_Hi.clone(); lib.Lamp_Bulb_Lo.name = 'Lamp_Bulb_Lo';
  lib.Lamp_TurnFront = lens('Lamp_TurnFront', [0.95, 0.42, 0.03], [1.0, 0.45, 0.02]);
  lib.Lamp_MarkerFront = lens('Lamp_MarkerFront', [0.95, 0.42, 0.03], [1.0, 0.45, 0.02]);
  lib.Lamp_TurnRear = lens('Lamp_TurnRear', [0.95, 0.42, 0.03], [1.0, 0.45, 0.02]);
  lib.Lamp_Tail = lens('Lamp_Tail', [0.60, 0.012, 0.010], [1.0, 0.02, 0.01]);
  lib.Lamp_MarkerRear = lens('Lamp_MarkerRear', [0.60, 0.012, 0.010], [1.0, 0.02, 0.01]);
  lib.Lamp_Reverse = lens('Lamp_Reverse', [0.92, 0.92, 0.92], [1.0, 0.97, 0.92], { attenuationDistance: 1 });

  // wheels (names from tools/model/wheels.py)
  lib.Tyre_Rubber = new THREE.MeshPhysicalMaterial({ name: 'Tyre_Rubber', color: lin(0.018, 0.018, 0.019), roughness: 0.86, sheen: 0.15, sheenRoughness: 0.8, sheenColor: lin(0.2, 0.2, 0.2) });
  lib.Wheel_Alloy = new THREE.MeshPhysicalMaterial({ name: 'Wheel_Alloy', color: lin(0.80, 0.80, 0.81), metalness: 1, roughness: 0.24, clearcoat: 0.6, clearcoatRoughness: 0.1 });
  lib.Wheel_SlotDark = new THREE.MeshStandardMaterial({ name: 'Wheel_SlotDark', color: lin(0.05, 0.05, 0.05), roughness: 0.6, metalness: 0.4 });
  lib.Brake_Disc = new THREE.MeshStandardMaterial({ name: 'Brake_Disc', color: lin(0.42, 0.40, 0.38), metalness: 1, roughness: 0.48 });
  lib.Brake_Caliper = new THREE.MeshStandardMaterial({ name: 'Brake_Caliper', color: lin(0.03, 0.03, 0.03), roughness: 0.5 });
  lib.Lug_Chrome = lib.Chrome;

  // interior (no UVs -> triplanar)
  const leatherN = tex(T + 'leather_n.png'), leatherR = tex(T + 'leather_r.png');
  const carpetC = tex(T + 'carpet_c.png', { srgb: true }), carpetN = tex(T + 'carpet_n.png');
  lib.Leather = triplanar(new THREE.MeshPhysicalMaterial({ name: 'Leather', color: lin(0.165, 0.17, 0.178), roughness: 0.62, sheen: 0.25, sheenRoughness: 0.6, sheenColor: lin(0.25, 0.25, 0.25), clearcoat: 0.12, clearcoatRoughness: 0.45 }),
    { normal: leatherN, rough: leatherR, scale: 6.5, normalScale: 0.75 });
  lib.LeatherBlack = triplanar(new THREE.MeshPhysicalMaterial({ name: 'LeatherBlack', color: lin(0.018, 0.018, 0.019), roughness: 0.55, sheen: 0.2, sheenRoughness: 0.5, sheenColor: lin(0.2, 0.2, 0.2), clearcoat: 0.15, clearcoatRoughness: 0.4 }),
    { normal: leatherN, rough: leatherR, scale: 9, normalScale: 0.7 });
  lib.Vinyl = triplanar(new THREE.MeshPhysicalMaterial({ name: 'Vinyl', color: lin(0.15, 0.155, 0.162), roughness: 0.68, clearcoat: 0.05 }),
    { normal: leatherN, rough: leatherR, scale: 11, normalScale: 0.45 });
  lib.Headliner = triplanar(new THREE.MeshStandardMaterial({ name: 'Headliner', color: lin(0.30, 0.30, 0.29), roughness: 0.95, side: THREE.DoubleSide }),
    { normal: carpetN, scale: 14, normalScale: 0.3 });
  lib.Carpet = triplanar(new THREE.MeshPhysicalMaterial({ name: 'Carpet', color: lin(0.105, 0.108, 0.112), roughness: 1.0, sheen: 0.6, sheenRoughness: 0.9, sheenColor: lin(0.25, 0.25, 0.26) }),
    { normal: carpetN, color: carpetC, scale: 4, normalScale: 1.0 });
  lib.PedalRubber = new THREE.MeshStandardMaterial({ name: 'PedalRubber', color: lin(0.02, 0.02, 0.02), roughness: 0.82 });
  lib.MetalDark = new THREE.MeshStandardMaterial({ name: 'MetalDark', color: lin(0.07, 0.07, 0.075), metalness: 1, roughness: 0.42 });
  lib.Lamp_Courtesy = new THREE.MeshPhysicalMaterial({ name: 'Lamp_Courtesy', color: lin(0.5, 0.03, 0.02), roughness: 0.2, transmission: 0.4, thickness: 0.004, emissive: lin(1, 0.08, 0.04), emissiveIntensity: 0 });
  triplanar(lib.Urethane, { normal: grainN, scale: 8, normalScale: 0.35 });
  lib.Urethane.normalMap = null;
  triplanar(lib.PlasticBlack, { normal: grainN, scale: 9, normalScale: 0.3 });
  triplanar(lib.PlasticMatte, { normal: grainN, scale: 6, normalScale: 0.4 });

  // engine bay
  lib.EngineAlu = triplanar(new THREE.MeshStandardMaterial({ name: 'EngineAlu', color: lin(0.36, 0.36, 0.35), metalness: 1, roughness: 0.62 }), { normal: grainN, scale: 14, normalScale: 0.5 });
  lib.CastAlu = triplanar(new THREE.MeshStandardMaterial({ name: 'CastAlu', color: lin(0.56, 0.56, 0.55), metalness: 1, roughness: 0.48 }), { normal: grainN, scale: 18, normalScale: 0.6 });
  lib.RustyIron = triplanar(new THREE.MeshStandardMaterial({ name: 'RustyIron', color: lin(0.16, 0.075, 0.035), metalness: 0.4, roughness: 0.9 }), { normal: grainN, scale: 10, normalScale: 1.0 });
  lib.RedPaint = new THREE.MeshPhysicalMaterial({ name: 'RedPaint', color: lin(0.42, 0.015, 0.01), roughness: 0.3, clearcoat: 0.6 });
  lib.Decal_Airbox = new THREE.MeshStandardMaterial({ name: 'Decal_Airbox', map: decalAirbox(), roughness: 0.45, metalness: 0.1 });
  lib.Decal_Jump = new THREE.MeshStandardMaterial({ name: 'Decal_Jump', map: decalJump(), roughness: 0.6 });

  lib._fallback = new THREE.MeshStandardMaterial({ name: 'fallback', color: 0xff00ff, roughness: 0.5 });
  // thin transparent shells instead of the (expensive) transmission pass
  thinGlass(lib.Glass, 0.16); lib.Glass.color = lin(0.30, 0.34, 0.33); lib.Glass.side = THREE.FrontSide;
  thinGlass(lib.Lamp_HeadLens, 0.10); lib.Lamp_HeadLens.side = THREE.FrontSide;
  for (const k of ['Lamp_TurnFront', 'Lamp_MarkerFront', 'Lamp_TurnRear', 'Lamp_Tail', 'Lamp_MarkerRear', 'Lamp_Reverse', 'Lamp_Courtesy']) thinGlass(lib[k], 0.82);
  // AO strength per material: the exterior steel is mostly specular -> light occlusion only
  const aoStr = { Stainless: 0.3, Urethane: 0.6, Rubber: 0.7, BadgeAlu: 0.4, Chrome: 0.5 };
  for (const [k, v] of Object.entries(aoStr)) lib[k].userData.aoStr = { value: v };
  for (const [k, m] of Object.entries(lib)) if (m && m.isMaterial && !m.userData.tri) enhance(m);
  return lib;
}

export function materialFor(lib, name) {
  return lib[name] || lib._fallback;
}
