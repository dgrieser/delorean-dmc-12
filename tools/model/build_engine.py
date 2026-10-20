"""Extract engine bay + front compartment parts."""
import os, sys, time
import numpy as np
from extract import extract, finish4
import engine as E

OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))


def P(name, f, bmin, bmax, h, target):
    return dict(name=name, f=f, bmin=bmin, bmax=bmax, h=h, target=target)


PARTS = [
    P('eng_block', E.block, (-1.92, -0.40, 0.18), (-0.88, 0.40, 0.70), 0.004, 40000),
    P('eng_covers', E.cam_covers, (-1.86, -0.42, 0.40), (-1.28, 0.42, 0.72), 0.0022, 30000),
    P('eng_intake', E.intake, (-1.86, -0.18, 0.50), (-1.22, 0.18, 0.78), 0.0025, 25000),
    P('eng_airbox', E.airbox, (-1.66, -0.12, 0.58), (-1.18, 0.30, 0.82), 0.003, 12000),
    P('eng_decal', E.airbox_decal, (-1.53, -0.04, 0.775), (-1.25, 0.20, 0.79), 0.0008, 600),
    P('eng_exhaust', E.exhaust_manifolds, (-1.95, -0.50, 0.24), (-1.26, 0.50, 0.66), 0.003, 16000),
    P('eng_tank', E.coolant_tank, (-1.68, -0.56, 0.58), (-1.32, -0.38, 0.76), 0.002, 8000),
    P('eng_aux', E.ancillaries, (-1.92, -0.34, 0.30), (-1.62, 0.36, 0.60), 0.0022, 14000),
    P('eng_battery', E.battery, (-1.10, -0.55, 0.37), (-0.86, -0.33, 0.57), 0.003, 3000),
    P('eng_hoses', E.hoses, (-1.84, -0.52, 0.36), (-0.86, 0.46, 0.70), 0.003, 16000),
    P('bay_tub', E.bay_tub, (-1.97, -0.93, 0.20), (-0.78, 0.93, 0.88), 0.006, 24000),
    P('bay_panel', E.firewall_panel, (-0.85, -0.43, 0.57), (-0.81, -0.17, 0.75), 0.0015, 600),
    P('frunk_tub', E.frunk_tub, (0.86, -0.93, 0.38), (2.04, 0.93, 0.82), 0.006, 24000),
    P('fuel_tank', E.fuel_tank, (0.85, -0.55, 0.39), (1.30, 0.55, 0.84), 0.004, 10000),
    P('spare_tyre', E.spare_tyre, (1.36, -0.34, 0.38), (2.04, 0.34, 0.56), 0.003, 12000),
    P('spare_rim', E.spare_rim, (1.50, -0.20, 0.41), (1.90, 0.20, 0.53), 0.003, 6000),
    P('extinguisher', E.extinguisher, (1.24, -0.50, 0.41), (1.36, -0.07, 0.51), 0.002, 3000),
]


import body as B


def inside(f):
    return lambda X, Y, Z: np.maximum(f(X, Y, Z), B.shell(X, Y, Z) + 0.005)


def build(p):
    t = time.time()
    p = dict(p, f=inside(p['f']))
    V, F = extract(p['f'], p['bmin'], p['bmax'], p['h'], verbose=False)
    if len(F) == 0:
        print('EMPTY', p['name'], flush=True)
        return
    V, F, N = finish4(p['f'], V, F, p['target'], 2, max_angle=10.0, min_len=0.0006)
    np.savez_compressed(f"{OUT}/{p['name']}.npz", V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    print(f"{p['name']}: {len(V)} v {len(F)} f {time.time() - t:.1f}s", flush=True)


if __name__ == '__main__':
    sel = sys.argv[1:]
    for p in PARTS:
        if not sel or any(p['name'].startswith(s) for s in sel):
            build(p)
