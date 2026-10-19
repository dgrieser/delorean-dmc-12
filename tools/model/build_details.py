"""Extract all exterior detail parts to NPZ."""
import os, sys, time
import numpy as np
from extract import extract, finish4
import body as B
import details as D

OUT = os.environ.get('OUT', '/home/user/delorean-dmc-12/tools/out')
os.makedirs(OUT, exist_ok=True)


def mirror_parts(f):
    """Build for +Y side; the -Y copy is mirrored."""
    return f


def P(name, f, bmin, bmax, h, red=0.6, mirror=False, refine=2):
    return dict(name=name, f=f, bmin=bmin, bmax=bmax, h=h, red=red, mirror=mirror, refine=refine)


HLs = []
for i, (a, b) in enumerate(B.HL_Y):
    yc, hw = 0.5 * (a + b), 0.5 * (b - a)
    tag = 'Hi' if i == 0 else 'Lo'      # inner pair = high beams, outer = low beams
    bb = ((1.96, yc - hw - 0.01, B.HL_Z[0] - 0.01), (2.06, yc + hw + 0.01, B.HL_Z[1] + 0.01))
    HLs += [
        P(f'hl_lens_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_lens(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0018, 0.5, True),
        P(f'hl_refl_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_reflector(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0018, 0.5, True),
        P(f'hl_bulb_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_bulb(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0015, 0.3, True),
        P(f'hl_bezel_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_bezel(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0018, 0.6, True),
    ]

BUDGET = {'badge_dmc': 6000, 'badge_plate': 800, 'hl_bulb_Hi': 1200, 'hl_bulb_Lo': 1200, 'door_handle_L': 2000, 'door_handle_R': 2000,
          'bumper_letters': 9000, 'grille': 30000, 'lid_slats': 26000, 'underbody': 12000, 'liner_f': 14000, 'liner_r': 14000,
          'tl_housing': 22000, 'lid_frame': 16000, 'hl_bezel_Hi': 10000, 'hl_bezel_Lo': 10000, 'exhaust': 9000,
          'hl_refl_Hi': 12000, 'hl_refl_Lo': 12000, 'tl_tail': 26000, 'mirror_L': 9000, 'mirror_R': 9000,
          'mirror_glass_L': 2000, 'mirror_glass_R': 2000, 'bpillar_vent': 6000, 'turn_front': 6000,
          'marker_front': 4000, 'marker_rear': 4000, 'tl_turn': 10000, 'tl_rev': 10000, 'hl_lens_Hi': 10000, 'hl_lens_Lo': 10000}

PARTS = HLs + [
    P('grille', D.grille_slats, (1.98, -0.30, 0.54), (2.06, 0.30, 0.68), 0.0016, 0.6),
    P('badge_plate', D.grille_badge_plate, (2.02, -0.09, 0.58), (2.06, 0.09, 0.64), 0.0012, 0.5),
    P('badge_dmc', D.grille_badge_letters, (2.008, -0.08, 0.59), (2.035, 0.08, 0.63), 0.0006, 0.5, False, 1),
    P('turn_front', D.front_turn_lens, (2.05, 0.49, 0.44), (2.13, 0.68, 0.515), 0.0018, 0.5, True),
    P('marker_front', D.side_marker_front, (1.57, 0.88, 0.555), (1.77, 0.94, 0.595), 0.0015, 0.5, True),
    P('marker_rear', D.side_marker_rear, (-1.83, 0.88, 0.59), (-1.64, 0.95, 0.63), 0.0015, 0.5, True),
    P('tl_turn', lambda X, Y, Z: D.tail_cells(X, Y, Z, 'Turn'), (-1.985, 0.70, 0.635), (-1.94, 0.79, 0.82), 0.0016, 0.5, True),
    P('tl_tail', lambda X, Y, Z: D.tail_cells(X, Y, Z, 'Tail'), (-1.985, 0.36, 0.635), (-1.94, 0.71, 0.82), 0.0018, 0.7, True, 1),
    P('tl_rev', lambda X, Y, Z: D.tail_cells(X, Y, Z, 'Reverse'), (-1.985, 0.29, 0.635), (-1.94, 0.37, 0.82), 0.0016, 0.5, True),
    P('tl_housing', D.tail_housing, (-1.99, -0.80, 0.625), (-1.93, 0.80, 0.825), 0.002, 0.8, False, 1),
    P('lid_frame', D.lid_frame, (-1.94, -0.75, 0.84), (-0.73, 0.75, 1.12), 0.003, 0.8, False, 1),
    P('lid_slats', D.lid_slats, (-1.90, -0.72, 0.84), (-0.75, 0.72, 1.12), 0.0025, 0.85, False, 1),
    P('lid_under', D.lid_under, (-1.92, -0.72, 0.78), (-0.74, 0.72, 1.07), 0.004, 0.95, False, 0),
    P('bpillar_vent', D.bpillar_insert, (-0.86, 0.50, 0.82), (-0.74, 0.82, 1.07), 0.0018, 0.6, True),
    P('mirror_L', lambda X, Y, Z: D.mirror_housing(X, Y, Z, 1), (0.40, 0.76, 0.83), (0.60, 1.01, 1.01), 0.003, 0.7),
    P('mirror_glass_L', lambda X, Y, Z: D.mirror_glass(X, Y, Z, 1), (0.46, 0.85, 0.88), (0.49, 1.00, 0.99), 0.0015, 0.5),
    P('mirror_R', lambda X, Y, Z: D.mirror_housing(X, Y, Z, -1), (0.40, -1.01, 0.83), (0.60, -0.76, 1.01), 0.003, 0.7),
    P('mirror_glass_R', lambda X, Y, Z: D.mirror_glass(X, Y, Z, -1), (0.46, -1.00, 0.88), (0.49, -0.85, 0.99), 0.0015, 0.5),
    P('liner_f', lambda X, Y, Z: D.well_liner(X, Y, Z, True), (0.82, 0.50, 0.22), (1.60, 0.93, 0.70), 0.004, 0.8, True),
    P('liner_r', lambda X, Y, Z: D.well_liner(X, Y, Z, False), (-1.62, 0.50, 0.24), (-0.79, 0.94, 0.77), 0.004, 0.8, True),
    P('underbody', D.underbody, (-2.0, -0.9, 0.19), (2.04, 0.9, 0.29), 0.006, 0.9),
    P('exhaust', D.exhaust, (-2.12, -0.62, 0.22), (-1.66, 0.62, 0.38), 0.003, 0.8),
    P('door_handle_L', lambda X, Y, Z: D.door_handle(X, Y, Z, 1), (-0.62, 0.86, 0.53), (-0.42, 0.95, 0.62), 0.0012, 0.6),
    P('door_handle_R', lambda X, Y, Z: D.door_handle(X, Y, Z, -1), (-0.62, -0.95, 0.53), (-0.42, -0.86, 0.62), 0.0012, 0.6),
    P('bumper_letters', D.bumper_letters, (-2.11, 0.15, 0.48), (-2.07, 0.62, 0.565), 0.0008, 0.6),
]


def build(p):
    t = time.time()
    V, F = extract(p['f'], p['bmin'], p['bmax'], p['h'], verbose=False)
    if len(F) == 0:
        print('EMPTY', p['name'])
        return
    tgt = BUDGET.get(p['name'], 8000)
    V, F, N = finish4(p['f'], V, F, tgt // (2 if p['mirror'] else 1), max(p['refine'], 2), max_angle=10.0, min_len=0.0006)
    if p['mirror']:
        Vm = V * [1, -1, 1]
        Nm = N * [1, -1, 1]
        Fm = F[:, [0, 2, 1]] + len(V)
        V = np.concatenate([V, Vm])
        N = np.concatenate([N, Nm])
        F = np.concatenate([F, Fm])
    np.savez_compressed(f"{OUT}/{p['name']}.npz", V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    print(f"{p['name']}: {len(V)} v {len(F)} f {time.time() - t:.1f}s", flush=True)


if __name__ == '__main__':
    sel = sys.argv[1:]
    for p in PARTS:
        if not sel or any(p['name'].startswith(s) for s in sel):
            build(p)
