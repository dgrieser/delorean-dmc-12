"""PRV ZMJ-159 V6 engine bay and the front luggage compartment (SDF parts).

Engine: longitudinal 90-degree V6 behind the rear axle, transaxle ahead of it.
Blender frame: X fwd, Y left, Z up.
"""
import numpy as np
from sdf import smin, smax, poly2d
import body as B
import shellx as SX
from body import _rbox2
from details import rbox3, cap_x

DEG = np.pi / 180
CRANK_Z = 0.40
EX0, EX1 = -1.86, -1.30          # engine block extent along X


def _bank_frame(X, Y, Z, side):
    """Coordinates in a cylinder-bank frame: a along the bore (tilted 45 deg outward), b lateral, x."""
    c, s = np.cos(45 * DEG), np.sin(45 * DEG)
    yy = Y * side
    a = (Z - CRANK_Z) * c + yy * s
    b = -(Z - CRANK_Z) * s + yy * c
    return a, b


def block(X, Y, Z):
    xc, hx = 0.5 * (EX0 + EX1), 0.5 * (EX1 - EX0)
    crankcase = rbox3(X, Y, Z, (xc, 0, CRANK_Z - 0.04), (hx, 0.19, 0.13), 0.04)
    d = crankcase
    for side in (1, -1):
        a, b = _bank_frame(X, Y, Z, side)
        bank = rbox3(X, b, a, (xc, 0, 0.20), (hx - 0.02, 0.10, 0.12), 0.03)
        d = smin(d, bank, 0.03)
    sump = rbox3(X, Y, Z, (xc + 0.02, 0, 0.255), (hx - 0.04, 0.15, 0.045), 0.03)
    bell = cap_x(X, Y, Z, (EX1, 0, CRANK_Z), (EX1 + 0.06, 0, CRANK_Z), 0.17)
    trans = rbox3(X, Y, Z, (-1.12, 0, 0.36), (0.20, 0.16, 0.10), 0.06)
    return smin(smin(smin(d, sump, 0.02), bell, 0.03), trans, 0.04)


def cam_covers(X, Y, Z):
    xc, hx = 0.5 * (EX0 + EX1), 0.5 * (EX1 - EX0)
    d = np.full(np.shape(X), 1.0)
    for side in (1, -1):
        a, b = _bank_frame(X, Y, Z, side)
        cov = rbox3(X, b, a, (xc, 0, 0.345), (hx - 0.03, 0.085, 0.035), 0.025)
        fins = np.maximum(np.abs(np.mod(X + 0.015, 0.03) - 0.015) - 0.006, np.abs(a - 0.383) - 0.006)
        fins = np.maximum(fins, np.abs(b) - 0.06)
        fins = np.maximum(fins, np.abs(X - xc) - (hx - 0.06))
        d = np.minimum(d, smin(cov, fins, 0.004))
    return d


def intake(X, Y, Z):
    """Cast aluminium plenum in the vee + the two looping runners towards the rear."""
    xc = 0.5 * (EX0 + EX1)
    plen = rbox3(X, Y, Z, (xc + 0.04, 0, 0.62), (0.20, 0.07, 0.05), 0.035)
    d = plen
    for s in (1, -1):
        # U-loop: torus segment in the XZ plane at the rear of the plenum
        cx, cz = xc - 0.18, 0.66
        r = np.sqrt((X - cx) ** 2 + (Z - cz) ** 2)
        tor = np.sqrt((r - 0.075) ** 2 + (Y - s * 0.075) ** 2) - 0.034
        tor = np.maximum(tor, X - cx)
        d = smin(d, tor, 0.02)
        leg = cap_x(X, Y, Z, (cx, s * 0.075, cz - 0.075), (cx + 0.12, s * 0.12, 0.56), 0.033)
        d = smin(d, leg, 0.02)
    throttle = cap_x(X, Y, Z, (xc + 0.24, 0.0, 0.64), (xc + 0.32, 0.0, 0.64), 0.04)
    return smin(d, throttle, 0.015)


