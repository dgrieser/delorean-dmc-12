"""Projected surface patches: 2D outline -> mesh lying on an SDF surface.

Used for glass, lenses, trim strips, decals and seals so that they follow the body
exactly with clean boundaries."""
import numpy as np
from scipy.spatial import Delaunay
from sdf import poly2d
from extract import sdf_normals

AX = {'X': 0, 'Y': 1, 'Z': 2}


def resample_poly(pts, step):
    pts = np.asarray(pts, np.float64)
    out = []
    n = len(pts)
    for i in range(n):
        a, b = pts[i], pts[(i + 1) % n]
        L = np.linalg.norm(b - a)
        k = max(1, int(np.ceil(L / step)))
        for j in range(k):
            out.append(a + (b - a) * j / k)
    return np.array(out)


def round_poly(pts, r, seg=6):
    """Replace each corner by a circular-ish fillet of radius r (approx)."""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    out = []
    for i in range(n):
        p0, p1, p2 = pts[i - 1], pts[i], pts[(i + 1) % n]
        d0 = p0 - p1
        d2 = p2 - p1
        l0, l2 = np.linalg.norm(d0), np.linalg.norm(d2)
        rr = min(r, 0.45 * l0, 0.45 * l2)
        a = p1 + d0 / l0 * rr
        b = p1 + d2 / l2 * rr
        for t in np.linspace(0, 1, seg):
            # quadratic bezier a -> p1 -> b
            out.append((1 - t) ** 2 * a + 2 * (1 - t) * t * p1 + t * t * b)
    return np.array(out)


def region2d(u, v, pts, holes=()):
    d = poly2d(u, v, pts)
    for h in holes:
        d = np.maximum(d, -poly2d(u, v, h))
    return d


def tri_poly(pts, step, holes=()):
    """Triangulate polygon interior (optionally with holes) with roughly uniform spacing."""
    bnd = resample_poly(pts, step * 0.6)
    hb = [resample_poly(h, step * 0.6) for h in holes]
    lo = bnd.min(0)
    hi = bnd.max(0)
    gu, gv = np.meshgrid(np.arange(lo[0], hi[0], step), np.arange(lo[1], hi[1], step * 0.866))
    gu = gu + (np.arange(gu.shape[0])[:, None] % 2) * step * 0.5
    gu, gv = gu.ravel(), gv.ravel()
    d = region2d(gu, gv, pts, holes)
    inner = np.stack([gu[d < -step * 0.35], gv[d < -step * 0.35]], 1)
    P = np.concatenate([bnd] + hb + [inner])
    tri = Delaunay(P)
    T = tri.simplices
    c = P[T].mean(1)
    keep = region2d(c[:, 0], c[:, 1], pts, holes) < 0
    return P, T[keep], len(bnd)


def project(f, P2, axes, proj, side, iters=80):
    """Sphere-trace from outside along -side*proj to the f=0 surface."""
    n = len(P2)
    V = np.zeros((n, 3))
    V[:, AX[axes[0]]] = P2[:, 0]
    V[:, AX[axes[1]]] = P2[:, 1]
    k = AX[proj]
    V[:, k] = side * 1.4
    for _ in range(iters):
        d = f(V[:, 0], V[:, 1], V[:, 2])
        V[:, k] -= side * np.clip(d, -0.05, 0.08) * 0.8
    # polish with a few secant steps
    for _ in range(4):
        d = f(V[:, 0], V[:, 1], V[:, 2])
        e = 1e-4
        V2 = V.copy()
        V2[:, k] -= side * e
        d2 = f(V2[:, 0], V2[:, 1], V2[:, 2])
        g = (d - d2) / e
        g = np.where(np.abs(g) < 0.05, 0.05 * np.sign(g + 1e-9), g)
        V[:, k] -= side * d / g
    return V


