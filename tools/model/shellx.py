"""Exact (Euclidean) distance to the body shell surface.

The analytic shell SDF is only a bound: inside the cabin, where several primitives meet, its
magnitude can be far too small, which makes "N mm under the skin" layers (trims, seals, tubs)
appear in mid-air. Here the inside/outside classification of the analytic field is turned into
a true distance with a Euclidean distance transform on a voxel grid (computed once and cached);
within a few millimetres of the skin the analytic value, which is accurate there, is used.
"""
import os
import numpy as np
from scipy import ndimage
import body as B

OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
CACHE = os.path.join(OUT, 'shell_edt.npz')
H = 0.006
LO = np.array([-2.04, -0.98, 0.20])
HI = np.array([2.12, 0.98, 1.20])
NEAR = 0.008
_grid = None


def _build():
    n = np.ceil((HI - LO) / H).astype(int) + 1
    inside = np.zeros(n, bool)
    xs = LO[0] + np.arange(n[0]) * H
    ys = LO[1] + np.arange(n[1]) * H
    zs = LO[2] + np.arange(n[2]) * H
    Y, Z = np.meshgrid(ys, zs, indexing='ij')
    for i, x in enumerate(xs):          # slab by slab to bound memory
        inside[i] = B.shell(np.full(Y.shape, x), Y, Z) < 0
    d_out = ndimage.distance_transform_edt(~inside) * H
    d_in = ndimage.distance_transform_edt(inside) * H
    # signed distance to the voxel boundary (half-voxel offset to centre it on the surface)
    sd = np.where(inside, -(d_in - 0.5 * H), d_out - 0.5 * H).astype(np.float32)
    # the voxelised boundary quantises distances to ~H/2: smooth away the staircase
    sd = ndimage.gaussian_filter(sd, 1.3).astype(np.float32)
    np.savez_compressed(CACHE, sd=sd)
    return sd


def grid():
    global _grid
    if _grid is None:
        _grid = np.load(CACHE)['sd'] if os.path.exists(CACHE) else _build()
    return _grid


def to_skin(X, Y, Z, e=0.002):
    """Closest point on the skin (one Newton step along the field gradient).

    Panel regions are outlines extruded along a fixed axis, so where the skin runs almost along
    that axis (roof header, upper A-pillar) their iso-surfaces meet the skin at a shallow angle
    and any band cut by them smears and staircases. Evaluating a region at the projected point
    makes its cuts perpendicular to the skin instead."""
    X, Y, Z = np.broadcast_arrays(np.asarray(X, np.float64), Y, Z)
    s = shell(X, Y, Z)
    g = np.stack([shell(X + e, Y, Z) - shell(X - e, Y, Z), shell(X, Y + e, Z) - shell(X, Y - e, Z),
                  shell(X, Y, Z + e) - shell(X, Y, Z - e)]) / (2 * e)
    g /= np.maximum(np.linalg.norm(g, axis=0), 1e-9)
    return X - s * g[0], Y - s * g[1], Z - s * g[2]


def shell(X, Y, Z):
    X = np.asarray(X, np.float64)
    shp = np.shape(X)
    x, y, z = np.ravel(X), np.ravel(np.broadcast_to(Y, shp)), np.ravel(np.broadcast_to(Z, shp))
    g = grid()
    coords = np.stack([(x - LO[0]) / H, (y - LO[1]) / H, (z - LO[2]) / H])
    e = ndimage.map_coordinates(g, coords, order=1, mode='nearest')
    a = B.shell(x, y, z)
    # near the skin the analytic field is a good distance; blend into the EDT value further in
    w = np.clip((np.abs(a) - NEAR) / NEAR, 0, 1)
    out = a * (1 - w) + np.where(np.sign(e) == np.sign(a), e, a) * w
    return out.reshape(shp)
