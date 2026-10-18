// Environment presets: studio / day / night. HDR lighting, grounded backdrop, sun,
// contact shadows, light-receiving ground (for the car's own lamps) and a glossy studio floor.
import * as THREE from 'three';
import { RGBELoader } from 'three/addons/loaders/RGBELoader.js';
import { GroundedSkybox } from 'three/addons/objects/GroundedSkybox.js';
import { HorizontalBlurShader } from 'three/addons/shaders/HorizontalBlurShader.js';
import { VerticalBlurShader } from 'three/addons/shaders/VerticalBlurShader.js';

export const PRESETS = {
  studio: { hdr: 'studio.hdr', exposure: 1.0, envIntensity: 1.0, sun: { dir: [0.15, 1, 0.25], color: 0xfff6ee, intensity: 1.2, radius: 6 },
            skybox: false, floor: 'gloss', bloom: 0.18, fog: null, lampGround: 0.25 },
  day: { hdr: 'day.hdr', exposure: 0.78, envIntensity: 1.0, sun: { dir: [0.6275, 0.5736, 0.5265], color: 0xfff0dc, intensity: 3.6, radius: 2 },
         skybox: true, floor: 'shadow', bloom: 0.10, fog: null, lampGround: 0.25 },
  night: { hdr: 'night.hdr', exposure: 1.05, envIntensity: 1.3, sun: { dir: [-0.3, 0.8, -0.5], color: 0x9fb4ff, intensity: 0.06, radius: 4 },
           skybox: true, floor: 'shadow', bloom: 0.55, fog: null, lampGround: 1.0 },
};

export class Environment {
  constructor(renderer, scene) {
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
    s.mapSize.set(4096, 4096);
    s.camera.left = -3.6; s.camera.right = 3.6; s.camera.top = 3.6; s.camera.bottom = -3.6;
    s.camera.near = 0.5; s.camera.far = 40;
    s.bias = -0.00015; s.normalBias = 0.015; s.radius = 3;
    this.sunTarget = new THREE.Object3D();
    this.sun.target = this.sunTarget;
    scene.add(this.sun, this.sunTarget);

    // shadow catcher
    this.shadowPlane = new THREE.Mesh(new THREE.PlaneGeometry(40, 40), new THREE.ShadowMaterial({ opacity: 0.55, color: 0x05070a }));
    this.shadowPlane.rotation.x = -Math.PI / 2;
    this.shadowPlane.position.y = 0.001;
    this.shadowPlane.receiveShadow = true;
    this.group.add(this.shadowPlane);

    // ground that receives the car's lamps (additive over the backdrop)
    this.lampGround = new THREE.Mesh(new THREE.CircleGeometry(45, 96), new THREE.MeshStandardMaterial({
      color: new THREE.Color().setRGB(0.11, 0.11, 0.115, THREE.LinearSRGBColorSpace), roughness: 0.42, metalness: 0,
      envMapIntensity: 0, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false,
    }));
    this.lampGround.rotation.x = -Math.PI / 2;
    this.lampGround.position.y = 0.0015;
    this.lampGround.renderOrder = 1;
    this.group.add(this.lampGround);

    // glossy studio floor with planar reflection
    this.floor = makeGlossFloor(renderer);
    this.group.add(this.floor.mesh);

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
    if (this.skybox) { this.group.remove(this.skybox); this.skybox.geometry.dispose(); this.skybox.material.dispose(); this.skybox = null; }
    if (P.skybox) {
      this.skybox = new GroundedSkybox(hdr, 1.0, 55, 128);
      this.skybox.position.y = 1.0 - 0.002;
      this.group.add(this.skybox);
      scene.background = null;
    } else {
      scene.background = hdr;
      scene.backgroundBlurriness = 0.45;
      scene.backgroundIntensity = 0.3;
    }
    const d = new THREE.Vector3(...P.sun.dir).normalize();
    this.sun.position.copy(d).multiplyScalar(15);
    this.sun.color.set(P.sun.color);
    this.sun.intensity = P.sun.intensity;
    this.sun.shadow.radius = P.sun.radius;
    this.floor.mesh.visible = P.floor === 'gloss';
    this.shadowPlane.visible = P.floor !== 'gloss';
    this.shadowPlane.material.opacity = name === 'night' ? 0.2 : 0.55;
    this.lampGround.material.opacity = P.lampGround;
    this.lampGround.visible = true;
    this.current = name;
    this.preset = P;
    return P;
  }
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
    this.cam.position.set(target.position.x, 0.0, target.position.z);
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
    this.mesh.position.x = target.position.x;
    this.mesh.position.z = target.position.z;
  }
}

// ----------------------------------------------------------------------------------------------
// Glossy floor: dark polished concrete + blurred planar reflection of the scene
function makeGlossFloor(renderer) {
  const size = 60;
  const rtSize = new THREE.Vector2(768, 768);
  const rt = new THREE.WebGLRenderTarget(rtSize.x, rtSize.y, { type: THREE.HalfFloatType, generateMipmaps: true, minFilter: THREE.LinearMipmapLinearFilter });
  const mat = new THREE.MeshPhysicalMaterial({ color: new THREE.Color().setRGB(0.012, 0.013, 0.015, THREE.LinearSRGBColorSpace), roughness: 0.3, metalness: 0, envMapIntensity: 0.22 });
  const uniforms = { tReflect: { value: rt.texture }, uReflMatrix: { value: new THREE.Matrix4() }, uReflStrength: { value: 0.55 } };
  mat.onBeforeCompile = sh => {
    Object.assign(sh.uniforms, uniforms);
    sh.vertexShader = sh.vertexShader.replace('#include <common>', '#include <common>\nuniform mat4 uReflMatrix; varying vec4 vReflUv;')
      .replace('#include <project_vertex>', '#include <project_vertex>\nvReflUv = uReflMatrix * modelMatrix * vec4( transformed, 1.0 );');
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
        outgoingLight += refl * uReflStrength * mix(0.12, 1.0, fres);
        #include <opaque_fragment>`);
  };
  const mesh = new THREE.Mesh(new THREE.CircleGeometry(size / 2, 128), mat);
  mesh.rotation.x = -Math.PI / 2;
  mesh.receiveShadow = true;
  const mirrorCam = new THREE.PerspectiveCamera();
  const tmp = new THREE.Vector3();
  const bias = new THREE.Matrix4().set(0.5, 0, 0, 0.5, 0, 0.5, 0, 0.5, 0, 0, 0.5, 0.5, 0, 0, 0, 1);
  function update(scene, camera) {
    if (!mesh.visible) return;
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
