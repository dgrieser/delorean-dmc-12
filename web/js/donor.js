// Materials and rig settings for the separately packaged donor car.
import * as THREE from 'three';

export async function loadDonorMaterials() {
  const response = await fetch('assets/donor/config.json');
  if (!response.ok) throw new Error('Could not load imported car configuration');
  const config = await response.json();
  const loader = new THREE.TextureLoader(), textures = new Map(), materials = {};
  const texture = (file, srgb) => {
    const key = file + ':' + srgb;
    if (!textures.has(key)) textures.set(key, loader.loadAsync('assets/donor/' + file).then(t => {
      t.flipY = false; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
      t.colorSpace = srgb ? THREE.SRGBColorSpace : THREE.NoColorSpace;
      return t;
    }));
    return textures.get(key);
  };
  await Promise.all(Object.entries(config.materials).map(async ([name, spec]) => {
    const m = new THREE.MeshPhysicalMaterial({ name, color: new THREE.Color().setRGB(...spec.color),
      roughness: spec.roughness ?? .5, metalness: spec.metalness ?? 0, alphaTest: spec.alphaTest ?? 0 });
    if (spec.map) m.map = await texture(spec.map, true);
    if (spec.emissiveMap) m.emissiveMap = await texture(spec.emissiveMap, true);
    if (spec.normalMap) { m.normalMap = await texture(spec.normalMap, false); m.normalScale.set(.6, .6); }
    if (spec.kind === 'glass') Object.assign(m, { transparent: true, opacity: .22, roughness: .07, depthWrite: false, envMapIntensity: .7 });
    if (spec.kind === 'mirror') { m.metalness = 1; m.roughness = .035; }
    if (spec.kind === 'lamp') {
      m.emissive.setRGB(...spec.emissive); m.emissiveIntensity = 0;
      m.roughness = .16; m.clearcoat = .4;
    }
    if (spec.opacity !== undefined) Object.assign(m, { transparent: true, opacity: spec.opacity, depthWrite: false });
    if (spec.trim) m.side = THREE.DoubleSide;
    m.userData.donorTrim = !!spec.trim;
    materials[name] = m;
  }));
  return { config, materials, setTrim(name) {
    for (const m of Object.values(materials)) if (m.userData.donorTrim) m.color.setScalar(name === 'black' ? .28 : 1);
  } };
}
