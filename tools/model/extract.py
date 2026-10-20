"""Sparse block marching cubes for numpy SDFs, plus decimation and SDF normals."""
import numpy as np
from skimage.measure import marching_cubes


def extract(f, bmin, bmax, h, block=24, margin=1.6, batch=48, verbose=True):
    """Extract the zero iso-surface of f(x,y,z) inside [bmin,bmax] at voxel size h.

    Returns (verts Nx3 float64, faces Mx3 int64)."""
    bmin = np.asarray(bmin, np.float64)
    bmax = np.asarray(bmax, np.float64)
    n = np.ceil((bmax - bmin) / h).astype(int) + 1
    nb = np.ceil((n - 1) / block).astype(int)
    # coarse test at block centres
    bi, bj, bk = np.meshgrid(np.arange(nb[0]), np.arange(nb[1]), np.arange(nb[2]), indexing="ij")
    bi, bj, bk = bi.ravel(), bj.ravel(), bk.ravel()
    cx = bmin[0] + (bi + 0.5) * block * h
    cy = bmin[1] + (bj + 0.5) * block * h
    cz = bmin[2] + (bk + 0.5) * block * h
    dc = f(cx, cy, cz)
    sel = np.abs(dc) < margin * 0.5 * np.sqrt(3) * block * h
    blocks = np.stack([bi[sel], bj[sel], bk[sel]], 1)
    if verbose:
        print(f"  grid {n}, blocks {len(blocks)}/{len(bi)}")
    lin = np.arange(block + 1)
    gi, gj, gk = np.meshgrid(lin, lin, lin, indexing="ij")
    gi, gj, gk = gi.ravel(), gj.ravel(), gk.ravel()
    allv, allf = [], []
    voff = 0
    for s in range(0, len(blocks), batch):
        grp = blocks[s:s + batch]
        X = bmin[0] + (grp[:, 0:1] * block + gi[None]) * h
        Y = bmin[1] + (grp[:, 1:2] * block + gj[None]) * h
        Z = bmin[2] + (grp[:, 2:3] * block + gk[None]) * h
        D = f(X.ravel(), Y.ravel(), Z.ravel()).reshape(len(grp), block + 1, block + 1, block + 1)
        for q in range(len(grp)):
            vol = D[q]
            if vol.min() >= 0 or vol.max() <= 0:
                continue
            try:
                v, fc, _, _ = marching_cubes(vol, 0.0, allow_degenerate=False)
            except Exception:
                continue
            base = grp[q] * block
            v = (v + base[None]) * h + bmin[None]
            allv.append(v)
            allf.append(fc + voff)
            voff += len(v)
    if not allv:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    V = np.concatenate(allv)
    F = np.concatenate(allf).astype(np.int64)
    # weld duplicates on block borders
    key = np.round(V / (h * 1e-4)).astype(np.int64)
    _, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    V = V[idx]
    F = inv.ravel()[F]
    good = (F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 0] != F[:, 2])
    F = F[good]
    if verbose:
        print(f"  verts {len(V)} faces {len(F)}")
    return V, F


def keep_faces(V, F, mask_fn):
    c = V[F].mean(1)
    m = mask_fn(c[:, 0], c[:, 1], c[:, 2])
    F = F[m]
    used = np.unique(F)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[F]


def clip_level(V, F, level_fn):
    """Keep the part of the mesh where level_fn >= 0, splitting triangles exactly on the zero line.

    Deleting whole triangles (keep_faces) leaves a sawtooth edge one triangle deep; this cuts
    along the iso-line instead (new vertices are shared between neighbours, so the cut stays
    watertight along its length)."""
    f = level_fn(V[:, 0], V[:, 1], V[:, 2]).astype(np.float64)
    pos = f >= 0
    k = pos[F].sum(1)
    out = [F[k == 3]]
    newV = []
    cache = {}

    def cut(i, j):
        if f[i] == 0:               # a vertex already on the cut line: reuse it
            return i
        if f[j] == 0:
            return j
        key = (min(i, j), max(i, j))
        if key not in cache:
            t = f[i] / (f[i] - f[j])
            cache[key] = len(V) + len(newV)
            newV.append(V[i] + t * (V[j] - V[i]))
        return cache[key]

    for tri, kk in zip(F[(k == 1) | (k == 2)], k[(k == 1) | (k == 2)]):
        a, b, c = tri
        # rotate so the odd vertex (the lone inside one for kk == 1, the lone outside one for kk == 2) is first
        for _ in range(3):
            if (pos[a] if kk == 1 else not pos[a]) and (pos[b] != pos[a]) and (pos[c] != pos[a]):
                break
            a, b, c = b, c, a
        ab, ac = cut(a, b), cut(a, c)
        if kk == 1:
            out.append(np.array([[a, ab, ac]]))
        else:
            out.append(np.array([[ab, b, c], [ab, c, ac]]))
    if newV:
        V = np.concatenate([V, np.array(newV)])
    F = np.concatenate(out)
    F = F[(F[:, 0] != F[:, 1]) & (F[:, 1] != F[:, 2]) & (F[:, 2] != F[:, 0])]
    used = np.unique(F)
    remap = -np.ones(len(V), np.int64)
    remap[used] = np.arange(len(used))
    return V[used], remap[F]


