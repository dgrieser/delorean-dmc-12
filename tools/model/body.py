"""DMC-12 outer body SDF and panel regions.

Frame: X forward, Y left, Z up, metres. Ground z=0, X=0 at mid wheelbase.
Published figures used: length 4216 mm (166 in), wheelbase 2413 mm (95 in),
height 1140 mm, width 1857 mm, track 1590/1588 mm, ground clearance 142/155 mm,
tyres 195/60 HR14 front, 235/60 HR15 rear.
"""
import numpy as np
from sdf import smin, smax, interp, cubic_interp, cyl_y, poly2d, box

DEG = np.pi / 180
X_FA, X_RA = 1.2065, -1.2065
R_F, R_R = 0.292, 0.322          # loaded wheel-centre heights
ARCH_F, ARCH_R = 0.372, 0.390
TRACK_F, TRACK_R = 1.590, 1.588


# ---- longitudinal control functions -------------------------------------------------
def z_crease(X):
    return interp(X, [-2.2, -1.2, 0.0, 1.2, 2.2], [0.640, 0.636, 0.626, 0.612, 0.598])


def w_crease(X):
    return interp(X, [-2.2, -1.6, -1.2, 0.0, 1.2, 2.2], [0.921, 0.926, 0.928, 0.921, 0.914, 0.906])


LEAN_UP = 21 * DEG
TUCK = 9 * DEG

_TOP_X = [-2.10, -1.95, -1.5, -1.0, -0.75, 0.0, 0.5, 0.80, 1.2, 1.6, 2.06, 2.2]
_TOP_Z = [0.874, 0.878, 0.880, 0.872, 0.858, 0.850, 0.850, 0.838, 0.790, 0.745, 0.697, 0.685]


def z_top_c(X):
    return cubic_interp(X, _TOP_X, _TOP_Z)


def crown(X, yy):
    k = interp(X, [-2.2, 0.45, 0.75, 2.2], [0.010, 0.010, 0.026, 0.026])
    return k * (yy / 0.85) ** 2


def x_nose(Z):
    return 2.040 - (Z - 0.55) * 0.20


def x_tail(Z):
    return -1.955 - (0.875 - Z) * 0.06


# ---- lower body ------------------------------------------------------------------------
def lower_body(X, Y, Z):
    yy = np.abs(Y)
    zc = z_crease(X)
    wc = w_crease(X)
    d_su = (yy - wc) * np.cos(LEAN_UP) + (Z - zc) * np.sin(LEAN_UP)
    d_sl = (yy - wc) * np.cos(TUCK) - (Z - zc) * np.sin(TUCK)
    side = smax(d_su, d_sl, 0.005)
    d_top = (Z - (z_top_c(X) - crown(X, yy))) * 0.994
    d_bot = 0.272 - Z
    d_nose = (X - x_nose(Z)) * 0.98
    d_fc = (X - 2.030) * 0.740 + (yy - 0.745) * 0.673
    d_tail = (x_tail(Z) - X) * 0.998
    d_rc = (X + 1.950) * (-0.672) + (yy - 0.790) * 0.741
    d = smax(side, d_top, 0.009)
    d = smax(d, d_nose, 0.008)
    d = smax(d, d_fc, 0.030)
    d = smax(d, d_tail, 0.010)
    d = smax(d, d_rc, 0.035)
    d = smax(d, d_bot, 0.015)
    return d


# ---- greenhouse ------------------------------------------------------------------------
WS_B = np.array([0.815, 0.848])
WS_T = np.array([0.300, 1.118])
_ws_dir = WS_T - WS_B
WS_N = np.array([_ws_dir[1], -_ws_dir[0]])
if WS_N[1] < 0:
    WS_N = -WS_N
WS_N = WS_N / np.linalg.norm(WS_N)          # (+x, +z) outward
WS_WRAP = 0.22
GS_Y0, GS_Z0 = 0.805, 0.850
GS_LEAN = 50 * DEG
FB_R1 = np.array([-0.64, 1.118])
FB_R2 = np.array([-1.935, 0.885])
_fb_dir = FB_R2 - FB_R1
FB_N = np.array([_fb_dir[1], -_fb_dir[0]])
if FB_N[1] < 0:
    FB_N = -FB_N
FB_N = FB_N / np.linalg.norm(FB_N)
ROOF_Z, ROOF_K = 1.132, 0.11


def d_windshield(X, yy, Z):
    Xe = X + WS_WRAP * yy ** 2
    return (Xe - WS_B[0]) * WS_N[0] + (Z - WS_B[1]) * WS_N[1]


