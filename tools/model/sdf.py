"""Small numpy signed-distance-field toolkit used to sculpt the DMC-12 body.

Convention: negative inside, positive outside. Car frame: X forward, Y left, Z up,
metres, ground at z=0, X=0 at mid wheelbase.
"""
import numpy as np


def smin(a, b, r):
    """Polynomial smooth union (fillet radius ~r; r may vary per point)."""
    if np.ndim(r) == 0 and r <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / r, 0.0, 1.0)
    return b * (1 - h) + a * h - r * h * (1 - h)


def smax(a, b, r):
    """Smooth intersection."""
    return -smin(-a, -b, r)


def smax_n(ds, r):
    out = ds[0]
    for d in ds[1:]:
        out = smax(out, d, r)
    return out


def plane(px, py, pz, origin, normal):
    n = np.asarray(normal, dtype=np.float64)
    n = n / np.linalg.norm(n)
    o = np.asarray(origin, dtype=np.float64)
    return (px - o[0]) * n[0] + (py - o[1]) * n[1] + (pz - o[2]) * n[2]


def interp(x, xs, ys):
    """Piecewise linear interpolation with clamped ends (xs ascending)."""
    return np.interp(x, xs, ys)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def cubic_interp(x, xs, ys):
    """Monotone-ish smooth interpolation (Catmull-Rom style via scipy PCHIP)."""
    from scipy.interpolate import PchipInterpolator
    f = PchipInterpolator(np.asarray(xs), np.asarray(ys), extrapolate=True)
    xc = np.clip(x, xs[0], xs[-1])
    return f(xc)


def poly2d(u, v, pts):
    """Signed distance to a closed 2D polygon (pts Nx2) evaluated at arrays u, v."""
    pts = np.asarray(pts, dtype=np.float64)
    n = len(pts)
    d2 = np.full(u.shape, np.inf)
    sign = np.ones(u.shape)
    for i in range(n):
        a = pts[i]
        b = pts[(i + 1) % n]
        eu, ev = b[0] - a[0], b[1] - a[1]
        wu, wv = u - a[0], v - a[1]
        t = np.clip((wu * eu + wv * ev) / (eu * eu + ev * ev), 0, 1)
        du, dv = wu - eu * t, wv - ev * t
        d2 = np.minimum(d2, du * du + dv * dv)
        c1 = v >= a[1]
        c2 = v < b[1]
        c3 = eu * wv > ev * wu
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        sign = np.where(flip, -sign, sign)
    return sign * np.sqrt(d2)


def box(px, py, pz, center, half):
    qx = np.abs(px - center[0]) - half[0]
    qy = np.abs(py - center[1]) - half[1]
    qz = np.abs(pz - center[2]) - half[2]
    ox = np.maximum(qx, 0)
    oy = np.maximum(qy, 0)
    oz = np.maximum(qz, 0)
    outside = np.sqrt(ox * ox + oy * oy + oz * oz)
    inside = np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0)
    return outside + inside


def cyl_y(px, py, pz, cx, cz, r):
    """Infinite cylinder along Y."""
    return np.sqrt((px - cx) ** 2 + (pz - cz) ** 2) - r