def decimate(V, F, reduction=0.85, agg=7):
    import fast_simplification
    V2, F2 = fast_simplification.simplify(V.astype(np.float32), F.astype(np.int32),
                                          target_reduction=reduction, agg=agg)
    return V2.astype(np.float64), F2.astype(np.int64)


def sdf_normals(f, V, eps=4e-4):
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    gx = f(x + eps, y, z) - f(x - eps, y, z)
    gy = f(x, y + eps, z) - f(x, y - eps, z)
    gz = f(x, y, z + eps) - f(x, y, z - eps)
    N = np.stack([gx, gy, gz], 1)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-12
    return N


def project_to_surface(f, V, iters=2, eps=4e-4):
    """Newton-project vertices back onto the iso-surface (after decimation)."""
    for _ in range(iters):
        d = f(V[:, 0], V[:, 1], V[:, 2])
        N = sdf_normals(f, V, eps)
        V = V - N * d[:, None]
    return V


def orient_faces(V, F, N):
    """Flip faces so geometric normal agrees with vertex normals."""
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = N[F].sum(1)
    flip = (fn * vn).sum(1) < 0
    F = F.copy()
    F[flip] = F[flip][:, [0, 2, 1]]
    return F


def refine(f, V, F, N=None, max_angle=10.0, min_len=0.0012, iters=3, eps=3e-4, verbose=False):
    """Adaptive edge-split refinement where vertex normals disagree, projecting new
    vertices onto the iso-surface. Keeps the mesh crack-free (1/2/3-split templates)."""
    if N is None:
        N = sdf_normals(f, V, eps)
    cos_t = np.cos(np.radians(max_angle))
    for it in range(iters):
        E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        Es = np.sort(E, 1)
        uniq, inv = np.unique(Es, axis=0, return_inverse=True)
        inv = inv.ravel()
        a, b = uniq[:, 0], uniq[:, 1]
        L = np.linalg.norm(V[a] - V[b], axis=1)
        dots = (N[a] * N[b]).sum(1)
        split = (dots < cos_t) & (L > min_len)
        if not split.any():
            break
        mid_idx = -np.ones(len(uniq), np.int64)
        ns = int(split.sum())
        mid_idx[split] = len(V) + np.arange(ns)
        M = 0.5 * (V[a[split]] + V[b[split]])
        M = project_to_surface(f, M, 2, eps)
        MN = sdf_normals(f, M, eps)
        V = np.concatenate([V, M])
        N = np.concatenate([N, MN])
        nf = len(F)
        e01 = mid_idx[inv[:nf]]
        e12 = mid_idx[inv[nf:2 * nf]]
        e20 = mid_idx[inv[2 * nf:]]
        out = []
        v0, v1, v2 = F[:, 0], F[:, 1], F[:, 2]
        s01, s12, s20 = e01 >= 0, e12 >= 0, e20 >= 0
        cnt = s01.astype(int) + s12 + s20
        m = cnt == 0
        out.append(F[m])
        # one split: rotate so the split edge is 01
        for sm, (A, Bv, C, M01) in [(s01 & (cnt == 1), (v0, v1, v2, e01)),
                                    (s12 & (cnt == 1), (v1, v2, v0, e12)),
                                    (s20 & (cnt == 1), (v2, v0, v1, e20))]:
            out.append(np.stack([A[sm], M01[sm], C[sm]], 1))
            out.append(np.stack([M01[sm], Bv[sm], C[sm]], 1))
        # two splits: the unsplit edge identifies orientation
        for sm, (A, Bv, C, Mab, Mbc) in [((cnt == 2) & ~s20, (v0, v1, v2, e01, e12)),
                                         ((cnt == 2) & ~s01, (v1, v2, v0, e12, e20)),
                                         ((cnt == 2) & ~s12, (v2, v0, v1, e20, e01))]:
            out.append(np.stack([A[sm], Mab[sm], Mbc[sm]], 1))
            out.append(np.stack([Mab[sm], Bv[sm], Mbc[sm]], 1))
            out.append(np.stack([A[sm], Mbc[sm], C[sm]], 1))
        m3 = cnt == 3
        out.append(np.stack([v0[m3], e01[m3], e20[m3]], 1))
        out.append(np.stack([e01[m3], v1[m3], e12[m3]], 1))
        out.append(np.stack([e20[m3], e12[m3], v2[m3]], 1))
        out.append(np.stack([e01[m3], e12[m3], e20[m3]], 1))
        F = np.concatenate(out)
        if verbose:
            print(f'   refine {it}: split {ns} edges -> {len(F)} faces')
    return V, F, N