def d_roof(X, yy, Z):
    return Z - (ROOF_Z - ROOF_K * yy ** 2)


def d_glass_side(X, yy, Z):
    return (yy - GS_Y0) * np.cos(GS_LEAN) + (Z - GS_Z0) * np.sin(GS_LEAN)


def d_fastback(X, yy, Z):
    return (X - FB_R1[0]) * FB_N[0] + (Z - FB_R1[1]) * FB_N[1]


def greenhouse(X, Y, Z):
    yy = np.abs(Y)
    ws = d_windshield(X, yy, Z)
    rf = d_roof(X, yy, Z)
    gs = d_glass_side(X, yy, Z)
    fb = d_fastback(X, yy, Z)
    d = smax(rf, ws, 0.05)
    d = smax(d, fb, 0.030)
    d = smax(d, gs, 0.020)
    d = smax(d, 0.80 - Z, 0.01)
    d = smax(d, (x_tail(Z) - X), 0.010)
    d = smax(d, (X + 1.950) * (-0.672) + (yy - 0.790) * 0.741, 0.02)
    return d


def pillar_x(Z):
    """X of the A-pillar edge (windshield ∩ side glass) at height Z, and its half-width."""
    yy = GS_Y0 - (Z - GS_Z0) * np.tan(GS_LEAN)
    Xe = WS_B[0] - (Z - WS_B[1]) * WS_N[1] / WS_N[0]
    return Xe - WS_WRAP * yy ** 2, yy


def cpillar_edge(X):
    """(yy, z) of the fastback ∩ side-glass edge at X."""
    z = FB_R1[1] + (X - FB_R1[0]) * (-FB_N[0] / FB_N[1])
    yy = GS_Y0 - (z - GS_Z0) * np.tan(GS_LEAN)
    return yy, z


# ---- arches ------------------------------------------------------------------------------
def arch_cyl(X, Y, Z, grow=0.0):
    a = np.minimum(cyl_y(X, Y, Z, X_FA, R_F, ARCH_F + grow), cyl_y(X, Y, Z, X_RA, R_R, ARCH_R + grow))
    return np.maximum(a, 0.55 - np.abs(Y))


# ---- recessed features in the shell -----------------------------------------------------
HL_Z = (0.548, 0.668)
HL_Y = [(0.300, 0.470), (0.485, 0.655)]
GRILLE_Y = 0.285
TL_Z = (0.632, 0.818)
TL_Y = 0.795


def _rbox2(u, v, hu, hv, r):
    qu = np.abs(u) - hu + r
    qv = np.abs(v) - hv + r
    return np.sqrt(np.maximum(qu, 0) ** 2 + np.maximum(qv, 0) ** 2) + np.minimum(np.maximum(qu, qv), 0) - r


def nose_recesses(X, Y, Z):
    """Pockets for headlights and grille in the nose panel (negative inside the pocket)."""
    yy = np.abs(Y)
    zc = 0.5 * (HL_Z[0] + HL_Z[1])
    hz = 0.5 * (HL_Z[1] - HL_Z[0])
    d = np.full(np.shape(X), 1.0)
    for a, b in HL_Y:
        d = np.minimum(d, _rbox2(yy - 0.5 * (a + b), Z - zc, 0.5 * (b - a), hz, 0.006))
    d = np.minimum(d, _rbox2(Y, Z - zc, GRILLE_Y, hz, 0.006))
    depth = X - (x_nose(Z) - 0.035)
    return np.maximum(d, -depth)


def tail_recess(X, Y, Z):
    zc = 0.5 * (TL_Z[0] + TL_Z[1])
    hz = 0.5 * (TL_Z[1] - TL_Z[0])
    r = _rbox2(Y, Z - zc, TL_Y, hz, 0.02)
    depth = (x_tail(Z) + 0.03) - X
    return np.maximum(r, -depth)


def bpillar_vents(X, Y, Z):
    """Vertical intake slot behind each door on the rear-quarter sail."""
    yy = np.abs(Y)
    u = X + 0.800 + (Z - 0.94) * 0.12
    slot = _rbox2(u, Z - 0.945, 0.017, 0.100, 0.014)
    depth = d_glass_side(X, yy, Z) + 0.03
    return np.maximum(slot, -depth)


def shell(X, Y, Z):
    d = smin(lower_body(X, Y, Z), greenhouse(X, Y, Z), 0.010)
    d = smax(d, -arch_cyl(X, Y, Z), 0.006)
    d = smax(d, -nose_recesses(X, Y, Z), 0.004)
    d = smax(d, -tail_recess(X, Y, Z), 0.005)
    d = smax(d, -bpillar_vents(X, Y, Z), 0.004)
    return d


