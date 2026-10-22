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

// indicator lens: fine vertical cylindrical ribs (tangent-space normal map, one rib per 32 px)
function ribNormal() {
  return canvasTex(256, 16, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const nx = Math.sin(((x / 32) % 1 - 0.5) * Math.PI) * 0.7;
      const i = (y * w + x) * 4;
      img.data[i] = (nx * 0.5 + 0.5) * 255; img.data[i + 1] = 128; img.data[i + 2] = 255; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, { repeat: [20, 20] });          // UVs in metres: 8 ribs per 5 cm
}

// Square wire grille seen in the front studio photograph.
function meshAlpha() {
  return canvasTex(256, 128, (g, w, h) => {
    g.fillStyle = '#000000'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#ffffff'; g.lineWidth = 3;
    for (let x = 0; x <= w; x += 32) {
      g.beginPath(); g.moveTo(x, 0); g.lineTo(x, h); g.stroke();
    }
    for (let y = 0; y <= h; y += 32) {
      g.beginPath(); g.moveTo(0, y); g.lineTo(w, y); g.stroke();
    }
  }, { repeat: [10, 20] });   // square openings at 12.5 mm pitch; UVs in metres
}

// radiator core: fine vertical fins
function finNormal() {
  return canvasTex(64, 8, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const nx = Math.sin(((x / 8) % 1 - 0.5) * Math.PI) * 0.85;
      const i = (y * w + x) * 4;
      img.data[i] = (nx * 0.5 + 0.5) * 255; img.data[i + 1] = 128; img.data[i + 2] = 255; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, { repeat: [60, 60] });
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

// Moulded rear lenses: broad vertical flutes crossed by finer horizontal ribs.
function rearLensNormal() {
  return canvasTex(256, 256, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const nx = Math.sin((x / 32 % 1 - 0.5) * Math.PI) * 0.65;
      const ny = Math.sin((y / 16 % 1 - 0.5) * Math.PI) * 0.35;
      const i = (y * w + x) * 4;
      img.data[i] = (nx * 0.5 + 0.5) * 255;
      img.data[i + 1] = (ny * 0.5 + 0.5) * 255;
      img.data[i + 2] = 240; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  }, { repeat: [20, 20] });
}

function braidNormal() {
  return canvasTex(128, 128, (g, w, h) => {
    const img = g.createImageData(w, h);
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
      const a = Math.sin((x + y) * Math.PI / 16), b = Math.sin((x - y) * Math.PI / 16);
      const i = (y * w + x) * 4;
      img.data[i] = 128 + 45 * (a + b); img.data[i + 1] = 128 + 45 * (a - b);
      img.data[i + 2] = 240; img.data[i + 3] = 255;
    }
    g.putImageData(img, 0, 0);
  });
}

