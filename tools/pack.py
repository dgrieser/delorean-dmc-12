"""Pack a (Blender-exported) GLB into a compact quantized container for the viewer.

Output: <name>.json (scene graph + mesh table) and <name>.bin.gz (gzip'd quantized buffers).
No WASM is needed to decode (the page inflates with DecompressionStream / fflate).
"""
import gzip, json, struct, sys
import numpy as np

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}


def read_glb(path):
    data = open(path, 'rb').read()
    magic, ver, length = struct.unpack_from('<III', data, 0)
    assert magic == 0x46546C67
    off = 12
    js, binc = None, None
    while off < length:
        clen, ctype = struct.unpack_from('<II', data, off)
        chunk = data[off + 8: off + 8 + clen]
        if ctype == 0x4E4F534A:
            js = json.loads(chunk)
        elif ctype == 0x004E4942:
            binc = chunk
        off += 8 + clen
    return js, binc


def accessor(js, binc, i):
    a = js['accessors'][i]
    bv = js['bufferViews'][a['bufferView']]
    dt = CT[a['componentType']]
    n = NC[a['type']]
    start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
    stride = bv.get('byteStride', 0)
    cnt = a['count']
    if stride and stride != n * np.dtype(dt).itemsize:
        raw = np.frombuffer(binc, np.uint8, count=stride * cnt, offset=start).reshape(cnt, stride)
        arr = raw[:, :n * np.dtype(dt).itemsize].copy().view(dt).reshape(cnt, n)
    else:
        arr = np.frombuffer(binc, dt, count=cnt * n, offset=start).reshape(cnt, n)
    arr = arr.astype(np.float64) if dt == np.float32 else arr
    if a.get('normalized'):
        info = np.iinfo(dt)
        arr = np.maximum(arr / info.max, -1.0)
    return arr


def oct_encode(N):
    N = N / (np.abs(N).sum(1, keepdims=True) + 1e-12)
    x, y, z = N[:, 0], N[:, 1], N[:, 2]
    neg = z < 0
    ox = np.where(neg, (1 - np.abs(y)) * np.sign(x + 1e-30), x)
    oy = np.where(neg, (1 - np.abs(x)) * np.sign(y + 1e-30), y)
    return np.clip(np.round(np.stack([ox, oy], 1) * 32767), -32767, 32767).astype(np.int16)


def reorder(idx, n):
    """Vertex order by first use in the index buffer; returns (new_idx, perm) with attr_new = attr[perm]."""
    first = np.full(n, -1, np.int64)
    seen = np.zeros(n, bool)
    order = []
    _, first_pos = np.unique(idx, return_index=True)
    used = np.unique(idx)
    perm = used[np.argsort(first_pos)]
    remap = np.full(n, -1, np.int64)
    remap[perm] = np.arange(len(perm))
    return remap[idx].astype(np.uint32), perm


def zz(d):
    return ((d << 1) ^ (d >> 31)).astype(np.uint32)


def delta_planes(q):
    """q: (n,k) uint16 -> byte planes of zigzag deltas along n (per component)."""
    q = q.astype(np.int32)
    d = np.diff(q, axis=0, prepend=np.zeros((1, q.shape[1]), np.int32))
    d = ((d + 32768) % 65536) - 32768
    z = zz(d).astype(np.uint16)
    lo = (z & 255).astype(np.uint8)
    hi = (z >> 8).astype(np.uint8)
    return np.concatenate([lo.T.ravel(), hi.T.ravel()])


def delta_planes8(q):
    d = np.diff(q.astype(np.int32), prepend=0)
    d = ((d + 128) % 256) - 128
    return ((d << 1) ^ (d >> 31)).astype(np.uint8)


def varint_indices(idx):
    idx = idx.astype(np.int64)
    hwm = np.maximum.accumulate(np.concatenate([[-1], idx[:-1]])) + 1
    z = (hwm - idx).astype(np.uint64)          # 0 == new vertex, small == recent
    out = []
    # vectorised LEB128
    parts = []
    rem = z.copy()
    nbytes = np.ones(len(z), np.int64)
    t = rem >> 7
    while t.any():
        nbytes += (t > 0)
        t >>= 7
    total = int(nbytes.sum())
    buf = np.zeros(total, np.uint8)
    pos = np.concatenate([[0], np.cumsum(nbytes)[:-1]])
    r = z.copy()
    k = 0
    active = np.ones(len(z), bool)
    while active.any():
        a = np.nonzero(active)[0]
        b = (r[a] & 127).astype(np.uint8)
        more = (r[a] >> 7) > 0
        buf[pos[a] + k] = b | (more.astype(np.uint8) << 7)
        r[a] >>= 7
        active[a[~more]] = False
        k += 1
    return buf


class Packer:
    def __init__(self):
        self.parts = []
        self.size = 0

    def add(self, arr):
        b = np.ascontiguousarray(arr).tobytes()
        pad = (-len(b)) % 4
        off = self.size
        self.parts.append(b + b'\0' * pad)
        self.size += len(b) + pad
        return off