def patch(f, pts, axes=('X', 'Z'), proj='Y', side=1, offset=0.0, step=0.012, rounded=0.0, thickness=0.0, holes=()):
    """Mesh lying on surface f inside 2D outline `pts` (in `axes` plane) seen from +side*proj.

    Returns V, F, N (normals pointing outward of f). With thickness>0 builds a closed slab
    (outer at offset, inner at offset-thickness, plus rim)."""
    if rounded > 0:
        pts = round_poly(pts, rounded)
    P2, T, nb = tri_poly(pts, step, holes)
    V = project(f, P2, axes, proj, side)
    N = sdf_normals(f, V)
    Vo = V + N * offset
    F = T.copy()
    # orient outward
    a, b, c = Vo[F[:, 0]], Vo[F[:, 1]], Vo[F[:, 2]]
    fn = np.cross(b - a, c - a)
    flip = (fn * N[F].sum(1)).sum(1) < 0
    F[flip] = F[flip][:, [0, 2, 1]]
    if thickness <= 0:
        return Vo, F, N
    Vi = V + N * (offset - thickness)
    n = len(V)
    Fi = F[:, [0, 2, 1]] + n
    # rim along boundary ring (first nb points form the boundary loop in order)
    ring = np.arange(nb)
    rim = []
    for i in range(nb):
        j = (i + 1) % nb
        rim.append([ring[i], ring[j], ring[j] + n])
        rim.append([ring[i], ring[j] + n, ring[i] + n])
    rim = np.array(rim)
    VV = np.concatenate([Vo, Vi])
    NN = np.concatenate([N, -N])
    FF = np.concatenate([F, Fi, rim])
    # orient rim outward: compare with direction from centroid
    cen = VV.mean(0)
    a, b, c = VV[rim[:, 0]], VV[rim[:, 1]], VV[rim[:, 2]]
    fn = np.cross(b - a, c - a)
    out = ((a + b + c) / 3 - cen)
    fl = (fn * out).sum(1) < 0
    rim[fl] = rim[fl][:, [0, 2, 1]]
    FF = np.concatenate([F, Fi, rim])
    return VV, FF, NN


def region_outline(f, region, axes, proj, side, lo, hi, res=0.004, level=0.0):
    """Outline (largest contour) of {region<level} on surface f, in the 2D `axes` plane."""
    from skimage.measure import find_contours
    us = np.arange(lo[0], hi[0], res)
    vs = np.arange(lo[1], hi[1], res)
    gu, gv = np.meshgrid(us, vs, indexing='ij')
    P2 = np.stack([gu.ravel(), gv.ravel()], 1)
    V = project(f, P2, axes, proj, side)
    r = region(V[:, 0], V[:, 1], V[:, 2]).reshape(gu.shape)
    cs = find_contours(r, level)
    c = max(cs, key=len)
    pts = np.stack([lo[0] + c[:, 0] * res, lo[1] + c[:, 1] * res], 1)
    # drop closing duplicate and decimate to ~2mm spacing
    if np.allclose(pts[0], pts[-1]):
        pts = pts[:-1]
    keep = [0]
    for i in range(1, len(pts)):
        if np.linalg.norm(pts[i] - pts[keep[-1]]) > 0.004:
            keep.append(i)
    return pts[keep]


def offset_poly(pts, dist):
    """Offset a polygon outward (dist>0) using shapely-free miter approximation via SDF contour."""
    from skimage.measure import find_contours
    pts = np.asarray(pts)
    lo = pts.min(0) - abs(dist) - 0.02
    hi = pts.max(0) + abs(dist) + 0.02
    res = 0.002
    us = np.arange(lo[0], hi[0], res)
    vs = np.arange(lo[1], hi[1], res)
    gu, gv = np.meshgrid(us, vs, indexing='ij')
    d = poly2d(gu.ravel(), gv.ravel(), pts).reshape(gu.shape)
    c = max(find_contours(d, dist), key=len)
    out = np.stack([lo[0] + c[:, 0] * res, lo[1] + c[:, 1] * res], 1)
    if np.allclose(out[0], out[-1]):
        out = out[:-1]
    keep = [0]
    for i in range(1, len(out)):
        if np.linalg.norm(out[i] - out[keep[-1]]) > 0.004:
            keep.append(i)
    # A contour passing exactly through a grid vertex can repeat its start
    # after thinning. The zero-length closing edge makes polygon distances NaN.
    while len(keep) > 3 and np.linalg.norm(out[keep[-1]] - out[keep[0]]) < 1e-9:
        keep.pop()
    return out[keep]