// Subtle mottling on exposed cast aluminium; deterministic and seamless.
function castColor() {
  return canvasTex(256, 256, (g, w, h) => {
    const img = g.createImageData(w, h);
    const hash = (x, y, n) => {
      const v = Math.sin((x % n) * 127.1 + (y % n) * 311.7) * 43758.5453;
      return v - Math.floor(v);
    };
    const noise = (x, y, n) => {
      const ix = Math.floor(x), iy = Math.floor(y);
      let u = x - ix, v = y - iy; u = u*u*(3-2*u); v = v*v*(3-2*v);
      return (hash(ix,iy,n)*(1-u)+hash(ix+1,iy,n)*u)*(1-v) +
        (hash(ix,iy+1,n)*(1-u)+hash(ix+1,iy+1,n)*u)*v;
    };
    for (let y=0; y<h; y++) for (let x=0; x<w; x++) {
      const c=207+30*noise(x/w*4,y/h*4,4)+15*noise(x/w*16,y/h*16,16), i=(y*w+x)*4;
      img.data[i]=c; img.data[i+1]=c; img.data[i+2]=c-3; img.data[i+3]=255;
    }
    g.putImageData(img,0,0);
  }, { srgb: true });
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

// Rear plate layout and lettering from the supplied studio photographs.
function decalPlate() {
  return decalCanvas(1024, 512, (g, w, h) => {
    g.fillStyle = '#eeeede'; g.fillRect(0, 0, w, h);
    g.strokeStyle = '#184a95'; g.lineWidth = 9; g.strokeRect(12, 12, w - 24, h - 24);
    g.fillStyle = '#144c9e'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.font = `italic 600 ${h * 0.12}px ${DFONT}`; g.fillText('Michigan', w / 2, h * 0.13);
    g.save(); g.translate(w / 2, h * 0.54); g.scale(0.77, 1);
    g.font = `500 ${h * 0.58}px monospace`; g.fillText('MCFLYIN', 0, 0); g.restore();
    g.fillStyle = '#174b98'; g.fillRect(20, h - 59, w - 40, 39);
    g.fillStyle = '#eeeeee'; g.font = `500 ${h * 0.065}px ${DFONT}`; g.fillText('michigan.org', w / 2, h - 39);
    g.fillStyle = '#e3c34b'; g.fillRect(w - 145, 24, 104, 85);
    g.fillStyle = '#30302a'; g.font = `700 ${h * 0.07}px ${DFONT}`; g.fillText('FEB', w - 93, 76);
    for (const x of [w * 0.18, w * 0.82]) {
      g.fillStyle = '#393a39'; g.beginPath(); g.arc(x, h * 0.16, 8, 0, Math.PI * 2); g.fill();
    }
  });
}

const lin = (r, g, b) => new THREE.Color().setRGB(r, g, b, THREE.LinearSRGBColorSpace);

// Shared uniforms for baked AO: blend between the doors-closed and doors-open bakes.
export const AO = { open: { value: 0 }, strength: { value: 1 }, direct: { value: 0 }, pow: { value: 1 } };
// How much of the key light shows in the car's reflections (set per scene, web/js/main.js): the
// studio's key stands in for the overhead softbox, which the reflection map already holds, so there
// it only lights the set and casts the shadows; the day's sun and the night's lamps glint as well.
export const KEY = { spec: { value: 1 } };

// One onBeforeCompile per material: optional triplanar texturing (object space, for meshes
// without UVs) + baked per-vertex ambient occlusion (attributes `ao`, `ao2`).
export function enhance(mat, tri = null) {
  if (tri) mat.userData.tri = tri;
  const T = mat.userData.tri;
  mat.onBeforeCompile = sh => {
    sh.uniforms.uAOOpen = AO.open;
    sh.uniforms.uAOStr = mat.userData.aoStr || AO.strength;
    sh.uniforms.uAODirect = mat.userData.aoDirect || AO.direct;
    sh.uniforms.uAOPow = mat.userData.aoPow || AO.pow;
    sh.uniforms.uKeySpec = KEY.spec;
    let v = sh.vertexShader.replace('#include <common>', '#include <common>\nattribute float ao; attribute float ao2; varying float vAO; uniform float uAOOpen;')
      .replace('#include <begin_vertex>', '#include <begin_vertex>\nvAO = mix(ao, ao2, uAOOpen);');
    const F = mat.userData.fascia;
    if (F) {
      // second stainless finish, weighted per vertex by the `fascia` attribute (web/js/main.js)
      sh.uniforms.uFasciaTint = { value: F.tint };
      sh.uniforms.uFasciaRough = { value: F.rough };
      v = v.replace('#include <common>', '#include <common>\nattribute float fascia; varying float vFascia;')
        .replace('#include <begin_vertex>', '#include <begin_vertex>\nvFascia = fascia;');
    }
    let f = sh.fragmentShader.replace('#include <common>', '#include <common>\nvarying float vAO; uniform float uAOStr; uniform float uAODirect; uniform float uAOPow; uniform float uKeySpec;')
      .replace('#include <aomap_fragment>', `#include <aomap_fragment>
      {
        // cabin trims: the roof hides most of the studio's lights from them, which the baked AO
        // (60 cm reach) only partly captures, so it bites harder there
        float ambientOcclusion = pow(mix(1.0, clamp(vAO * 1.06, 0.0, 1.0), uAOStr), uAOPow);
        reflectedLight.indirectDiffuse *= ambientOcclusion;
        // micro-shadowing: the shadow map can't resolve a 4 mm panel gap, so the baked AO dims
        // direct light on the rolled edges that face into it (open panel areas sit at ~1)
        float aoDirect = mix(1.0, smoothstep(0.5, 0.97, vAO), uAODirect);
        reflectedLight.directSpecular *= aoDirect * uKeySpec;
        reflectedLight.directDiffuse *= aoDirect;
        #if defined( USE_CLEARCOAT )
          clearcoatSpecularIndirect *= ambientOcclusion;
          clearcoatSpecularDirect *= uKeySpec;
        #endif
        #if defined( USE_SHEEN )
          sheenSpecularIndirect *= ambientOcclusion;
        #endif
        #if defined( USE_ENVMAP ) && defined( STANDARD )
          float dotNVao = saturate( dot( geometryNormal, geometryViewDir ) );
          reflectedLight.indirectSpecular *= computeSpecularOcclusion( dotNVao, ambientOcclusion, material.roughness );
        #endif
      }`);
    if (F) {
      f = f.replace('#include <common>', '#include <common>\nvarying float vFascia; uniform vec3 uFasciaTint; uniform float uFasciaRough;')
        .replace('#include <map_fragment>', '#include <map_fragment>\ndiffuseColor.rgb *= mix(vec3(1.0), uFasciaTint, vFascia);')
        .replace('#include <roughnessmap_fragment>', '#include <roughnessmap_fragment>\nroughnessFactor = min(roughnessFactor * mix(1.0, uFasciaRough, vFascia), 1.0);');
    }
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
  const key = (mat.userData.thin ? 'thin' : '') + (mat.userData.fascia ? 'fascia' : '') + 'enh' + (T ? 't' + (T.normal ? 'n' : '') + (T.rough ? 'r' : '') + (T.color ? 'c' : '') : '');
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
  // as on the reference car (ref/studio 03, 04, 09-12): charcoal hide, near-black carpet, grey cloth
  // on the headliner and the upper door panels
  black: { leather: [0.014, 0.014, 0.015], vinyl: [0.016, 0.016, 0.017], carpet: [0.010, 0.010, 0.011], head: [0.36, 0.365, 0.36] },
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
  // brushed stainless: a CC0 scan (ambientCG Metal009, tools/tex/import_cc0.py), one tile per
  // 0.5 m; the UVs are metres with U along the car (web/js/main.js), the grain runs along U
  const steelC = tex(T + 'stainless_c.jpg', { srgb: true, repeat: 2 });
  const steelN = tex(T + 'stainless_n.jpg', { repeat: 2 });
  const steelR = tex(T + 'stainless_r.jpg', { repeat: 2 });
  const grainN = tex(T + 'plastic_grain_n.png', { repeat: 6 });
  const flute = fluteNormal();
  const prism = prismNormal();
  const lib = {};

  lib.Stainless = new THREE.MeshPhysicalMaterial({
    // brushed grain lives in the normal / roughness maps; the lobe itself is isotropic: three.js's
    // anisotropic IBL bends the lookup normal along the grain, which smears away the light-over-dark
    // flank gradient the reference photos show
    // the maps are centred on 0.5: colour and roughness here are twice the mean values
    name: 'Stainless', color: lin(1.24, 1.21, 1.17), metalness: 1, roughness: 0.50,
    map: steelC, roughnessMap: steelR, normalMap: steelN, normalScale: new THREE.Vector2(0.2, 0.2),
    side: THREE.DoubleSide, envMapIntensity: 1.0,
  });
  lib.Urethane = new THREE.MeshPhysicalMaterial({
    // satin graphite urethane (bumpers and rear valance): a cool dark grey that reads as a
    // second, darker metal against the stainless in the photos (sRGB ~55-65 face-on in front, ~40 at
    // the back), not black; it picks up soft reflections that show the bumper's shape
    name: 'Urethane', color: lin(0.052, 0.057, 0.080), metalness: 0, roughness: 0.55,
    normalMap: grainN, normalScale: new THREE.Vector2(0.2, 0.2), clearcoat: 0.35, clearcoatRoughness: 0.35,
  });
  // Smooth painted rear fascia, distinct from the brushed stainless quarters.
  lib.FasciaPaint = new THREE.MeshPhysicalMaterial({ name: 'FasciaPaint', color: lin(0.52, 0.53, 0.54),
    metalness: 0.95, roughness: 0.28, clearcoat: 0.2, clearcoatRoughness: 0.3 });
  lib.TailFrame = new THREE.MeshPhysicalMaterial({ name: 'TailFrame', color: lin(0.026, 0.028, 0.030),
    roughness: 0.38, clearcoat: 0.25, clearcoatRoughness: 0.3 });
  lib.Lamp_RearRefl = new THREE.MeshStandardMaterial({ name: 'Lamp_RearRefl', color: lin(0.65, 0.64, 0.60), metalness: 1, roughness: 0.27 });
  lib.FrameCoat = new THREE.MeshStandardMaterial({ name: 'FrameCoat', color: lin(0.085, 0.090, 0.092), metalness: 0.25, roughness: 0.62 });
  lib.BraidedMetal = triplanar(new THREE.MeshStandardMaterial({ name: 'BraidedMetal', color: lin(0.36, 0.35, 0.32), metalness: 0.8, roughness: 0.58 }),
    { normal: braidNormal(), scale: 80, normalScale: 0.65 });
  lib.AnodizedBlue = new THREE.MeshStandardMaterial({ name: 'AnodizedBlue', color: lin(0.018, 0.12, 0.20), metalness: 0.75, roughness: 0.3 });
  lib.PlateLight = new THREE.MeshPhysicalMaterial({ name: 'PlateLight', color: lin(0.72, 0.65, 0.46), roughness: 0.25,
    emissive: lin(1, 0.80, 0.48), emissiveIntensity: 0 });
  lib.Rubber = new THREE.MeshStandardMaterial({ name: 'Rubber', color: lin(0.010, 0.010, 0.011), roughness: 0.78 });
  lib.PlasticBlack = new THREE.MeshPhysicalMaterial({ name: 'PlasticBlack', color: lin(0.012, 0.012, 0.013), roughness: 0.42, clearcoat: 0.15, clearcoatRoughness: 0.4, side: THREE.DoubleSide });
  // The chin spoiler has a satin moulded finish: broad highlights reveal its rolled cheeks.
  lib.AirDam = new THREE.MeshPhysicalMaterial({ name: 'AirDam', color: lin(0.020, 0.022, 0.029), roughness: 0.30,
    clearcoat: 0.25, clearcoatRoughness: 0.30, envMapIntensity: 1.3, side: THREE.DoubleSide });
  lib.PlasticMatte = new THREE.MeshStandardMaterial({ name: 'PlasticMatte', color: lin(0.024, 0.024, 0.026), roughness: 0.8, side: THREE.DoubleSide });
  lib.Louvre = new THREE.MeshPhysicalMaterial({ name: 'Louvre', color: lin(0.045, 0.048, 0.050), roughness: 0.32,
    clearcoat: 0.25, clearcoatRoughness: 0.4, side: THREE.DoubleSide });
  lib.Glass = new THREE.MeshPhysicalMaterial({
    name: 'Glass', color: lin(0.86, 0.90, 0.88), metalness: 0, roughness: 0.0, transmission: 1, thickness: 0.0,
    ior: 1.52, specularIntensity: 1, side: THREE.DoubleSide, envMapIntensity: 1.2,
  });
  // amber-coated reflector behind the front indicator lenses (the lens itself only tints what it reflects)
  lib.Lamp_TurnRefl = new THREE.MeshStandardMaterial({ name: 'Lamp_TurnRefl', color: lin(0.80, 0.34, 0.04), metalness: 1, roughness: 0.3 });
  // sealed-beam reflectors: bright, a little hazy (the fluted glass in front scatters them), so the
  // deep bowls read silver all over instead of mirroring the dark studio walls at their centres
  lib.Lamp_HeadRefl = new THREE.MeshStandardMaterial({ name: 'Lamp_HeadRefl', color: lin(0.90, 0.90, 0.90), metalness: 1, roughness: 0.32, side: THREE.DoubleSide });
  lib.Chrome = new THREE.MeshStandardMaterial({ name: 'Chrome', color: lin(0.92, 0.92, 0.92), metalness: 1, roughness: 0.06, side: THREE.DoubleSide });
  lib.MirrorGlass = new THREE.MeshStandardMaterial({ name: 'MirrorGlass', color: lin(0.55, 0.56, 0.58), metalness: 1, roughness: 0.0 });
  lib.BadgeAlu = new THREE.MeshPhysicalMaterial({ name: 'BadgeAlu', color: lin(0.80, 0.80, 0.82), metalness: 1, roughness: 0.26, clearcoat: 0.4 });
  // sooty steel tips (they read dark under the bumper in the photos)
  lib.Exhaust = new THREE.MeshStandardMaterial({ name: 'Exhaust', color: lin(0.16, 0.15, 0.14), metalness: 1, roughness: 0.5 });
  // black-painted wire mesh: only its sheen picks it out against the dark radiator (front photo)
  lib.GrilleMesh = new THREE.MeshStandardMaterial({ name: 'GrilleMesh', color: lin(0.035, 0.040, 0.045), alphaMap: meshAlpha(), alphaTest: 0.15,
    metalness: 0.5, roughness: 0.5, side: THREE.FrontSide });
  lib.Radiator = new THREE.MeshStandardMaterial({ name: 'Radiator', color: lin(0.035, 0.035, 0.037), metalness: 0.6, roughness: 0.55,
    normalMap: finNormal(), normalScale: new THREE.Vector2(0.8, 0.8) });
  lib.RadiatorFrame = new THREE.MeshStandardMaterial({ name: 'RadiatorFrame', color: lin(0.16, 0.17, 0.18), metalness: 0.5, roughness: 0.5 });

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
  // deep amber, as the unlit lenses read on the reference car
  lib.Lamp_TurnFront = lens('Lamp_TurnFront', [0.62, 0.17, 0.004], [1.0, 0.45, 0.02], { normalMap: ribNormal(), normalScale: new THREE.Vector2(0.8, 0.8) });
  lib.Lamp_MarkerFront = lens('Lamp_MarkerFront', [0.42, 0.10, 0.005], [1.0, 0.45, 0.02]);
  lib.Lamp_TurnRear = lens('Lamp_TurnRear', [0.50, 0.13, 0.006], [1.0, 0.45, 0.02]);
  lib.Lamp_Tail = lens('Lamp_Tail', [0.22, 0.006, 0.005], [1.0, 0.02, 0.01]);
  lib.Lamp_MarkerRear = lens('Lamp_MarkerRear', [0.16, 0.006, 0.005], [1.0, 0.02, 0.01]);
  lib.Lamp_Reverse = lens('Lamp_Reverse', [0.42, 0.42, 0.42], [1.0, 0.97, 0.92], { attenuationDistance: 1 });

  const rearOptics = rearLensNormal();
  for (const k of ['Lamp_TurnRear', 'Lamp_Tail', 'Lamp_Reverse']) {
    lib[k].normalMap = rearOptics; lib[k].normalScale.set(0.35, 0.35);
    lib[k].roughness = 0.14;
  }

  // wheels (names from tools/model/wheels.py)
  lib.Tyre_Rubber = new THREE.MeshPhysicalMaterial({ name: 'Tyre_Rubber', color: lin(0.018, 0.018, 0.019), roughness: 0.86, sheen: 0.15, sheenRoughness: 0.8, sheenColor: lin(0.2, 0.2, 0.2) });
  lib.Wheel_Alloy = new THREE.MeshPhysicalMaterial({ name: 'Wheel_Alloy', color: lin(0.80, 0.80, 0.81), metalness: 1, roughness: 0.24, clearcoat: 0.6, clearcoatRoughness: 0.1 });
  lib.Wheel_SlotDark = new THREE.MeshStandardMaterial({ name: 'Wheel_SlotDark', color: lin(0.05, 0.05, 0.05), roughness: 0.6, metalness: 0.4 });
  // Peter_D's "DeLorean wheels" (Sketchfab, CC BY 4.0): glTF PBR maps, UVs in glTF orientation,
  // occlusion / roughness / metalness packed in R / G / B
  const pdTex = (part, k) => { const t = tex(T + `pd_${part}_${k}.jpg`, { srgb: k === 'base' }); t.flipY = false; return t; };
  const pdMat = (name, part, o = {}) => {
    const orm = pdTex(part, 'orm');
    return new THREE.MeshPhysicalMaterial({ name, map: pdTex(part, 'base'), normalMap: pdTex(part, 'normal'), aoMap: orm,
      roughnessMap: orm, metalnessMap: orm, roughness: 1, metalness: 1, side: THREE.DoubleSide, ...o });
  };
  lib.Tyre_PD_F = pdMat('Tyre_PD_F', 'tyre_f', { metalness: 0, sheen: 0.12, sheenRoughness: 0.8, sheenColor: lin(0.2, 0.2, 0.2) });
  lib.Tyre_PD_R = pdMat('Tyre_PD_R', 'tyre_r', { metalness: 0, sheen: 0.12, sheenRoughness: 0.8, sheenColor: lin(0.2, 0.2, 0.2) });
  // the source albedo is a dull grey; the turbine faces on the reference car read bright silver
  // (rim brightness matched to the side view: satin silver faces, dark slots)
  lib.Wheel_PD = pdMat('Wheel_PD', 'wheel', { aoMapIntensity: 0.8, roughness: 0.42, clearcoat: 0.6, clearcoatRoughness: 0.2, envMapIntensity: 1.25 });
  lib.Wheel_PD.color.setScalar(3.2);
  // the sidewall lettering reads dark-on-black on the reference car's tyres
  lib.Tyre_PD_F.color.setScalar(0.6); lib.Tyre_PD_R.color.setScalar(0.6);
  lib.Brake_Disc = new THREE.MeshStandardMaterial({ name: 'Brake_Disc', color: lin(0.42, 0.40, 0.38), metalness: 1, roughness: 0.48 });
  lib.Brake_Caliper = new THREE.MeshStandardMaterial({ name: 'Brake_Caliper', color: lin(0.03, 0.03, 0.03), roughness: 0.5 });
  lib.Lug_Chrome = lib.Chrome;

  // interior (no UVs -> triplanar)
  // CC0 scans (ambientCG Leather026, Carpet012; tools/tex/import_cc0.py)
  const leatherN = tex(T + 'leather_n.jpg'), leatherR = tex(T + 'leather_r.jpg');
  const carpetC = tex(T + 'carpet_c.jpg', { srgb: true }), carpetN = tex(T + 'carpet_n.jpg');
  lib.Leather = triplanar(new THREE.MeshPhysicalMaterial({ name: 'Leather', color: lin(0.165, 0.17, 0.178), roughness: 0.48, sheen: 0.15, sheenRoughness: 0.5, sheenColor: lin(0.2, 0.2, 0.2), clearcoat: 0.25, clearcoatRoughness: 0.38 }),
    { normal: leatherN, rough: leatherR, scale: 6.5, normalScale: 0.75 });
  lib.LeatherBlack = triplanar(new THREE.MeshPhysicalMaterial({ name: 'LeatherBlack', color: lin(0.018, 0.018, 0.019), roughness: 0.55, sheen: 0.2, sheenRoughness: 0.5, sheenColor: lin(0.2, 0.2, 0.2), clearcoat: 0.15, clearcoatRoughness: 0.4 }),
    { normal: leatherN, rough: leatherR, scale: 9, normalScale: 0.7 });
  lib.Vinyl = triplanar(new THREE.MeshPhysicalMaterial({ name: 'Vinyl', color: lin(0.15, 0.155, 0.162), roughness: 0.68, clearcoat: 0.05 }),
    { normal: leatherN, rough: leatherR, scale: 11, normalScale: 0.45 });
  lib.Headliner = triplanar(new THREE.MeshStandardMaterial({ name: 'Headliner', color: lin(0.30, 0.30, 0.29), roughness: 0.80, side: THREE.DoubleSide }),
    { normal: carpetN, scale: 14, normalScale: 0.3 });
  lib.Carpet = triplanar(new THREE.MeshPhysicalMaterial({ name: 'Carpet', color: lin(0.105, 0.108, 0.112), roughness: 1.0, sheen: 0.6, sheenRoughness: 0.9, sheenColor: lin(0.25, 0.25, 0.26) }),
    { normal: carpetN, color: carpetC, scale: 4, normalScale: 1.0 });
  // door edges and aperture jambs: the black-painted inner door frame / rubber seal faces
  lib.DoorEdge = triplanar(new THREE.MeshPhysicalMaterial({ name: 'DoorEdge', color: lin(0.022, 0.022, 0.024), roughness: 0.55, metalness: 0.0, clearcoat: 0.2, clearcoatRoughness: 0.5, side: THREE.DoubleSide }),
    { normal: grainN, scale: 9, normalScale: 0.25 });
  lib.PedalRubber = new THREE.MeshStandardMaterial({ name: 'PedalRubber', color: lin(0.02, 0.02, 0.02), roughness: 0.82 });
  lib.MetalDark = new THREE.MeshStandardMaterial({ name: 'MetalDark', color: lin(0.07, 0.07, 0.075), metalness: 1, roughness: 0.42 });
  lib.Lamp_Courtesy = new THREE.MeshPhysicalMaterial({ name: 'Lamp_Courtesy', color: lin(0.62, 0.20, 0.012), roughness: 0.2, transmission: 0.4, thickness: 0.004, emissive: lin(1, 0.36, 0.03), emissiveIntensity: 0 });
  triplanar(lib.Urethane, { normal: grainN, scale: 8, normalScale: 0.35 });
  lib.Urethane.normalMap = null;
  triplanar(lib.PlasticBlack, { normal: grainN, scale: 9, normalScale: 0.3 });
  triplanar(lib.Louvre, { normal: grainN, scale: 9, normalScale: 0.15 });
  triplanar(lib.PlasticMatte, { normal: grainN, scale: 6, normalScale: 0.4 });

  // engine bay
  const castC = castColor();
  lib.EngineAlu = triplanar(new THREE.MeshStandardMaterial({ name: 'EngineAlu', color: lin(0.36, 0.36, 0.35), metalness: 1, roughness: 0.62 }), { normal: grainN, color: castC, scale: 14, normalScale: 0.5 });
  lib.CastAlu = triplanar(new THREE.MeshStandardMaterial({ name: 'CastAlu', color: lin(0.56, 0.56, 0.55), metalness: 1, roughness: 0.48 }), { normal: grainN, color: castC, scale: 18, normalScale: 0.6 });
  lib.RustyIron = triplanar(new THREE.MeshStandardMaterial({ name: 'RustyIron', color: lin(0.16, 0.075, 0.035), metalness: 0.4, roughness: 0.9 }), { normal: grainN, scale: 10, normalScale: 1.0 });
  lib.RedPaint = new THREE.MeshPhysicalMaterial({ name: 'RedPaint', color: lin(0.42, 0.015, 0.01), roughness: 0.3, clearcoat: 0.6 });
  lib.Decal_Airbox = new THREE.MeshStandardMaterial({ name: 'Decal_Airbox', map: decalAirbox(), roughness: 0.45, metalness: 0.1 });
  lib.Decal_Jump = new THREE.MeshStandardMaterial({ name: 'Decal_Jump', map: decalJump(), roughness: 0.6 });
  lib.Decal_Plate = new THREE.MeshPhysicalMaterial({ name: 'Decal_Plate', map: decalPlate(), roughness: 0.35, clearcoat: 0.5, clearcoatRoughness: 0.3 });

  lib._fallback = new THREE.MeshStandardMaterial({ name: 'fallback', color: 0xff00ff, roughness: 0.5 });
  // thin transparent shells instead of the (expensive) transmission pass
  // tinted: the panes cut ~30 % of the light passing through and scatter very little themselves,
  // so the dark cabin reads through them as in the reference photos
  thinGlass(lib.Glass, 0.30); lib.Glass.color = lin(0.035, 0.032, 0.026); lib.Glass.side = THREE.FrontSide;
  thinGlass(lib.Lamp_HeadLens, 0.05); lib.Lamp_HeadLens.side = THREE.FrontSide;      // clear: the chrome reflectors show
  for (const k of ['Lamp_TurnFront', 'Lamp_MarkerFront', 'Lamp_TurnRear', 'Lamp_Tail', 'Lamp_MarkerRear', 'Lamp_Reverse', 'Lamp_Courtesy']) thinGlass(lib[k], 0.82);
  for (const k of ['Lamp_TurnRear', 'Lamp_Tail']) lib[k].opacity = 0.97;
  lib.Lamp_TurnFront.opacity = 0.75;     // the reflector shows through the front indicators
  // AO strength per material (open steel panels bake to ~1, so this mostly darkens gaps, arches and the strip's shadow)
  // (the lamp reflectors bake deep inside their bowls, but light reaches them through the glass)
  const aoStr = { Stainless: 0.6, Urethane: 0.6, AirDam: 0.45, Rubber: 0.7, BadgeAlu: 0.4, Chrome: 0.5, Lamp_HeadRefl: 0.1, Lamp_RearRefl: 0.1, FasciaPaint: 0.5, TailFrame: 0.5, FrameCoat: 0.7, Decal_Plate: 0.15 };
  for (const [k, v] of Object.entries(aoStr)) lib[k].userData.aoStr = { value: v };
  lib.Decal_Plate.userData.aoDirect = { value: 0 };
  lib.Stainless.userData.aoDirect = { value: 0.85 };
  // The nose retains its darker finish through the fascia vertex mask. The rear fascia
  // uses its own smooth painted material; the wings, doors and bonnet remain brushed steel.
  lib.Stainless.userData.fascia = { tint: new THREE.Color().setRGB(0.62, 0.62, 0.62, THREE.LinearSRGBColorSpace), rough: 1.12 };
  // the cabin sits under a roof: far less of the studio's light reaches it than the bake captures
  for (const k of ['Leather', 'LeatherBlack', 'Vinyl', 'Carpet', 'Headliner']) { lib[k].userData.aoPow = { value: 2.2 }; lib[k].envMapIntensity = 0.5; }
  lib.Headliner.userData.aoPow = { value: 1.1 }; lib.Headliner.envMapIntensity = 1.0;
  for (const [k, m] of Object.entries(lib)) if (m && m.isMaterial && !m.userData.tri) enhance(m);
  return lib;
}

export function materialFor(lib, name) {
  return lib[name] || lib._fallback;
}