BODY_BMIN = (-2.00, -0.95, 0.24)
BODY_BMAX = (2.08, 0.95, 1.16)


# ---- panel regions (negative inside) ----------------------------------------------------
def _door_poly():
    pts = [(0.475, 0.24), (0.652, 0.845)]
    for z in [0.90, 0.96, 1.02, 1.07]:
        x, _ = pillar_x(z)
        pts.append((float(x) - 0.028, z))
    pts += [(0.272, 1.105), (0.272, 1.25), (-0.700, 1.25), (-0.702, 1.06),
            (-0.735, 0.93), (-0.732, 0.80), (-0.705, 0.70), (-0.668, 0.625), (-0.400, 0.24)]
    return np.array(pts)


DOOR_POLY = _door_poly()
SPINE_Y = 0.118


def r_door(X, Y, Z, side=1):
    d = poly2d(X, Z, DOOR_POLY)
    return np.maximum(d, SPINE_Y - side * Y)


def _hood_poly():
    ys = np.linspace(-0.795, 0.795, 21)
    rear = [(0.80 - WS_WRAP * y * y - 0.005, y) for y in ys]
    return np.array([(2.026, -0.846), (2.026, 0.846)] + rear[::-1])


HOOD_POLY = _hood_poly()


def r_hood(X, Y, Z):
    d = poly2d(X, Y, HOOD_POLY)
    return np.maximum(d, 0.62 - Z)


FUEL_FLAP = (0.875, 1.035, 0.105, 0.265)


def r_fuel(X, Y, Z):
    x0, x1, y0, y1 = FUEL_FLAP
    r = _rbox2(X - 0.5 * (x0 + x1), Y - 0.5 * (y0 + y1), 0.5 * (x1 - x0), 0.5 * (y1 - y0), 0.012)
    return np.maximum(r, 0.62 - Z)


def _lid_poly():
    xs = np.linspace(-0.748, -1.925, 12)
    side = [(x, float(cpillar_edge(x)[0]) - 0.045) for x in xs]
    return np.array(side + [(x, -y) for x, y in side[::-1]])


LID_POLY = _lid_poly()


def r_lid(X, Y, Z):
    d = poly2d(X, Y, LID_POLY)
    return np.maximum(d, 0.82 - Z)


def r_windshield(X, Y, Z):
    """Windshield glass opening: inset from pillar/roof/cowl edges."""
    yy = np.abs(Y)
    ws = d_windshield(X, yy, Z)
    m = np.maximum(d_roof(X, yy, Z) + 0.03, d_glass_side(X, yy, Z) + 0.035)
    m = np.maximum(m, 0.872 - Z)
    return np.maximum(m, -ws - 0.05)


def _door_glass_poly():
    pts = []
    for z in [0.875, 0.93, 0.99, 1.04]:
        x, _ = pillar_x(z)
        pts.append((float(x) - 0.075, z))
    pts += [(0.22, 1.058), (-0.50, 1.062), (-0.585, 1.045), (-0.625, 0.99), (-0.628, 0.90), (-0.60, 0.875)]
    return np.array(pts)


DOOR_GLASS_POLY = _door_glass_poly()


def r_door_glass(X, Y, Z, side=1):
    d = poly2d(X, Z, DOOR_GLASS_POLY)
    return np.maximum(d, np.maximum(0.3 - side * Y, 0.82 - Z))


def _quarter_poly():
    xs = np.linspace(-0.905, -1.70, 9)
    top = [(x, float(cpillar_edge(x)[1]) - 0.032) for x in xs]
    return np.array(top + [(-1.73, 0.888), (-1.60, 0.872), (-0.90, 0.872)])


QUARTER_POLY = _quarter_poly()


def r_quarter(X, Y, Z):
    d = poly2d(X, Z, QUARTER_POLY)
    return np.maximum(d, 0.5 - np.abs(Y))


