// Materials and rig settings for the separately packaged donor car.
import * as THREE from 'three';
import { enhance, thinGlass } from './materials.js';

export async function loadDonorMaterials() {
  const response = await fetch('assets/donor/config.json');
  if (!response.ok) throw new Error('Could not load imported car configuration');
  const config = await response.json();
  const loader = new THREE.TextureLoader(), textures = new Map(), materials = {};
  const texture = (file, srgb, repeat = 1) => {
    const key = file + ':' + srgb + ':' + repeat;
    if (!textures.has(key)) textures.set(key, loader.loadAsync('assets/donor/' + file).then(t => {
      t.flipY = false; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
      t.repeat.setScalar(repeat);
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      return t;
    }));
    return textures.get(key);
  };
  await Promise.all(Object.entries(config.materials).map(async ([name, spec]) => {
    const m = new THREE.MeshPhysicalMaterial({ name, color: new THREE.Color().setRGB(...spec.color),
      roughness: spec.roughness ?? .5, metalness: spec.metalness ?? 0, alphaTest: spec.alphaTest ?? 0 });
    if (spec.map && !name.includes('phong4SG')) m.map = await texture(spec.map, true);
    if (spec.emissiveMap) m.emissiveMap = await texture(spec.emissiveMap, true);
    if (spec.normalMap) { m.normalMap = await texture(spec.normalMap, false); m.normalScale.set(.6, .6); }
    if (name.includes('phong4SG')) {
      // CC0 Metal009 scan, with high-pass colour: fine grain, no baked highlights.
      m.map = await texture('../tex/stainless_c.jpg', true, 6);
      m.normalMap = await texture('../tex/stainless_n.jpg', false, 6);
      m.roughnessMap = await texture('../tex/stainless_r.jpg', false, 6);
      m.color.setRGB(.92, .94, .96); m.metalness = 1; m.roughness = .74;
      m.normalScale.set(.08, .08); m.anisotropy = .28;
      m.userData.brushedSteel = true;
    }
    if (spec.detail === 'leather') {
      m.normalMap = await texture('../tex/leather_n.jpg', false, 7);
      m.roughnessMap = await texture('../tex/leather_r.jpg', false, 7);
      m.normalScale.set(.24, .24); m.roughness = .98;
      m.clearcoat = .12; m.clearcoatRoughness = .52;
    }
    if (spec.detail === 'carpet') {
      m.map = await texture('../tex/carpet_c.jpg', true, 4);
      m.normalMap = await texture('../tex/carpet_n.jpg', false, 4);
      m.normalScale.set(.50, .50); m.sheen = .25;
      m.sheenColor.setRGB(.12, .12, .13); m.sheenRoughness = 1;
    }
    if (spec.detail === 'rubber') {
      m.normalMap = await texture('../tex/leather_n.jpg', false, 13);
      m.normalScale.set(.10, .10);
    }
    if (spec.detail === 'cloth' || spec.detail === 'webbing') {
      m.normalMap = await texture('../tex/carpet_n.jpg', false, spec.detail === 'cloth' ? 18 : 30);
      m.normalScale.set(.16, .16);
    }
    if (spec.detail === 'seat_mark') {
      const canvas = document.createElement('canvas'); canvas.width = 1024; canvas.height = 192;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#e3e3dd'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.font = '600 148px Arial, sans-serif'; ctx.fillText('RECARO', 512, 99, 985);
      // Fine diagonal thread bands stay inside the embroidered letter mask.
      ctx.globalCompositeOperation = 'source-atop';
      ctx.strokeStyle = 'rgba(80,82,78,.28)'; ctx.lineWidth = 1;
      for (let x = -192; x < 1024; x += 4) {
        ctx.beginPath(); ctx.moveTo(x,192); ctx.lineTo(x+144,0); ctx.stroke();
      }
      m.map = new THREE.CanvasTexture(canvas); m.map.colorSpace = THREE.SRGBColorSpace;
      m.bumpMap = m.map; m.bumpScale = .00010;
      m.map.flipY = false; m.map.anisotropy = 8; m.alphaTest = .5;
    }
    if (spec.kind === 'glass') {
      Object.assign(m, { roughness: .07, envMapIntensity: .7 });
      thinGlass(m, .22); enhance(m);
    }
    if (spec.kind === 'mirror') { m.metalness = 1; m.roughness = .035; }
    if (spec.kind === 'lamp') {
      m.emissive.setRGB(...spec.emissive); m.emissiveIntensity = 0;
      m.roughness = .16; m.clearcoat = .4;
    }
    if (spec.opacity !== undefined) Object.assign(m, { transparent: true, opacity: spec.opacity, depthWrite: false });
    if (spec.trim) m.side = THREE.DoubleSide;
    m.userData.donorTrim = !!spec.trim;
    m.userData.cabinTrim = spec.cabinTrim;
    // Thin overlapping trim is a poor receiver for strong vertex AO. Keep the
    // bake as soft contact shading, not a multiplier on the direct studio light.
    m.userData.aoStr = { value: name === 'Donor_DoorSteel' ? 0 : .62 };
    m.userData.aoDirect = { value: 0 };
    // The same two-pose occlusion and studio-light accounting as the original car.
    if (!['glass', 'mirror', 'lamp'].includes(spec.kind)) enhance(m);
    materials[name] = m;
  }));
  return { config, materials, setTrim(name) {
    for (const m of Object.values(materials)) {
      if (m.userData.donorTrim) m.color.setScalar(name === 'black' ? .28 : 1);
      const kind = m.userData.cabinTrim;
      if (kind) {
        const colors = name === 'black'
          ? { leather: [.022,.023,.025], carpet: [.045,.047,.050], piping: [.012,.013,.014] }
          : { leather: [.18,.185,.19], carpet: [.14,.145,.15], piping: [.09,.095,.10] };
        m.color.setRGB(...colors[kind]);
      }
    }
  } };
}