def airbox(X, Y, Z):
    """Black air-filter housing on top (carries the DMC decal) + ducting."""
    c = (-1.42, 0.10, 0.72)
    box = rbox3(X, Y, Z, c, (0.20, 0.16, 0.055), 0.03)
    lid = rbox3(X, Y, Z, (c[0], c[1], c[2] + 0.05), (0.19, 0.15, 0.012), 0.012)
    duct = cap_x(X, Y, Z, (c[0] + 0.05, c[1] - 0.14, c[2] - 0.02), (-1.62, -0.05, 0.64), 0.04)
    return smin(smin(box, lid, 0.01), duct, 0.02)


def airbox_decal(X, Y, Z):
    c = (-1.42, 0.10, 0.72 + 0.0625)
    plate = rbox3(X, Y, Z, (c[0] + 0.03, c[1] - 0.02, c[2]), (0.08, 0.10, 0.0015), 0.004)
    return plate


def exhaust_manifolds(X, Y, Z):
    xc, hx = 0.5 * (EX0 + EX1), 0.5 * (EX1 - EX0)
    d = np.full(np.shape(X), 1.0)
    for side in (1, -1):
        a, b = _bank_frame(X, Y, Z, side)
        pipe = rbox3(X, b, a, (xc, 0.12, 0.20), (hx - 0.05, 0.03, 0.04), 0.028)
        d = np.minimum(d, pipe)
        down = cap_x(X, Y, Z, (EX0 + 0.06, side * 0.30, 0.42), (-1.88, side * 0.42, 0.30), 0.03)
        d = np.minimum(d, down)
    return d


def coolant_tank(X, Y, Z):
    r = np.sqrt((Y + 0.47) ** 2 + (Z - 0.66) ** 2)
    tank = np.maximum(r - 0.065, np.abs(X + 1.50) - 0.15) - 0.0
    cap = np.maximum(np.sqrt((X + 1.42) ** 2 + (Y + 0.47) ** 2) - 0.022, np.abs(Z - 0.73) - 0.012)
    return smin(smin(tank, 0.0 * tank + tank, 0.0), cap, 0.006)


def ancillaries(X, Y, Z):
    """AC compressor + alternator + pulleys at the rear (timing end) of the engine."""
    ac = np.maximum(np.sqrt((Y - 0.27) ** 2 + (Z - 0.50) ** 2) - 0.062, np.abs(X + 1.74) - 0.10)
    acp = np.maximum(np.sqrt((Y - 0.27) ** 2 + (Z - 0.50) ** 2) - 0.07, np.abs(X + 1.87) - 0.018)
    alt = np.maximum(np.sqrt((Y + 0.24) ** 2 + (Z - 0.55) ** 2) - 0.065, np.abs(X + 1.78) - 0.07)
    crankp = np.maximum(np.sqrt(Y ** 2 + (Z - CRANK_Z) ** 2) - 0.085, np.abs(X + 1.885) - 0.016)
    return np.minimum(np.minimum(ac, acp), np.minimum(alt, crankp))


def battery(X, Y, Z):
    return rbox3(X, Y, Z, (-0.98, -0.44, 0.47), (0.10, 0.09, 0.09), 0.012)


def hoses(X, Y, Z):
    pts = [
        [(-1.36, -0.47, 0.66), (-1.30, -0.30, 0.62), (-1.31, -0.08, 0.64)],
        [(-1.64, -0.47, 0.64), (-1.75, -0.30, 0.58), (-1.80, -0.12, 0.52)],
        [(-1.25, 0.25, 0.60), (-1.10, 0.35, 0.55), (-0.95, 0.40, 0.48)],
        [(-1.25, -0.25, 0.58), (-1.05, -0.32, 0.52), (-0.90, -0.30, 0.40)],
        [(-1.55, 0.30, 0.62), (-1.62, 0.40, 0.55), (-1.70, 0.36, 0.45)],
    ]
    d = np.full(np.shape(X), 1.0)
    for chain in pts:
        for a, b in zip(chain[:-1], chain[1:]):
            d = smin(d, cap_x(X, Y, Z, a, b, 0.018), 0.015)
    return d


