"""Extract all outer-shell parts of the body and save them as NPZ (+ a preview GLB)."""
import sys, time, os
import numpy as np
from extract import extract, decimate, sdf_normals, orient_faces, project_to_surface, keep_faces, finish4, clip_level
from sdf import smax, smin
import body as B

H = float(os.environ.get('H', '0.006'))
GAP = 0.0045
ROLL = 0.004
DEPTH = 0.012
OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
os.makedirs(OUT, exist_ok=True)


def door_L(X, Y, Z):
    return np.maximum(B.r_door(X, Y, Z, 1), -B.r_door_glass(X, Y, Z, 1))


def door_R(X, Y, Z):
    return np.maximum(B.r_door(X, Y, Z, -1), -B.r_door_glass(X, Y, Z, -1))


def hood(X, Y, Z):
    return B.r_hood(X, Y, Z)


def cut_all(X, Y, Z):
    r = np.minimum(B.r_door(X, Y, Z, 1), B.r_door(X, Y, Z, -1))
    r = np.minimum(r, B.r_hood(X, Y, Z))
    r = np.minimum(r, B.r_lid(X, Y, Z))
    r = np.minimum(r, B.r_windshield(X, Y, Z))
    r = np.minimum(r, B.r_quarter(X, Y, Z))
    r = np.minimum(r, B.r_nose(X, Y, Z))
    r = np.minimum(r, B.r_tail(X, Y, Z))
    return r


def panel(region):
    def f(X, Y, Z):
        return smax(B.shell(X, Y, Z), region(X, Y, Z) + GAP / 2, ROLL)
    return f


def fixed(X, Y, Z):
    d = smax(B.shell(X, Y, Z), GAP / 2 - cut_all(X, Y, Z), ROLL)
    # the nose skin stops just below the airdam's top edge, hidden behind it (a cut in the field
    # gives a clean edge; a face mask would leave a sawtooth in the line under the bumper)
    nose = np.maximum(1.70 - X, Z - (B.FB_Z[0] - 0.03))
    return smax(d, -nose, 0.004)


def skin_mask(X, Y, Z):
    return B.shell(X, Y, Z) > -DEPTH


PARTS = {
    'body': (fixed, B.BODY_BMIN, B.BODY_BMAX, True),
    'door_L': (panel(door_L), (-0.76, 0.09, 0.23), (0.70, 0.95, 1.16), True),
    'door_R': (panel(door_R), (-0.76, -0.95, 0.23), (0.70, -0.09, 1.16), True),
    'hood': (panel(hood), (0.62, -0.90, 0.60), (2.07, 0.90, 0.87), True),
    'lid_skin': (panel(B.r_lid), (-1.95, -0.80, 0.82), (-0.70, 0.80, 1.14), True),
    'nose': (panel(B.r_nose), (1.78, -0.92, 0.48), (2.06, 0.92, 0.76), True),
    'tail': (panel(B.r_tail), (-2.10, -0.92, 0.53), (-1.79, 0.92, 0.90), True),
    'bumper_f': (B.front_bumper, B.FBUMP_BMIN, B.FBUMP_BMAX, False),
    'bumper_r': (B.rear_bumper, B.RBUMP_BMIN, B.RBUMP_BMAX, False),
    'rocker': (B.rocker, B.ROCKER_BMIN, B.ROCKER_BMAX, False),
    'airdam': (B.airdam, B.AIRDAM_BMIN, B.AIRDAM_BMAX, False),
    'fstrip': (B.front_strip, B.FSTRIP_BMIN, B.FSTRIP_BMAX, False),
    'rvalance': (B.rear_valance, B.RVAL_BMIN, B.RVAL_BMAX, False),
}


BUDGET = {'body': 240000, 'hood': 40000, 'nose': 30000, 'tail': 30000, 'bumper_f': 40000, 'bumper_r': 42000, 'rocker': 10000, 'lid_skin': 1000,
          'door_L': 45000, 'door_R': 45000, 'airdam': 24000, 'rvalance': 6000, 'fstrip': 12000}


# stainless panels: split long slivers (baked AO smears along them); dark/flat parts are left as is
SPLIT = {'body', 'door_L', 'door_R', 'hood', 'nose', 'tail'}


def build(name, reduction=0.86):
    f, a, b, skin = PARTS[name]
    t = time.time()
    V, F = extract(f, a, b, H, verbose=False)
    if skin:
        # skin down to DEPTH (the rolled edge walls) and nothing under the floor line, cut exactly
        # stop at the sill line and turn only ARCH_LIP into the wheel arches (black liners beyond)
        V, F = clip_level(V, F, lambda x, y, z: np.minimum(np.minimum(B.shell(x, y, z) + DEPTH, z - B.SILL_Z),
                                                           np.maximum(B.flanks(x, y, z) + B.ARCH_LIP, B.arch_cyl(x, y, z, 0.01))))
    V, F, N = finish4(f, V, F, BUDGET.get(name, 30000), int(os.environ.get('REFINE', '3')), max_edge=0.05 if name in SPLIT else None)
    np.savez_compressed(f'{OUT}/{name}.npz', V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    print(f'{name}: {len(V)} verts {len(F)} faces {time.time() - t:.1f}s', flush=True)
    return V, F, N


if __name__ == '__main__':
    names = sys.argv[1:] or list(PARTS)
    for n in names:
        build(n)
