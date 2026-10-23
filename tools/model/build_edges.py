"""Door edge walls (perimeter + window reveal) and the body's door-aperture jambs.

Each is a closed solid band from just under the skin down to the trim depth: its outer face hides
inside the panel's own rolled edge wall, the edge-side wall continues that wall inward, and a narrow
flange runs under the trim's end, so the door and aperture read as solid from every side."""
import os, sys, time
import numpy as np
from extract import extract, finish4
from sdf import smax
import body as B
import interior as I
import shellx as SX
import build_shell as S

OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
GAP = S.GAP
LIFT = 0.005      # edge flanges sit this much behind the trim surface, so the trim always wins
BAND = 0.018      # flange width measured from the panel edge (trims stop at I.TRIM_RECESS, well inside it)
JAMB_D = 0.028 - LIFT
INSET = 0.0025    # walls sit behind the skin's own rolled edge wall (build_shell DEPTH) where they overlap


SKIN = 0.0095     # solids start this far under the skin, inside the panels' own edge walls (12 mm)


def door_solid(side):
    def f(X, Y, Z):
        s = SX.shell(X, Y, Z)
        reg = np.maximum(B.r_door(X, Y, Z, side), -B.r_door_glass(X, Y, Z, side))
        d = smax(s + SKIN, reg + GAP / 2 + INSET, 0.0015)
        d = smax(d, -(s + I.door_t(Z) - LIFT), 0.002)
        # a frame band along the edges (the trim covers the rest) plus everything below the door card,
        # closed off at the skins' lower cut; all bounds live in the field, so every edge is clean.
        # The band is measured on the skin so its inner wall stands square to it.
        Xs, Ys, Zs = SX.to_skin(X, Y, Z)
        reg_s = np.maximum(B.r_door(Xs, Ys, Zs, side), -B.r_door_glass(Xs, Ys, Zs, side))
        band = np.minimum(-(reg_s + I.DOOR_FRAME + 0.010 + I.front_end(X)), Z - 0.35)
        d = smax(d, band, 0.0015)
        # below the card only out at the sill: further in, the body's bottom skin lies within reach
        # of the outline, which would hang a slab under the whole cabin floor on the door
        d = np.maximum(d, np.minimum(0.35 - Z, -(B.flanks(X, Y, Z) + 0.09)))
        # the door outline is extruded across the car: keep the solid off the inside of the
        # windscreen, which the A-pillar corner of that outline reaches (skin points on the glass
        # sit 12 mm outside the door region, r_door's windscreen clearance)
        d = np.maximum(d, reg_s - 0.008)
        return smax(d, B.SILL_Z - Z, 0.0015)
    return f


def jamb_solid(side):
    def f(X, Y, Z):
        s = SX.shell(X, Y, Z)
        d = smax(s + SKIN, GAP / 2 + INSET - B.r_door(X, Y, Z, side), 0.0015)
        d = smax(d, -(s + JAMB_D), 0.002)
        # only a band around the aperture (measured on the skin), ending in a clean wall under the trim
        d = smax(d, B.r_door(*SX.to_skin(X, Y, Z), side) - BAND, 0.0015)
        # The aperture flange must stop behind the windscreen reveal, not extend
        # through its glass at the shallow upper A-pillar junction.
        d = smax(d, -(B.r_windshield(X, Y, Z) - 0.004), 0.002)
        return smax(d, B.SILL_Z + 0.005 - Z, 0.0015)
    return f


def aperture_seal(side):
    def f(X, Y, Z):
        s = SX.shell(X, Y, Z)
        edge = B.r_door(*SX.to_skin(X, Y, Z), side)
        tube = np.sqrt((s + 0.025) ** 2 + (edge - 0.005) ** 2) - 0.005
        return np.maximum(tube, B.SILL_Z + 0.010 - Z)
    return f


PARTS = []
for side, tag in [(1, 'L'), (-1, 'R')]:
    ylo, yhi = (0.08, 0.96) if side > 0 else (-0.96, -0.08)
    PARTS.append((f'door_edge_{tag}', door_solid(side), (-0.78, ylo, 0.24), (0.72, yhi, 1.16), 30000))
    PARTS.append((f'jamb_{tag}', jamb_solid(side), (-0.82, ylo - 0.02 * side, 0.26), (0.76, yhi, 1.16), 24000))
    PARTS.append((f'door_seal_{tag}', aperture_seal(side), (-0.82, ylo - 0.02 * side, 0.30), (0.76, yhi, 1.16), 12000))

if __name__ == '__main__':
    sel = sys.argv[1:]
    for name, f, lo, hi, tgt in PARTS:
        if sel and not any(name.startswith(s) for s in sel):
            continue
        t = time.time()
        lo, hi = np.minimum(lo, hi), np.maximum(lo, hi)
        V, F = extract(f, lo, hi, 0.004, verbose=False)
        V, F, N = finish4(f, V, F, tgt, 2, max_angle=10.0, min_len=0.0008)
        np.savez_compressed(f'{OUT}/{name}.npz', V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
        print(f'{name}: {len(V)} v {len(F)} f {time.time() - t:.1f}s', flush=True)