def pack(glb_path, out_base):
    js, binc = read_glb(glb_path)
    P = Packer()
    mats = [m.get('name', f'mat{i}') for i, m in enumerate(js.get('materials', []))]
    meshes_out = []
    mesh_map = {}
    for mi, m in enumerate(js.get('meshes', [])):
        prims = []
        for pi, pr in enumerate(m['primitives']):
            at = pr['attributes']
            pos = accessor(js, binc, at['POSITION'])
            if 'indices' in pr:
                idx0 = accessor(js, binc, pr['indices'])[:, 0].astype(np.uint32)
            else:
                idx0 = np.arange(len(pos), dtype=np.uint32)
            # spatially coherent triangle order (Morton code of centroids) -> small deltas
            tri = idx0.reshape(-1, 3)
            c = pos[tri].mean(1)
            cl, ch = c.min(0), c.max(0)
            qc = ((c - cl) / np.maximum(ch - cl, 1e-9) * 1023).astype(np.uint64)

            def spread(v):
                v = v & 0x3FF
                v = (v | (v << 16)) & 0x30000FF
                v = (v | (v << 8)) & 0x300F00F
                v = (v | (v << 4)) & 0x30C30C3
                v = (v | (v << 2)) & 0x9249249
                return v
            mort = spread(qc[:, 0]) | (spread(qc[:, 1]) << 1) | (spread(qc[:, 2]) << 2)
            tri = tri[np.argsort(mort, kind='stable')]
            idx0 = tri.ravel()
            idx0, perm = reorder(idx0, len(pos))
            cache = {}

            def A(key):
                if key not in cache:
                    cache[key] = accessor(js, binc, at[key])[perm]
                return cache[key]
            pos = pos[perm]
            ent = {'name': m.get('name', f'mesh{mi}') + (f'_{pi}' if len(m['primitives']) > 1 else ''),
                   'material': mats[pr['material']] if 'material' in pr else None, 'count': int(len(pos)), 'attrs': {}}
            lo, hi = pos.min(0), pos.max(0)
            ext = np.maximum(hi - lo, 1e-9)
            q = np.round((pos - lo) / ext * 65535).astype(np.uint16)
            ent['attrs']['position'] = {'offset': P.add(delta_planes(q)), 'type': 'd16x3', 'min': lo.tolist(), 'max': hi.tolist()}
            if 'NORMAL' in at:
                o = (np.round(oct_encode(A('NORMAL')).astype(np.float64) / 32767 * 2047)).astype(np.int32) + 2048
                ent['attrs']['normal'] = {'offset': P.add(delta_planes(o.astype(np.uint16))), 'type': 'doct12'}
            boxcode = None
            if 'TEXCOORD_0' in at:
                uv = A('TEXCOORD_0')
                gx, gy, gz = pos[:, 0], pos[:, 1], pos[:, 2]
                cands = [(-gz, 1 - gy), (gz, 1 - gy), (gx, 1 - gy), (gx, 1 + gz)]
                code = np.full(len(pos), 255, np.uint8)
                for ci, (cu, cv) in enumerate(cands):
                    ok = (np.abs(uv[:, 0] - cu) < 2e-4) & (np.abs(uv[:, 1] - cv) < 2e-4) & (code == 255)
                    code[ok] = ci
                if (code != 255).all():
                    boxcode = code
            if boxcode is not None:
                ent['attrs']['uvbox'] = {'offset': P.add(boxcode), 'type': 'u8'}
            elif 'TEXCOORD_0' in at:
                ulo, uhi = uv.min(0), uv.max(0)
                uext = np.maximum(uhi - ulo, 1e-9)
                ent['attrs']['uv'] = {'offset': P.add(delta_planes(np.round((uv - ulo) / uext * 65535).astype(np.uint16))),
                                      'type': 'd16x2', 'min': ulo.tolist(), 'max': uhi.tolist()}
            for k in at:
                if k.startswith('_'):
                    v = A(k)[:, 0]
                    ent['attrs'][k[1:].lower()] = {'offset': P.add(delta_planes8(np.round(np.clip(v, 0, 1) * 255).astype(np.uint8))), 'type': 'du8'}
                if k == 'COLOR_0':
                    c = A(k)[:, :3]
                    ent['attrs']['color'] = {'offset': P.add(np.round(np.clip(c, 0, 1) * 255).astype(np.uint8)), 'type': 'u8x3'}
            vb = varint_indices(idx0)
            ent['index'] = {'offset': P.add(vb), 'bytes': int(len(vb)), 'count': int(len(idx0)), 'type': 'varint'}
            prims.append(len(meshes_out))
            meshes_out.append(ent)
        mesh_map[mi] = prims
    nodes_out = []
    for ni, n in enumerate(js['nodes']):
        nodes_out.append({'name': n.get('name', f'node{ni}'), 'parent': -1,
                          't': n.get('translation', [0, 0, 0]), 'r': n.get('rotation', [0, 0, 0, 1]),
                          's': n.get('scale', [1, 1, 1]), 'meshes': mesh_map.get(n.get('mesh'), []) if 'mesh' in n else []})
    for ni, n in enumerate(js['nodes']):
        for c in n.get('children', []):
            nodes_out[c]['parent'] = ni
    header = {'version': 1, 'nodes': nodes_out, 'meshes': meshes_out, 'materials': mats, 'byteLength': P.size}
    blob = b''.join(P.parts)
    open(out_base + '.bin', 'wb').write(gzip.compress(blob, 9))
    json.dump(header, open(out_base + '.json', 'w'), separators=(',', ':'))
    tv = sum(m['count'] for m in meshes_out)
    ti = sum(m['index']['count'] for m in meshes_out) // 3
    import os
    print(f'packed {glb_path}: {len(meshes_out)} meshes, {tv} verts, {ti} tris, raw {P.size/1e6:.1f} MB, '
          f'gz {os.path.getsize(out_base + ".bin")/1e6:.1f} MB')


if __name__ == '__main__':
    pack(sys.argv[1], sys.argv[2])