# ---- bumpers (grey urethane) -------------------------------------------------------------
def front_bumper(X, Y, Z):
    yy = np.abs(Y)
    wc = w_crease(X)
    zc = z_crease(X)
    xb = 2.117 - 0.055 * (yy / 0.8) ** 2 - np.maximum(0.0, 0.37 - Z) ** 2 * 3.0
    d_front = X - xb
    d_side = (yy - (wc + 0.010)) * np.cos(TUCK) - np.minimum(Z - zc, 0) * np.sin(TUCK)
    t = np.clip((yy - 0.66) / 0.24, 0, 1)
    ztop = 0.536 + (zc + 0.002 - 0.536) * (t * t * (3 - 2 * t))
    d_top = Z - ztop
    d_back = 1.50 - X
    zb = 0.335 - 0.10 * np.clip((yy - 0.62) / 0.28, 0, 1)
    d_bot = zb - Z
    d = smax(d_front, d_side, 0.13)
    d = smax(d, d_top, 0.010)
    d = smax(d, d_bot, 0.02)
    d = smax(d, d_back, 0.0)
    d = smax(d, -np.maximum(cyl_y(X, Y, Z, X_FA, R_F, ARCH_F), 0.55 - yy), 0.006)
    # turn-signal pockets
    ts = _rbox2(yy - 0.585, Z - 0.455, 0.085, 0.028, 0.004)
    pocket = np.maximum(ts, -(X - (xb - 0.012)))
    d = smax(d, -pocket, 0.003)
    return d


def rear_bumper(X, Y, Z):
    yy = np.abs(Y)
    wc = w_crease(X)
    zc = z_crease(X)
    xb = -2.097 + 0.05 * (yy / 0.85) ** 2 + np.maximum(0.0, 0.395 - Z) * 0.30
    d_rear = xb - X
    d_side = (yy - (wc + 0.010)) * np.cos(TUCK) - np.minimum(Z - zc, 0) * np.sin(TUCK)
    t = np.clip((yy - 0.70) / 0.2, 0, 1)
    ztop = 0.578 + (zc + 0.002 - 0.578) * (t * t * (3 - 2 * t))
    d_top = Z - ztop
    d_front = X + 1.565
    d_bot = 0.245 - Z
    d = smax(d_rear, d_side, 0.11)
    d = smax(d, d_top, 0.010)
    d = smax(d, d_bot, 0.015)
    d = smax(d, d_front, 0.0)
    d = smax(d, -np.maximum(cyl_y(X, Y, Z, X_RA, R_R, ARCH_R), 0.55 - yy), 0.006)
    # slot row in the lower valance
    u = np.mod(Y + 0.032, 0.064) - 0.032
    slots = np.maximum(_rbox2(u, Z - 0.375, 0.022, 0.006, 0.003), yy - 0.28)
    d = smax(d, -np.maximum(slots, -(xb + 0.01 - X)), 0.002)
    return d


FBUMP_BMIN = (1.45, -0.96, 0.15)
FBUMP_BMAX = (2.14, 0.96, 0.64)
RBUMP_BMIN = (-2.12, -0.97, 0.22)
RBUMP_BMAX = (-1.50, 0.97, 0.67)


def rocker(X, Y, Z):
    """Black sill cover under the doors, between the arches."""
    yy = np.abs(Y)
    zc = z_crease(X)
    wc = w_crease(X)
    w = wc - (zc - Z) * np.tan(TUCK) - 0.004
    d = np.maximum(yy - w, 0.62 - yy)
    d = smax(d, np.maximum(Z - 0.285, 0.205 - Z), 0.008)
    d = smax(d, np.maximum(X - 0.84, -1.59 - X), 0.0)
    d = smax(d, -arch_cyl(X, Y, Z, 0.0), 0.004)
    return d


ROCKER_BMIN = (-1.62, -0.95, 0.19)
ROCKER_BMAX = (0.86, 0.95, 0.30)


def airdam(X, Y, Z):
    """Black lower valance / spoiler under the front bumper with the full-width intake slot."""
    yy = np.abs(Y)
    xb = 2.117 - 0.055 * (yy / 0.8) ** 2 - 0.028 - np.maximum(0.0, 0.30 - Z) * 0.35
    d = X - xb
    d = smax(d, (yy - (w_crease(X) - 0.03)), 0.10)
    d = smax(d, np.maximum(Z - 0.36, 0.186 - Z), 0.012)
    d = smax(d, 1.72 - X, 0.0)
    d = smax(d, -np.maximum(cyl_y(X, Y, Z, X_FA, R_F, ARCH_F + 0.01), 0.55 - yy), 0.01)
    slot = _rbox2(Y, Z - 0.272, 0.56, 0.034, 0.012)
    d = smax(d, -np.maximum(slot, -(X - (xb - 0.05))), 0.004)
    # vanes inside the slot
    v = np.maximum(np.abs(np.mod(Z - 0.272 + 0.009, 0.018) - 0.009) - 0.0022, np.maximum(slot - 0.002, np.abs(X - (xb - 0.03)) - 0.012))
    return np.minimum(d, v)


AIRDAM_BMIN = (1.70, -0.93, 0.17)
AIRDAM_BMAX = (2.10, 0.93, 0.38)
