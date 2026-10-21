"""Extract cabin parts to NPZ (world-frame parts and local-frame moving parts)."""
import os, sys, time
import numpy as np
from extract import extract, finish4
import interior as I
import body as B

OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
H = float(os.environ.get('HI', '0.004'))


def P(name, f, bmin, bmax, h, target, mirror=False):
    return dict(name=name, f=f, bmin=bmin, bmax=bmax, h=h, target=target, mirror=mirror)


# light, broad trim panels: split the decimator's long slivers so baked AO can't streak across them
SPLIT = ('door_card', 'door_liner', 'body_trim')


SY = I.SEAT_Y
PARTS = [
    P('seat_L', lambda X, Y, Z: I.seat(X, Y, Z, 1), (-0.80, SY - 0.30, 0.20), (0.15, SY + 0.30, 1.12), 0.004, 60000),
    P('seat_R', lambda X, Y, Z: I.seat(X, Y, Z, -1), (-0.80, -SY - 0.30, 0.20), (0.15, -SY + 0.30, 1.12), 0.004, 60000),
    P('seatbase_L', lambda X, Y, Z: I.seat_base(X, Y, Z, 1), (-0.50, SY - 0.30, 0.22), (0.20, SY + 0.30, 0.33), 0.003, 6000),
    P('seatbase_R', lambda X, Y, Z: I.seat_base(X, Y, Z, -1), (-0.50, -SY - 0.30, 0.22), (0.20, -SY + 0.30, 0.33), 0.003, 6000),
    P('dash', I.dashboard, (0.25, -0.84, 0.36), (1.05, 0.84, 0.92), 0.004, 90000),
    P('stack', I.center_stack, (0.38, -0.15, 0.40), (0.86, 0.15, 0.84), 0.0025, 20000),
    P('stack_inserts', I.stack_inserts, (0.44, -0.12, 0.49), (0.62, 0.12, 0.78), 0.0015, 16000),
    P('end_vents', I.end_vents, (0.44, -0.80, 0.64), (0.58, 0.80, 0.76), 0.0015, 8000),
    P('console', I.console, (-0.52, -0.18, 0.22), (0.52, 0.18, 0.56), 0.003, 30000),
    P('console_inserts', I.console_inserts, (-0.03, -0.10, 0.42), (0.10, 0.10, 0.46), 0.0012, 6000),
    P('column', I.column, (0.10, 0.12, 0.42), (0.58, 0.62, 0.70), 0.0025, 12000),
    P('door_card_L', lambda X, Y, Z: I.door_trim(X, Y, Z, 1, False), (-0.78, 0.55, 0.33), (0.70, 0.95, 0.90), 0.004, 50000),
    P('door_card_R', lambda X, Y, Z: I.door_trim(X, Y, Z, -1, False), (-0.78, -0.95, 0.33), (0.70, -0.55, 0.90), 0.004, 50000),
    P('door_liner_L', lambda X, Y, Z: I.door_trim(X, Y, Z, 1, True), (-0.78, 0.08, 0.85), (0.70, 0.90, 1.15), 0.004, 30000),
    P('door_liner_R', lambda X, Y, Z: I.door_trim(X, Y, Z, -1, True), (-0.78, -0.90, 0.85), (0.70, -0.08, 1.15), 0.004, 30000),
    P('body_trim', I.body_trim, (-0.80, -0.90, 0.60), (0.88, 0.90, 1.15), 0.004, 40000),
    P('carpet', I.carpet, (-0.79, -0.82, 0.22), (0.97, 0.82, 0.57), 0.005, 30000),
    P('sills', I.sill, (-0.62, -0.86, 0.24), (0.62, 0.86, 0.35), 0.004, 8000),
    P('sill_plates', I.sill_plate, (-0.46, -0.85, 0.335), (0.50, 0.85, 0.35), 0.0012, 20000),
    P('parcel', I.parcel_shelf, (-0.79, -0.80, 0.64), (-0.65, 0.80, 0.68), 0.004, 3000),
    P('rear_window', I.rear_window, (-0.79, -0.65, 0.67), (-0.78, 0.65, 1.08), 0.002, 2000),
    P('bulkhead', I.bulkhead_upper, (-0.81, -0.85, 0.64), (-0.77, 0.85, 1.12), 0.004, 8000),
    P('rear_mirror', I.rear_mirror, (-0.10, -0.14, 0.98), (0.02, 0.14, 1.12), 0.0015, 4000),
    P('buckles', I.seatbelt_buckles, (-0.37, -0.18, 0.35), (-0.27, 0.18, 0.45), 0.0015, 3000),
    P('belt_buttons', I.belt_buttons, (-0.34, -0.17, 0.43), (-0.30, 0.17, 0.45), 0.001, 1000),
    P('door_strap_L', lambda X, Y, Z: I.door_strap(X, Y, Z, 1), (0.02, 0.70, 0.69), (0.08, 0.90, 0.90), 0.0012, 1500),
    P('door_strap_R', lambda X, Y, Z: I.door_strap(X, Y, Z, -1), (0.02, -0.90, 0.69), (0.08, -0.70, 0.90), 0.0012, 1500),
    P('courtesy_L', lambda X, Y, Z: I.courtesy_lamp(X, Y, Z, 1), (0.40, 0.81, 0.27), (0.48, 0.87, 0.35), 0.0010, 1500),
    P('courtesy_R', lambda X, Y, Z: I.courtesy_lamp(X, Y, Z, -1), (0.40, -0.87, 0.27), (0.48, -0.81, 0.35), 0.0010, 1500),
    # local-frame moving parts
    P('steering_wheel', I.steering_wheel_local, (-0.22, -0.22, -0.11), (0.22, 0.22, 0.04), 0.0015, 30000),
    P('pedal_Clutch', lambda x, y, z: I.pedal_local(x, y, z, 'Clutch'), (-0.07, -0.06, -0.34), (0.02, 0.06, 0.02), 0.0015, 4000),
    P('pedal_Brake', lambda x, y, z: I.pedal_local(x, y, z, 'Brake'), (-0.07, -0.06, -0.34), (0.02, 0.06, 0.02), 0.0015, 4000),
    P('pedal_Gas', lambda x, y, z: I.pedal_local(x, y, z, 'Gas'), (-0.06, -0.05, -0.36), (0.02, 0.05, 0.02), 0.0015, 4000),
    P('shifter_lever', I.shifter_lever_local, (-0.02, -0.02, -0.01), (0.02, 0.02, 0.18), 0.001, 1500),
    P('shifter_knob', I.shifter_knob_local, (-0.03, -0.03, 0.16), (0.03, 0.03, 0.21), 0.001, 3000),
    P('shift_boot', I.shift_boot_local, (-0.07, -0.07, -0.01), (0.07, 0.07, 0.13), 0.0015, 5000),
    P('handbrake', I.handbrake_local, (-0.03, -0.03, -0.03), (0.28, 0.03, 0.03), 0.0012, 3000),
]


def build(p):
    t = time.time()
    V, F = extract(p['f'], p['bmin'], p['bmax'], p['h'], verbose=False)
    if len(F) == 0:
        print('EMPTY', p['name'], flush=True)
        return
    V, F, N = finish4(p['f'], V, F, p['target'], 2, max_angle=10.0, min_len=0.0006, max_edge=0.05 if p['name'].startswith(SPLIT) else None)
    np.savez_compressed(f"{OUT}/{p['name']}.npz", V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    print(f"{p['name']}: {len(V)} v {len(F)} f {time.time() - t:.1f}s", flush=True)


if __name__ == '__main__':
    sel = sys.argv[1:]
    for p in PARTS:
        if not sel or any(p['name'].startswith(s) for s in sel):
            build(p)
