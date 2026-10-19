// Decoder for the compact quantized scene container written by tools/pack.py.
import * as THREE from 'three';

async function inflate(buf) {
  const u8 = new Uint8Array(buf);
  // a host may already have removed the gzip layer (Content-Encoding); only inflate real gzip data
  if (!(u8[0] === 0x1f && u8[1] === 0x8b)) return u8;
  if (typeof DecompressionStream !== 'undefined') {
    const ds = new DecompressionStream('gzip');
    const stream = new Blob([buf]).stream().pipeThrough(ds);
    return new Uint8Array(await new Response(stream).arrayBuffer());
  }
  const { gunzipSync } = await import('https://cdn.jsdelivr.net/npm/fflate@0.8.2/esm/browser.js');
  return gunzipSync(new Uint8Array(buf));
}

async function fetchProgress(url, onProgress) {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Could not load ${url} (${res.status})`);
  const total = +res.headers.get('content-length') || 0;
  if (!res.body || !total) {
    const b = await res.arrayBuffer();
    onProgress?.(1);
    return b;
  }
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.length;
    onProgress?.(Math.min(1, got / total));
  }
  const out = new Uint8Array(got);
  let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.length; }
  return out.buffer;
}

// undo delta + zigzag + byte planes -> Uint16 values (n * k)
function undelta(bytes, off, n, k) {
  const lo = bytes.subarray(off, off + n * k);
  const hi = bytes.subarray(off + n * k, off + 2 * n * k);
  const out = new Uint16Array(n * k);
  for (let c = 0; c < k; c++) {
    let acc = 0;
    const base = c * n;
    for (let i = 0; i < n; i++) {
      const z = lo[base + i] | (hi[base + i] << 8);
      const d = (z >>> 1) ^ -(z & 1);
      acc = (acc + d) & 0xffff;
      out[i * k + c] = acc;
    }
  }
  return out;
}

function decodeIndices(bytes, off, nbytes, count, nverts) {
  const out = nverts < 65536 ? new Uint16Array(count) : new Uint32Array(count);
  let p = off, hwm = 0;
  for (let i = 0; i < count; i++) {
    let v = 0, shift = 0, b;
    do { b = bytes[p++]; v += (b & 127) * Math.pow(2, shift); shift += 7; } while (b & 128);
    const idx = hwm - v;
    out[i] = idx;
    if (idx === hwm) hwm++;
  }
  return out;
}

function octDecode(q, n, bits) {
  const out = new Float32Array(n * 3);
  const half = (1 << (bits - 1)), scale = half - 1;
  for (let i = 0; i < n; i++) {
    let x = (q[i * 2] - half) / scale, y = (q[i * 2 + 1] - half) / scale;
    let z = 1 - Math.abs(x) - Math.abs(y);
    if (z < 0) { const ox = x; x = (1 - Math.abs(y)) * Math.sign(ox || 1); y = (1 - Math.abs(ox)) * Math.sign(y || 1); }
    const l = Math.hypot(x, y, z) || 1;
    out[i * 3] = x / l; out[i * 3 + 1] = y / l; out[i * 3 + 2] = z / l;
  }
  return out;
}

export function buildGeometry(m, bytes) {
  const n = m.count;
  const g = new THREE.BufferGeometry();
  const P = m.attrs.position;
  const qp = undelta(bytes, P.offset, n, 3);
  const pos = new Float32Array(n * 3);
  for (let c = 0; c < 3; c++) {
    const lo = P.min[c], ext = (P.max[c] - P.min[c]) / 65535;
    for (let i = 0; i < n; i++) pos[i * 3 + c] = lo + qp[i * 3 + c] * ext;
  }
  g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  if (m.attrs.normal) {
    const A = m.attrs.normal;
    const q = undelta(bytes, A.offset, n, 2);
    g.setAttribute('normal', new THREE.BufferAttribute(octDecode(q, n, A.type === 'doct12' ? 12 : 16), 3));
  }
  if (m.attrs.uvbox) {
    const code = bytes.subarray(m.attrs.uvbox.offset, m.attrs.uvbox.offset + n);
    const uv = new Float32Array(n * 2);
    for (let i = 0; i < n; i++) {
      const x = pos[i * 3], y = pos[i * 3 + 1], z = pos[i * 3 + 2];
      switch (code[i]) {
        case 0: uv[i * 2] = -z; uv[i * 2 + 1] = 1 - y; break;
        case 1: uv[i * 2] = z; uv[i * 2 + 1] = 1 - y; break;
        case 2: uv[i * 2] = x; uv[i * 2 + 1] = 1 - y; break;
        default: uv[i * 2] = x; uv[i * 2 + 1] = 1 + z;
      }
    }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  } else if (m.attrs.uv) {
    const A = m.attrs.uv;
    const q = undelta(bytes, A.offset, n, 2);
    const uv = new Float32Array(n * 2);
    for (let c = 0; c < 2; c++) {
      const lo = A.min[c], ext = (A.max[c] - A.min[c]) / 65535;
      for (let i = 0; i < n; i++) uv[i * 2 + c] = lo + q[i * 2 + c] * ext;
    }
    g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
  }
  for (const [k, A] of Object.entries(m.attrs)) {
    if (A.type === 'du8') {
      const src = bytes.subarray(A.offset, A.offset + n);
      const out = new Uint8Array(n);
      let acc = 0;
      for (let i = 0; i < n; i++) { const z = src[i]; acc = (acc + ((z >>> 1) ^ -(z & 1))) & 255; out[i] = acc; }
      g.setAttribute(k, new THREE.BufferAttribute(out, 1, true));
    } else if (A.type === 'u8' && k !== 'uvbox') {
      const src = bytes.subarray(A.offset, A.offset + n);
      g.setAttribute(k, new THREE.BufferAttribute(new Uint8Array(src), 1, true));
    }
  }
  const I = m.index;
  g.setIndex(new THREE.BufferAttribute(decodeIndices(bytes, I.offset, I.bytes, I.count, n), 1));
  g.computeBoundingSphere();
  g.computeBoundingBox();
  return g;
}

// Load container; returns root Object3D with named nodes. makeMaterial(name) supplies materials.
export async function loadPacked(base, makeMaterial, onProgress) {
  const [header, raw] = await Promise.all([
    fetch(base + '.json').then(r => { if (!r.ok) throw new Error('Could not load ' + base + '.json'); return r.json(); }),
    fetchProgress(base + '.bin', onProgress),
  ]);
  const bytes = await inflate(raw);
  const objs = header.nodes.map(n => {
    const o = new THREE.Group();
    o.name = n.name;
    o.position.fromArray(n.t);
    o.quaternion.fromArray(n.r);
    o.scale.fromArray(n.s);
    for (const mi of n.meshes) {
      const m = header.meshes[mi];
      const mesh = new THREE.Mesh(buildGeometry(m, bytes), makeMaterial(m.material, m.name));
      mesh.name = m.name;
      mesh.userData.material = m.material;
      o.add(mesh);
    }
    return o;
  });
  const root = new THREE.Group();
  header.nodes.forEach((n, i) => (n.parent >= 0 ? objs[n.parent] : root).add(objs[i]));
  return root;
}
