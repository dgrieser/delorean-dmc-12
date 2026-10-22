"""Extract all exterior detail parts to NPZ."""
import os, sys, time
import numpy as np
from extract import extract, finish4
import body as B
import details as D

OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
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
    bb = ((1.86, yc - hw - 0.012, B.HL_Z[0] - 0.012), (2.00, yc + hw + 0.012, B.HL_Z[1] + 0.012))   # the outer bowls reach back to 1.89
    bbz = ((1.86, yc - hw - 0.012, B.HL_Z[0] - 0.012), (2.05, yc + hw + 0.012 + (0.07 if i else 0), B.HL_Z[1] + 0.012))
    HLs += [
        P(f'hl_lens_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_lens(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0018, 0.5, True),
        P(f'hl_refl_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_reflector(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0018, 0.5, True),
        P(f'hl_bulb_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_bulb(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0015, 0.3, True),
        P(f'hl_bezel_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_bezel(X, Y, Z, yc, hw))(yc, hw), *bbz, 0.0018, 0.6, True),
        P(f'hl_rim_{tag}', (lambda yc, hw: lambda X, Y, Z: D.headlight_rim(X, Y, Z, yc, hw))(yc, hw), *bb, 0.0012, 0.5, True),
    ]

BUDGET = {'badge_dmc': 6000, 'antenna': 3000, 'turn_bezel': 4000, 'turn_refl': 4000, 'intake_mesh': 2000, 'radiator': 2000, 'rear_frame': 8000, 'driveshafts': 4000, 'plate': 1500, 'cowl_vent': 30000, 'antenna_base': 1500, 'hl_rim_Hi': 6000, 'hl_rim_Lo': 6000, 'hl_bulb_Hi': 1200, 'hl_bulb_Lo': 1200, 'door_handle_L': 2000, 'door_handle_R': 2000,
          'bumper_letters': 9000, 'grille': 30000, 'lid_slats': 26000, 'underbody': 12000, 'liner_f': 14000, 'liner_r': 14000,
          'tl_housing': 22000, 'lid_frame': 16000, 'hl_bezel_Hi': 10000, 'hl_bezel_Lo': 10000, 'exhaust': 9000,
          'hl_refl_Hi': 12000, 'hl_refl_Lo': 12000, 'tl_tail': 26000, 'mirror_L': 14000, 'mirror_R': 14000,
          'mirror_glass_L': 2000, 'mirror_glass_R': 2000, 'bpillar_vent': 6000, 'turn_front': 6000,
          'marker_front': 4000, 'marker_rear': 4000, 'tl_turn': 10000, 'tl_rev': 10000, 'hl_lens_Hi': 10000, 'hl_lens_Lo': 10000}

PARTS = HLs + [
    P('grille', D.grille_slats, (1.90, -0.36, 0.54), (2.01, 0.36, 0.675), 0.0016, 0.6),
    P('badge_dmc', D.grille_badge_letters, (1.94, -0.09, 0.57), (1.99, 0.09, 0.62), 0.0006, 0.5, False, 1),
    P('turn_housing', D.front_turn_housing, (1.98, 0.39, 0.42), (2.12, 0.63, 0.53), 0.0016, 0.6, True),
    P('turn_bezel', D.front_turn_bezel, (2.0, 0.42, 0.44), (2.11, 0.60, 0.51), 0.0012, 0.6, True),
    P('turn_refl', D.front_turn_reflector, (2.0, 0.43, 0.445), (2.10, 0.59, 0.505), 0.0012, 0.5, True),
    P('turn_front', D.front_turn_lens, (2.0, 0.43, 0.445), (2.11, 0.59, 0.505), 0.0014, 0.5, True),
    P('intake_mesh', D.intake_mesh, (1.80, -0.52, 0.26), (1.92, 0.52, 0.39), 0.0015, 0.5),
    P('radiator', D.radiator, (1.72, -0.55, 0.20), (1.84, 0.55, 0.42), 0.003, 0.5),
    P('intake_supports', D.intake_supports, (1.74, -0.37, 0.25), (1.85, 0.37, 0.37), 0.002, 0.6),
    P('marker_front', D.side_marker_front, (1.57, 0.80, 0.51), (1.80, 0.93, 0.57), 0.0015, 0.5, True),
    P('marker_rear', D.side_marker_rear, (-1.89, 0.79, 0.55), (-1.66, 0.92, 0.61), 0.0015, 0.5, True),
    P('tl_turn', lambda X, Y, Z: D.tail_cells(X, Y, Z, 'Turn'), (-2.04, 0.60, 0.65), (-1.90, 0.75, 0.81), 0.0016, 0.5, True),
    P('tl_tail', lambda X, Y, Z: D.tail_cells(X, Y, Z, 'Tail'), (-2.04, 0.33, 0.65), (-1.90, 0.62, 0.81), 0.0018, 0.7, True, 1),
    P('tl_rev', lambda X, Y, Z: D.tail_cells(X, Y, Z, 'Reverse'), (-2.04, 0.27, 0.65), (-1.90, 0.35, 0.81), 0.0016, 0.5, True),
    P('plate', D.licence_plate, (-2.05, -0.17, 0.66), (-1.90, 0.17, 0.83), 0.0012, 0.5),
    P('tl_housing', D.tail_housing, (-2.04, -0.76, 0.64), (-1.90, 0.76, 0.815), 0.002, 0.8, False, 1),
    P('lid_frame', D.lid_frame, (-1.94, -0.62, 0.76), (-0.89, 0.62, 1.15), 0.003, 0.8, False, 1),
    P('lid_slats', D.lid_slats, (-1.93, -0.60, 0.82), (-0.90, 0.60, 1.15), 0.002, 0.85, False, 1),
    P('lid_under', D.lid_under, (-1.93, -0.60, 0.76), (-0.90, 0.60, 1.10), 0.004, 0.95, False, 0),
    P('bpillar_vent', D.bpillar_insert, (-0.94, 0.48, 0.80), (-0.76, 0.86, 1.09), 0.0018, 0.6, True),
    P('mirror_L', lambda X, Y, Z: D.mirror_housing(X, Y, Z, 1), (0.22, 0.73, 0.74), (0.50, 1.01, 0.91), 0.0025, 0.7),
    P('mirror_glass_L', lambda X, Y, Z: D.mirror_glass(X, Y, Z, 1), (0.22, 0.76, 0.75), (0.45, 1.00, 0.89), 0.0015, 0.5),
    P('mirror_R', lambda X, Y, Z: D.mirror_housing(X, Y, Z, -1), (0.22, -1.01, 0.74), (0.50, -0.73, 0.91), 0.0025, 0.7),
    P('mirror_glass_R', lambda X, Y, Z: D.mirror_glass(X, Y, Z, -1), (0.22, -1.00, 0.75), (0.45, -0.76, 0.89), 0.0015, 0.5),
    P('liner_f', lambda X, Y, Z: D.well_liner(X, Y, Z, True), (0.82, 0.50, 0.22), (1.60, 0.93, 0.70), 0.004, 0.8, True),
    P('liner_r', lambda X, Y, Z: D.well_liner(X, Y, Z, False), (-1.62, 0.50, 0.24), (-0.79, 0.94, 0.77), 0.004, 0.8, True),
    P('rear_frame', D.rear_frame, (-1.95, -0.80, 0.17), (-0.55, 0.80, 0.46), 0.004, 0.8),
    P('driveshafts', D.driveshafts, (-1.30, -0.70, 0.27), (-1.11, 0.70, 0.42), 0.003, 0.7),
    P('underbody', D.underbody, (-2.0, -0.9, 0.19), (2.04, 0.9, 0.29), 0.006, 0.9),
    P('cowl_vent', D.cowl_vent, (0.60, -0.74, 0.80), (0.80, 0.74, 0.92), 0.0016, 0.6),
    P('antenna', D.antenna_mast, (0.64, -0.87, 0.78), (0.78, -0.78, 1.61), 0.0007, 0.6, False, 1),
    P('antenna_base', D.antenna_base, (0.74, -0.82, 0.77), (0.79, -0.77, 0.83), 0.0008, 0.6),
    P('exhaust', D.exhaust, (-2.14, -0.42, 0.34), (-1.89, 0.42, 0.57), 0.002, 0.8),
    P('rear_fasteners', D.rear_fasteners, (-2.10, -0.72, 0.31), (-1.78, 0.72, 0.82), 0.0015, 0.6),
    P('plate_lights', D.plate_lights, (-2.07, -0.18, 0.80), (-1.90, 0.18, 0.86), 0.002, 0.6),
    P('rear_slot_back', D.rear_slot_back, (-2.08, -0.36, 0.415), (-1.97, 0.36, 0.435), 0.0015, 0.6),
    P('sill_details', D.sill_details, (-0.80, 0.78, 0.16), (0.70, 0.92, 0.23), 0.0015, 0.6, True),
    P('door_handle_L', lambda X, Y, Z: D.door_handle(X, Y, Z, 1), (-0.62, 0.86, 0.49), (-0.42, 0.95, 0.57), 0.0012, 0.6),
    P('door_handle_R', lambda X, Y, Z: D.door_handle(X, Y, Z, -1), (-0.62, -0.95, 0.49), (-0.42, -0.86, 0.57), 0.0012, 0.6),
    P('bumper_letters', D.bumper_letters, (-2.11, 0.24, 0.48), (-2.04, 0.76, 0.555), 0.0008, 0.6),
]


def build(p):
    t = time.time()
    V, F = extract(p['f'], p['bmin'], p['bmax'], p['h'], verbose=False)
    if len(F) == 0:
        print('EMPTY', p['name'])
        return
    tgt = BUDGET.get(p['name'], 8000)
    V, F, N = finish4(p['f'], V, F, tgt // (2 if p['mirror'] else 1), max(p['refine'], 2), max_angle=10.0, min_len=0.0006,
                      max_edge=0.05 if p['name'] in ('lid_frame', 'lid_slats') else None)
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