def finish(f, V, F, reduction=0.8, refine_iters=3, max_angle=9.0, min_len=0.0012):
    """Decimate, snap to surface, adaptively refine creases, orient."""
    if reduction > 0:
        V, F = decimate(V, F, reduction)
    V = project_to_surface(f, V, 2)
    N = sdf_normals(f, V)
    V, F, N = refine(f, V, F, N, max_angle=max_angle, iters=refine_iters, min_len=min_len)
    F = orient_faces(V, F, N)
    return V, F, N


def budget(f, V, F, N, target):
    """Bring a refined mesh down to ~target triangles with QEM, then re-snap and re-normal."""
    if len(F) <= target:
        return V, F, N
    V, F = decimate(V, F, 1.0 - target / len(F), agg=5)
    V = project_to_surface(f, V, 2)
    N = sdf_normals(f, V)
    F = orient_faces(V, F, N)
    return V, F, N


def finish2(f, V, F, target, refine_iters=3, max_angle=8.0, min_len=0.0008):
    """Snap raw MC mesh, refine creases first, then QEM down to `target` triangles."""
    V = project_to_surface(f, V, 2)
    N = sdf_normals(f, V)
    V, F, N = refine(f, V, F, N, max_angle=max_angle, iters=refine_iters, min_len=min_len)
    if target and len(F) > target:
        V, F = decimate(V, F, 1.0 - target / len(F), agg=4)
        V = project_to_surface(f, V, 2)
        N = sdf_normals(f, V)
    F = orient_faces(V, F, N)
    return V, F, N


def decimate_ml(V, F, target, N=None, crease_weight=True):
    """Feature-aware QEM via PyMeshLab (keeps refined creases)."""
    import pymeshlab
    ms = pymeshlab.MeshSet()
    q = None
    if crease_weight and N is not None:
        # vertex quality = max normal deviation to neighbours (creases get high weight)
        E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        dev = 1.0 - (N[E[:, 0]] * N[E[:, 1]]).sum(1)
        q = np.zeros(len(V))
        np.maximum.at(q, E[:, 0], dev)
        np.maximum.at(q, E[:, 1], dev)
        q = 1.0 + 200.0 * np.clip(q, 0, 0.05)
    m = pymeshlab.Mesh(vertex_matrix=V, face_matrix=F.astype(np.int32),
                       v_normals_matrix=N if N is not None else np.zeros((0, 3)),
                       v_scalar_array=q if q is not None else np.zeros(0))
    ms.add_mesh(m)
    ms.meshing_decimation_quadric_edge_collapse(targetfacenum=int(target), qualitythr=0.4, preserveboundary=True,
                                                boundaryweight=2.0, preservenormal=True, preservetopology=False,
                                                optimalplacement=True, planarquadric=True, planarweight=0.002,
                                                qualityweight=q is not None, autoclean=True)
    mm = ms.current_mesh()
    return mm.vertex_matrix().astype(np.float64), mm.face_matrix().astype(np.int64)


def finish3(f, V, F, target, refine_iters=3, max_angle=8.0, min_len=0.0008):
    V = project_to_surface(f, V, 2)
    N = sdf_normals(f, V)
    V, F, N = refine(f, V, F, N, max_angle=max_angle, iters=refine_iters, min_len=min_len)
    if target and len(F) > target:
        V, F = decimate_ml(V, F, target, N)
        V = project_to_surface(f, V, 2)
        N = sdf_normals(f, V)
    F = orient_faces(V, F, N)
    return V, F, N