def bay_tub(X, Y, Z):
    """Black engine-bay walls (inner layer of the shell under the cover) and floor."""
    s = SX.shell(X, Y, Z)
    yy = np.abs(Y)
    wall = np.maximum(s + 0.03, -(s + 0.045))
    wall = np.maximum(wall, np.maximum(-1.96 - X, X + 0.80))
    wall = np.maximum(wall, 0.30 - Z)
    wall = np.maximum(wall, Z - 0.86)
    # no ceiling: the louvred cover is the lid
    wall = np.maximum(wall, -(poly2d(X, Y, B.LID_POLY) - 0.06))
    floor = rbox3(X, Y, Z, (-1.40, 0, 0.215), (0.56, 0.70, 0.01), 0.01)
    floor = smax(floor, -B.arch_cyl(X, Y, Z, 0.03), 0.01)
    # inner fender walls between the bay and the rear wheel wells
    fw = np.maximum(np.abs(yy - 0.56) - 0.008, np.maximum(np.maximum(-1.64 - X, X + 0.78), np.maximum(0.22 - Z, Z - 0.80)))
    return np.minimum(np.minimum(wall, floor), fw)


def firewall_panel(X, Y, Z):
    """Black panel with the 'JUMP LEAD STARTING' decal on the cabin bulkhead (engine side)."""
    return rbox3(X, Y, Z, (-0.83, -0.30, 0.66), (0.006, 0.12, 0.08), 0.004)


# ======================================================================================
# Front luggage compartment
def frunk_tub(X, Y, Z):
    s = SX.shell(X, Y, Z)
    yy = np.abs(Y)
    wall = np.maximum(s + 0.03, -(s + 0.045))
    wall = np.maximum(wall, np.maximum(0.86 - X, X - 2.02))
    wall = np.maximum(wall, 0.40 - Z)
    wall = np.maximum(wall, Z - 0.80)
    wall = np.maximum(wall, -(poly2d(X, Y, B.HOOD_POLY) - 0.05))
    # floor and side walls stay inboard of the wheel-well liners (inner wall at |y| 0.53)
    floor = rbox3(X, Y, Z, (1.45, 0, 0.40), (0.58, 0.52, 0.012), 0.01)
    floor = smax(floor, -B.arch_cyl(X, Y, Z, 0.03), 0.01)
    rear = rbox3(X, Y, Z, (0.90, 0, 0.60), (0.012, 0.70, 0.20), 0.01)
    side = np.maximum(np.abs(yy - 0.515) - 0.01, np.maximum(np.maximum(0.88 - X, X - 1.62), np.maximum(0.39 - Z, Z - 0.78)))
    return np.minimum(np.minimum(wall, floor), np.minimum(rear, side))


def fuel_tank(X, Y, Z):
    t = rbox3(X, Y, Z, (1.08, 0.0, 0.49), (0.18, 0.50, 0.08), 0.05)
    neck = cap_x(X, Y, Z, (1.02, 0.185, 0.56), (0.955, 0.185, 0.80), 0.032)
    cap = np.maximum(np.sqrt((X - 0.955) ** 2 + (Y - 0.185) ** 2) - 0.042, np.abs(Z - 0.815) - 0.014)
    return smin(smin(t, neck, 0.02), cap, 0.005)


def spare_wheel(X, Y, Z):
    # space-saver lying flat at the front of the compartment
    r = np.sqrt((X - 1.70) ** 2 + Y ** 2)
    tyre = np.sqrt((r - 0.24) ** 2 + ((Z - 0.47) * 1.25) ** 2) - 0.065
    rim = np.maximum(r - 0.19, np.abs(Z - 0.47) - 0.05)
    rim = smax(rim, -np.maximum(r - 0.16, np.abs(Z - 0.52) - 0.03), 0.01)
    return smin(tyre, rim, 0.01)


def spare_rim(X, Y, Z):
    r = np.sqrt((X - 1.70) ** 2 + Y ** 2)
    rim = np.maximum(r - 0.188, np.abs(Z - 0.47) - 0.048)
    return smax(rim, -np.maximum(r - 0.16, np.abs(Z - 0.53) - 0.03), 0.01)


def spare_tyre(X, Y, Z):
    r = np.sqrt((X - 1.70) ** 2 + Y ** 2)
    return np.sqrt((r - 0.245) ** 2 + ((Z - 0.47) * 1.25) ** 2) - 0.068


def extinguisher(X, Y, Z):
    body = cap_x(X, Y, Z, (1.30, -0.45, 0.46), (1.30, -0.12, 0.46), 0.042)
    return body
