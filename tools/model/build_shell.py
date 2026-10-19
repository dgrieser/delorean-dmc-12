"""Extract all outer-shell parts of the body and save them as NPZ (+ a preview GLB)."""
import sys, time, os
import numpy as np
from extract import extract, decimate, sdf_normals, orient_faces, project_to_surface, keep_faces, finish4
from sdf import smax, smin
import body as B

H = float(os.environ.get('H', '0.006'))
GAP = 0.0045
ROLL = 0.004
DEPTH = 0.012
OUT = os.environ.get('OUT', '/home/user/delorean-dmc-12/tools/out')
os.makedirs(OUT, exist_ok=True)


def door_L(X, Y, Z):
    return np.maximum(B.r_door(X, Y, Z, 1), -B.r_door_glass(X, Y, Z, 1))


def door_R(X, Y, Z):
    return np.maximum(B.r_door(X, Y, Z, -1), -B.r_door_glass(X, Y, Z, -1))


def hood(X, Y, Z):
    return np.maximum(B.r_hood(X, Y, Z), -B.r_fuel(X, Y, Z))


def cut_all(X, Y, Z):
    r = np.minimum(B.r_door(X, Y, Z, 1), B.r_door(X, Y, Z, -1))
    r = np.minimum(r, B.r_hood(X, Y, Z))
    r = np.minimum(r, B.r_lid(X, Y, Z))
    r = np.minimum(r, B.r_windshield(X, Y, Z))
    r = np.minimum(r, B.r_quarter(X, Y, Z))
    return r


def panel(region):
    def f(X, Y, Z):
        return smax(B.shell(X, Y, Z), region(X, Y, Z) + GAP / 2, ROLL)
    return f


def fixed(X, Y, Z):
    return smax(B.shell(X, Y, Z), GAP / 2 - cut_all(X, Y, Z), ROLL)


def skin_mask(X, Y, Z):
    return B.shell(X, Y, Z) > -DEPTH


PARTS = {
    'body': (fixed, B.BODY_BMIN, B.BODY_BMAX, True),
    'door_L': (panel(door_L), (-0.76, 0.09, 0.23), (0.70, 0.95, 1.16), True),
    'door_R': (panel(door_R), (-0.76, -0.95, 0.23), (0.70, -0.09, 1.16), True),
    'hood': (panel(hood), (0.62, -0.90, 0.60), (2.07, 0.90, 0.87), True),
    'fuel_flap': (panel(B.r_fuel), (0.85, 0.08, 0.80), (1.06, 0.29, 0.87), True),
    'lid_skin': (panel(B.r_lid), (-1.95, -0.80, 0.82), (-0.70, 0.80, 1.14), True),
    'bumper_f': (B.front_bumper, B.FBUMP_BMIN, B.FBUMP_BMAX, False),
    'bumper_r': (B.rear_bumper, B.RBUMP_BMIN, B.RBUMP_BMAX, False),
    'rocker': (B.rocker, B.ROCKER_BMIN, B.ROCKER_BMAX, False),
    'airdam': (B.airdam, B.AIRDAM_BMIN, B.AIRDAM_BMAX, False),
}


BUDGET = {'body': 260000, 'hood': 40000, 'bumper_f': 40000, 'bumper_r': 42000, 'rocker': 10000, 'lid_skin': 1000,
          'door_L': 45000, 'door_R': 45000, 'fuel_flap': 2500, 'airdam': 24000}


# stainless panels: split long slivers (baked AO smears along them); dark/flat parts are left as is
SPLIT = {'body', 'door_L', 'door_R', 'hood', 'fuel_flap'}


def build(name, reduction=0.86):
    f, a, b, skin = PARTS[name]
    t = time.time()
    V, F = extract(f, a, b, H, verbose=False)
    if skin:
        def m(x, y, z):
            keep = skin_mask(x, y, z)
            under = z < 0.285
            # the nose skin below the front bumper's lower edge (z 0.336) would show as a steel lip
            under |= (x > 1.70) & (z < 0.345)
            return keep & ~under
        V, F = keep_faces(V, F, m)
    V, F, N = finish4(f, V, F, BUDGET.get(name, 30000), int(os.environ.get('REFINE', '3')), max_edge=0.05 if name in SPLIT else None)
    np.savez_compressed(f'{OUT}/{name}.npz', V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    print(f'{name}: {len(V)} verts {len(F)} faces {time.time() - t:.1f}s', flush=True)
    return V, F, N


if __name__ == '__main__':
    names = sys.argv[1:] or list(PARTS)
    for n in names:
        build(n)