def decimate_mo(V, F, N, ratio, err=0.0005):
    """Attribute-aware simplification (meshoptimizer via gltfpack -sv). Returns V, F, N."""
    import subprocess, tempfile, os, trimesh, sys
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
    from pack import read_glb, accessor
    d = tempfile.mkdtemp()
    a, b = os.path.join(d, 'a.glb'), os.path.join(d, 'b.glb')
    trimesh.Trimesh(V, F, vertex_normals=N, process=False).export(a)
    subprocess.run([os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'node_modules', '.bin', 'gltfpack'), '-i', a, '-o', b, '-noq',
                    '-si', f'{ratio:.4f}', '-se', f'{err}', '-sv', '-kn', '-km'], check=True, capture_output=True)
    js, binc = read_glb(b)
    pr = js['meshes'][0]['primitives'][0]
    V2 = accessor(js, binc, pr['attributes']['POSITION'])
    N2 = accessor(js, binc, pr['attributes']['NORMAL'])
    F2 = accessor(js, binc, pr['indices'])[:, 0].reshape(-1, 3).astype(np.int64)
    # gltfpack may bake node transforms; trimesh exports identity so positions are as given
    return V2, F2, N2


def split_long(V, F, max_len, iters=6):
    """Conforming red-green bisection of every edge longer than max_len.

    The decimator leaves long slivers across flat panels; per-vertex attributes (baked AO,
    normals) interpolated along them show up as streaks fanning across the surface."""
    for _ in range(iters):
        E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
        Es = np.sort(E, 1)
        uniq, inv = np.unique(Es, axis=0, return_inverse=True)
        inv = inv.reshape(3, -1).T                          # face -> its 3 edge ids (e01, e12, e20)
        long_ = np.linalg.norm(V[uniq[:, 0]] - V[uniq[:, 1]], axis=1) > max_len
        if not long_.any():
            break
        mid = np.full(len(uniq), -1, np.int64)
        mid[long_] = len(V) + np.arange(long_.sum())
        V = np.concatenate([V, 0.5 * (V[uniq[long_, 0]] + V[uniq[long_, 1]])])
        M = mid[inv]                                        # midpoint per face edge or -1
        k = (M >= 0).sum(1)
        out = [F[k == 0]]
        # rotate each face so the pattern is canonical: 1 mark -> on e01; 2 marks -> e01 and e12
        for r in range(3):
            Fr, Mr = np.roll(F, -r, 1), np.roll(M, -r, 1)
            one = (k == 1) & (Mr[:, 0] >= 0)
            v0, v1, v2, m = Fr[one, 0], Fr[one, 1], Fr[one, 2], Mr[one, 0]
            out += [np.stack([v0, m, v2], 1), np.stack([m, v1, v2], 1)]
            two = (k == 2) & (Mr[:, 0] >= 0) & (Mr[:, 1] >= 0)
            v0, v1, v2, a, b = Fr[two, 0], Fr[two, 1], Fr[two, 2], Mr[two, 0], Mr[two, 1]
            out += [np.stack([a, v1, b], 1), np.stack([v0, a, b], 1), np.stack([v0, b, v2], 1)]
        three = k == 3
        v0, v1, v2 = F[three, 0], F[three, 1], F[three, 2]
        a, b, c = M[three, 0], M[three, 1], M[three, 2]
        out += [np.stack([v0, a, c], 1), np.stack([a, v1, b], 1), np.stack([c, b, v2], 1), np.stack([a, b, c], 1)]
        F = np.concatenate(out)
    return V, F


def finish4(f, V, F, target, refine_iters=3, max_angle=8.0, min_len=0.0008, err=0.0004, max_edge=None):
    V = project_to_surface(f, V, 2)
    N = sdf_normals(f, V)
    V, F, N = refine(f, V, F, N, max_angle=max_angle, iters=refine_iters, min_len=min_len)
    ratio = (target / len(F)) if target else 1.0
    if ratio < 1:
        V, F, N = decimate_mo(V, F, N, ratio, err)
        if max_edge:
            V, F = split_long(V, F, max_edge)
        V = project_to_surface(f, V, 1)
        N = sdf_normals(f, V)
    F = orient_faces(V, F, N)
    return V, F, N
