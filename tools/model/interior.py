"""DMC-12 cabin: seats, dashboard, binnacle, console, door cards, headliner, carpets, controls.

Blender frame (X fwd, Y left, Z up). LHD: driver at Y=+0.37.
Moving parts (steering wheel, pedals, shifter, handbrake) are modelled in LOCAL pivot frames.
"""
import numpy as np
from sdf import smin, smax, interp, poly2d
import body as B
import shellx as SX
from body import _rbox2
from details import rbox3, cap_x

DEG = np.pi / 180
SEAT_Y = 0.37
FLOOR_Z = 0.255
CAB_X0, CAB_X1 = -0.79, 0.90


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


# ======================================================================================
# Seats
RECLINE = 21 * DEG
SEAT_X_REAR, SEAT_X_FRONT = -0.44, 0.08
SEAT_ZB = 0.36            # cushion height at the rear (H-point region)


def seat(X, Y, Z, side=1):
    t = Y * side - SEAT_Y
    at = np.abs(t)
    # --- cushion
    xc = 0.5 * (SEAT_X_REAR + SEAT_X_FRONT)
    hx = 0.5 * (SEAT_X_FRONT - SEAT_X_REAR)
    u = (X - SEAT_X_REAR) / (SEAT_X_FRONT - SEAT_X_REAR)          # 0 rear .. 1 front
    ztop = SEAT_ZB + 0.035 * smoothstep(0.55, 1.0, u) + 0.055 * smoothstep(0.12, 0.235, at) * (1 - 0.4 * u)
    ztop = ztop - 0.012 * np.exp(-(t / 0.11) ** 2) * smoothstep(0.1, 0.5, u) * (1 - smoothstep(0.8, 1.0, u))
    cush = rbox3(X, t, Z, (xc, 0.0, 0.30), (hx, 0.255, 0.16), 0.045)
    cush = smax(cush, Z - ztop, 0.035)
    # stitch grooves on cushion (two longitudinal)
    gro = np.sqrt((at - 0.085) ** 2 + (Z - ztop) ** 2) - 0.004
    cush = smax(cush, -np.maximum(gro, np.abs(u - 0.5) - 0.42), 0.003)
    # --- backrest (local frame along the recline): Recaro sports seats on the reference car, with
    # full-height side bolsters and a separate headrest on two posts
    xo, zo = SEAT_X_REAR + 0.02, SEAT_ZB - 0.02
    sa, ca = np.sin(RECLINE), np.cos(RECLINE)
    a = -(X - xo) * sa + (Z - zo) * ca                 # up the backrest
    n = (X - xo) * ca + (Z - zo) * sa                  # forward
    w = 0.262 - 0.020 * smoothstep(0.40, 0.60, a)
    nf = 0.070 * smoothstep(0.12, 0.21, at) * (1 - smoothstep(0.46, 0.60, a)) \
        + 0.018 * np.exp(-((a - 0.16) / 0.08) ** 2)
    back = rbox3(a, t, n, (0.30, 0.0, -0.075), (0.30, 0.27, 0.085), 0.05)
    back = np.maximum(back, at - w)
    back = smax(back, n - nf, 0.03)
    # stitched seams: the centre panel between the bolsters, and a lumbar seam across it
    gv = np.sqrt((at - 0.115) ** 2 + (n - nf) ** 2) - 0.0045
    gv = np.maximum(gv, np.abs(a - 0.30) - 0.26)
    gh = np.sqrt((a - 0.27) ** 2 + (n - nf) ** 2) - 0.0035
    gh = np.maximum(gh, at - 0.115)
    back = smax(back, -np.minimum(gv, gh), 0.003)
    # headrest: a padded block on two posts above the backrest
    head = rbox3(a, t, n, (0.690, 0.0, -0.062), (0.098, 0.128, 0.052), 0.045)
    posts = np.minimum(cap_x(a, t, n, (0.56, 0.075, -0.075), (0.62, 0.075, -0.07), 0.007),
                       cap_x(a, t, n, (0.56, -0.075, -0.075), (0.62, -0.075, -0.07), 0.007))
    back = np.minimum(back, np.minimum(head, posts))
    d = smin(cush, back, 0.03)
    return d


def seat_base(X, Y, Z, side=1):
    """Black plastic seat frame skirt + runners."""
    t = Y * side - SEAT_Y
    skirt = rbox3(X, t, Z, (-0.17, 0.0, 0.265), (0.25, 0.235, 0.03), 0.015)
    run = np.minimum(rbox3(X, t, Z, (-0.12, 0.17, 0.262), (0.30, 0.012, 0.010), 0.004),
                     rbox3(X, t, Z, (-0.12, -0.17, 0.262), (0.30, 0.012, 0.010), 0.004))
    lever = cap_x(X, t, Z, (-0.10, 0.27 * 1, 0.30), (0.02, 0.275, 0.29), 0.008)
    return np.minimum(np.minimum(skirt, run), lever)


# ======================================================================================
# Dashboard
GAUGE_U0 = (0.40, 0.725)
GAUGE_DEPTH = 0.115
GAUGE_FACE = (GAUGE_U0[0] + GAUGE_DEPTH * np.cos(14 * DEG), SEAT_Y, GAUGE_U0[1] - GAUGE_DEPTH * np.sin(14 * DEG))


def dash_top_z(X, Y):
    return 0.835 - (0.80 - X) * 0.09


def x_dash_face(Z):
    return 0.475 + (0.80 - Z) * 0.12


def dashboard(X, Y, Z):
    yy = np.abs(Y)
    ws = B.d_windshield(X, yy, Z)
    d = smax(Z - dash_top_z(X, Y), ws + 0.014, 0.02)
    d = smax(d, x_dash_face(Z) - X, 0.03)                       # cabin-facing face
    d = smax(d, 0.535 - Z, 0.04)                                # underside of the upper dash
    d = smax(d, yy - 0.805, 0.03)                               # end caps at the door apertures
    d = smax(d, X - 0.86, 0.0)
    # lower dash on passenger side (glovebox volume / knee panel)
    lo = rbox3(X, Y, Z, (0.70, -0.42, 0.48), (0.20, 0.36, 0.08), 0.04)
    lo = smax(lo, (0.58 + (0.56 - Z) * 0.3) - X, 0.02)
    d = smin(d, lo, 0.03)
    # instrument binnacle: surround frame + hood overhang (driver)
    fr = rbox3(X, Y, Z, (0.555, SEAT_Y, 0.775), (0.165, 0.300, 0.125), 0.045)
    hood = rbox3(X, Y, Z, (0.515, SEAT_Y, 0.872), (0.105, 0.300, 0.030), 0.028)
    bx = smin(fr, hood, 0.03)
    bx = smax(bx, Z - 0.905, 0.02)
    d = smin(d, bx, 0.03)
    # gauge window recess (faces the driver, tilted 14 deg)
    gu = (X - GAUGE_U0[0]) * np.cos(14 * DEG) - (Z - GAUGE_U0[1]) * np.sin(14 * DEG)
    gw = _rbox2(Y - SEAT_Y, Z - GAUGE_U0[1] - 0.012, 0.272, 0.080, 0.025)
    rec = np.maximum(gw, np.maximum(-gu - 0.12, gu - 0.13))
    d = smax(d, -rec, 0.008)
    # end vents (round eyeballs) recess
    for s in (1, -1):
        r = np.sqrt((Y - s * 0.735) ** 2 + (Z - 0.700) ** 2) - 0.040
        d = smax(d, -np.maximum(r, x_dash_face(Z) + 0.035 - X), 0.006)
    # glovebox lid seam on passenger dash top (shallow groove)
    gb = np.abs(_rbox2(X - 0.64, Y + 0.42, 0.10, 0.20, 0.02)) - 0.0015
    d = smax(d, -np.maximum(gb, np.abs(Z - dash_top_z(X, Y)) - 0.004), 0.001)
    # defrost slot along the windshield base
    df = np.maximum(np.abs(ws + 0.030) - 0.004, np.abs(Z - dash_top_z(X, Y)) - 0.006)
    df = np.maximum(df, yy - 0.55)
    d = smax(d, -df, 0.002)
    # knee cut-out under the binnacle for the driver's legs (open under the column)
    knee = rbox3(X, Y, Z, (0.52, SEAT_Y, 0.47), (0.10, 0.24, 0.08), 0.04)
    d = smax(d, -knee, 0.03)
    # never outside the body shell
    return np.maximum(d, B.shell(X, Y, Z) + 0.006)


def center_stack(X, Y, Z):
    xf = 0.455 + (0.78 - Z) * 0.20
    d = rbox3(X, Y, Z, (0.62, 0.0, 0.62), (0.22, 0.125, 0.20), 0.03)
    d = smax(d, xf - X, 0.02)
    # vents, radio, HVAC recesses
    rec = np.minimum(np.minimum(
        _rbox2(np.abs(Y) - 0.052, Z - 0.735, 0.044, 0.030, 0.006),
        _rbox2(Y, Z - 0.655, 0.090, 0.024, 0.004)),
        _rbox2(Y, Z - 0.555, 0.098, 0.050, 0.008))
    d = smax(d, -np.maximum(rec, -(X - (xf + 0.018))), 0.003)
    return d


def stack_inserts(X, Y, Z):
    """Black inserts: vent louvres, radio face, HVAC panel with knobs."""
    xf = 0.455 + (0.78 - Z) * 0.20
    u = X - (xf + 0.014)
    vents = np.maximum(_rbox2(np.abs(Y) - 0.052, Z - 0.735, 0.044, 0.030, 0.006), np.abs(u + 0.006) - 0.004)
    slats = np.maximum(np.maximum(_rbox2(np.abs(Y) - 0.052, Z - 0.735, 0.042, 0.028, 0.004),
                                  np.abs(np.mod(Z - 0.735 + 0.006, 0.012) - 0.006) - 0.0016), np.abs(u + 0.002) - 0.008)
    radio = np.maximum(_rbox2(Y, Z - 0.655, 0.088, 0.022, 0.003), np.abs(u + 0.004) - 0.004)
    hvac = np.maximum(_rbox2(Y, Z - 0.555, 0.096, 0.048, 0.006), np.abs(u + 0.004) - 0.004)
    d = np.minimum(np.minimum(vents, slats), np.minimum(radio, hvac))
    for ky, kz, r in [(-0.060, 0.565, 0.016), (0.0, 0.565, 0.016), (0.060, 0.565, 0.016), (-0.072, 0.660, 0.008), (0.072, 0.660, 0.008)]:
        k = np.maximum(np.sqrt((Y - ky) ** 2 + (Z - kz) ** 2) - r, np.abs(u + 0.012) - 0.012)
        d = np.minimum(d, k)
    return d


def end_vents(X, Y, Z):
    d = np.full(np.shape(X), 1.0)
    for s in (1, -1):
        r = np.sqrt((Y - s * 0.735) ** 2 + (Z - 0.700) ** 2)
        xf = x_dash_face(Z)
        ring = np.maximum(np.abs(r - 0.036) - 0.004, np.abs(X - (xf + 0.012)) - 0.010)
        ball = np.sqrt((X - (xf + 0.03)) ** 2 + (Y - s * 0.735) ** 2 + (Z - 0.700) ** 2) - 0.032
        ball = smax(ball, -np.maximum(np.abs(np.mod(Z - 0.70 + 0.005, 0.010) - 0.005) - 0.0015, xf + 0.012 - X), 0.001)
        d = np.minimum(d, np.minimum(ring, ball))
    return d


# ======================================================================================
# Console (centre tunnel)
def console(X, Y, Z):
    yy = np.abs(Y)
    w = 0.128 + (0.44 - Z) * 0.08
    top = 0.445 + 0.085 * smoothstep(-0.10, -0.16, X)          # armrest box rises at the rear
    d = np.maximum(yy - w, Z - top)
    d = smax(d, np.maximum(X - 0.47, -0.47 - X), 0.03)
    d = smax(d, FLOOR_Z - 0.01 - Z, 0.0)
    d = smax(d, d * 0 + (yy - w), 0.0)
    d = smax(d, Z - top, 0.02)
    # shifter tray recess, switch bank recess, armrest lid seam
    tray = _rbox2(X - 0.215, Y, 0.075, 0.075, 0.015)
    d = smax(d, -np.maximum(tray, -(Z - (top - 0.02))), 0.006)
    sw = _rbox2(X - 0.035, Y, 0.055, 0.085, 0.006)
    d = smax(d, -np.maximum(sw, -(Z - (top - 0.010))), 0.003)
    lid = np.abs(_rbox2(X + 0.30, Y, 0.145, 0.100, 0.015)) - 0.0012
    d = smax(d, -np.maximum(lid, -(Z - (top - 0.004))), 0.001)
    latch = _rbox2(X + 0.20, Y, 0.022, 0.035, 0.004)
    d = smax(d, -np.maximum(latch, -(Z - (top - 0.008))), 0.002)
    return d


def console_inserts(X, Y, Z):
    """Black switch bank (window/lock/hazard rockers) and clock bezel."""
    top = 0.445
    sw = np.maximum(_rbox2(X - 0.035, Y, 0.054, 0.084, 0.005), np.abs(Z - (top - 0.012)) - 0.004)
    rock = np.full(np.shape(X), 1.0)
    for i, yv in enumerate([-0.054, -0.018, 0.018, 0.054]):
        rock = np.minimum(rock, rbox3(X, Y, Z, (0.04, yv, top - 0.004), (0.022, 0.012, 0.006), 0.004))
    clock = np.maximum(_rbox2(X + 0.005, Y - 0.0, 0.012, 0.03, 0.003), np.abs(Z - (top - 0.006)) - 0.002)
    return np.minimum(np.minimum(sw, rock), clock)


# ======================================================================================
# Steering wheel (LOCAL frame: rim in XY plane, +Z toward the driver, +X = 12 o'clock)
SW_CENTER = np.array([0.120, SEAT_Y, 0.620])
COL_ANG = 25 * DEG


def steering_wheel_local(x, y, z):
    R, r = 0.190, 0.0155
    rho = np.sqrt(x * x + y * y)
    rim = np.sqrt((rho - R) ** 2 + (z * 1.15) ** 2) - r
    # hub pad (rounded triangle-ish pad)
    hub = rbox3(x, y, z, (-0.015, 0, -0.03), (0.075, 0.085, 0.035), 0.035)
    # 3 spokes at 3, 9 and 6 o'clock, slightly dropped
    def spoke(ang, drop):
        ex = np.array([np.cos(ang), np.sin(ang)])
        # flat wide spoke: scale perpendicular in-plane
        px, py = x * ex[1] - y * ex[0], x * ex[0] + y * ex[1]
        t = np.clip(py / (R - 0.005), 0, 1)
        wid = 0.030 - 0.010 * t
        flat = np.maximum(np.abs(px + drop * t) - wid, np.abs(z + 0.03 - 0.025 * t) - 0.012)
        return np.maximum(flat, np.maximum(-py, py - (R - 0.005)))
    sp = np.minimum(np.minimum(spoke(110 * DEG, 0.0), spoke(-110 * DEG, 0.0)), spoke(np.pi, 0.0))
    d = smin(rim, smin(hub, sp, 0.02), 0.012)
    boss = np.maximum(np.sqrt(x * x + y * y) - 0.03, np.abs(z + 0.075) - 0.02)
    return smin(d, boss, 0.01)


def column(X, Y, Z):
    """Steering column shroud from the wheel into the dash, plus stalks."""
    c = SW_CENTER
    ax = np.array([np.cos(COL_ANG), 0, -np.sin(COL_ANG)])
    a = c + ax * 0.10
    b = c + ax * 0.42
    sh = cap_x(X, Y, Z, a, b, 0.045)
    sh = smax(sh, -cap_x(X, Y, Z, c - ax * 0.05, c + ax * 0.08, 0.06), 0.01)
    # stalks: left (indicators) and right (wipers)
    s1 = cap_x(X, Y, Z, a + np.array([0.02, 0.04, 0.0]), a + np.array([-0.02, 0.17, 0.02]), 0.007)
    s2 = cap_x(X, Y, Z, a + np.array([0.02, -0.04, 0.0]), a + np.array([-0.02, -0.17, 0.02]), 0.007)
    k1 = rbox3(X, Y, Z, a + np.array([-0.02, 0.18, 0.02]), (0.012, 0.025, 0.012), 0.008)
    k2 = rbox3(X, Y, Z, a + np.array([-0.02, -0.18, 0.02]), (0.012, 0.025, 0.012), 0.008)
    return smin(sh, np.minimum(np.minimum(s1, s2), np.minimum(k1, k2)), 0.008)


# ======================================================================================
# Pedals (LOCAL frame: pivot at origin, arm hangs down -Z, pad faces -X (driver))
PEDALS = {'Clutch': (0.52, 0.0), 'Brake': (0.385, 0.0), 'Gas': (0.25, 0.0)}
PEDAL_PIVOT_X, PEDAL_PIVOT_Z = 0.86, 0.62


def pedal_local(x, y, z, kind):
    if kind == 'Gas':
        pad = rbox3(x, y, z, (-0.040, 0, -0.27), (0.008, 0.035, 0.075), 0.006)
        arm = cap_x(x, y, z, (0, 0, 0), (-0.03, 0, -0.20), 0.008)
    else:
        pad = rbox3(x, y, z, (-0.050, 0, -0.29), (0.010, 0.045, 0.040), 0.008)
        arm = cap_x(x, y, z, (0, 0, 0), (-0.045, 0, -0.27), 0.009)
    ribs = np.maximum(pad - 0.0, -(np.abs(np.mod(z + 0.01, 0.014) - 0.007) - 0.0025))
    return smin(arm, pad, 0.01)


# ======================================================================================
# Shifter (LOCAL: pivot at origin on the console, lever up +Z), handbrake (LOCAL)
def shifter_lever_local(x, y, z):
    rod = cap_x(x, y, z, (0, 0, 0), (0, 0, 0.17), 0.006)
    return rod


def shifter_knob_local(x, y, z):
    return np.sqrt(x * x + y * y + (z - 0.185) ** 2) - 0.021


def shift_boot_local(x, y, z):
    # leather gaiter: cone with folds
    rr = 0.055 - 0.04 * np.clip(z / 0.12, 0, 1)
    rr = rr + 0.004 * np.sin(z * 120) * (1 - np.clip(z / 0.12, 0, 1))
    d = np.sqrt(x * x + y * y) - rr
    return smax(d, np.maximum(-z, z - 0.12), 0.01)


def handbrake_local(x, y, z):
    lev = rbox3(x, y, z, (0.12, 0, 0.0), (0.13, 0.016, 0.018), 0.012)
    grip = rbox3(x, y, z, (0.21, 0, 0.0), (0.05, 0.019, 0.021), 0.016)
    btn = np.sqrt((x - 0.265) ** 2 + y * y + z * z) - 0.008
    return np.minimum(smin(lev, grip, 0.01), btn)


# ======================================================================================
# Shell-following trims
def layer(X, Y, Z, t_out, t_in):
    s = SX.shell(X, Y, Z)
    return np.maximum(s + t_out, -(s + t_in))


# how far trims stop short of a door/aperture edge; the edge walls' flange covers that strip
TRIM_RECESS = 0.0075


def front_end(X):
    """Extra width of the door's stainless inner frame at its front end (the end you see when the
    door is up: bare steel with the lamp and latch on the reference car), where the trims stop."""
    return 0.035 * smoothstep(0.35, 0.55, X)


def door_t(Z):
    return 0.085 - 0.050 * smoothstep(0.62, 0.86, Z) - 0.012 * smoothstep(0.95, 1.05, Z)


def door_trim(X, Y, Z, side=1, upper=False):
    s = SX.shell(X, Y, Z)
    t = door_t(Z)
    d = np.maximum(s + 0.004, -(s + t))
    # stop just short of the door's edge walls (build_edges.py), whose dark flange band runs under
    # the trim's end, so the two never share a surface (that z-fights into a sawtooth)
    Xs, Ys, Zs = SX.to_skin(X, Y, Z)
    d = np.maximum(d, B.r_door(Xs, Ys, Zs, side) + TRIM_RECESS + front_end(X))
    d = smax(d, -(B.r_door_glass(Xs, Ys, Zs, side) - TRIM_RECESS), 0.002)
    d = np.maximum(d, 0.345 - Z)
    split = 0.875
    d = np.maximum(d, (split - Z) if upper else (Z - split))
    if not upper:
        # the card lines the door side only: the shell distance also reaches the body's floor
        # skin, which would leave a plate across the cabin floor that swings out with the door
        d = np.maximum(d, -(B.flanks(X, Y, Z) + 0.13))
        # armrest / pull pocket bolster
        yy = Y * side
        inner = B.w_crease(X) - 0.085
        arm = rbox3(X, yy, Z, (-0.10, inner - 0.02, 0.625), (0.34, 0.035, 0.030), 0.025)
        arm = np.maximum(arm, -(s + 0.03))
        d = smin(d, arm, 0.02)
        pocket = rbox3(X, yy, Z, (-0.10, inner - 0.05, 0.645), (0.10, 0.03, 0.012), 0.01)
        d = smax(d, -pocket, 0.006)
        # inner handle recess near the front
        hr = rbox3(X, yy, Z, (0.30, inner, 0.70), (0.05, 0.03, 0.018), 0.012)
        d = smax(d, -hr, 0.005)
        # horizontal stitched seam on the card
        seam = np.abs(Z - 0.50) - 0.0025
        d = smax(d, -np.maximum(seam, np.abs(s + t) - 0.004), 0.001)
    return d


def body_trim(X, Y, Z):
    """Fixed inner trim: A-pillars, roof spine, B/C-pillar corners (headliner/vinyl)."""
    s = SX.shell(X, Y, Z)
    d = np.maximum(s + 0.004, -(s + 0.028))
    d = np.maximum(d, np.maximum(CAB_X0 - X, X - 0.86))
    d = np.maximum(d, 0.62 - Z)
    Xs, Ys, Zs = SX.to_skin(X, Y, Z)
    rd = np.minimum(B.r_door(Xs, Ys, Zs, 1), B.r_door(Xs, Ys, Zs, -1))
    d = np.maximum(d, -(rd - TRIM_RECESS))
    d = smax(d, -(B.r_windshield(X, Y, Z) - 0.010), 0.004)
    return d


# ======================================================================================
# Floor, sills, bulkheads
def carpet(X, Y, Z):
    yy = np.abs(Y)
    toe = FLOOR_Z + np.maximum(0, X - 0.72) * 1.1
    d = np.maximum(np.abs(Z - toe + 0.008) - 0.010, np.maximum(-0.765 - X, X - 0.95))
    d = np.maximum(d, yy - 0.66)
    d = np.maximum(d, 0.105 - yy)
    # footwell side walls (kick panels) carpeted
    kick = np.maximum(np.abs(yy - 0.80) - 0.008, np.maximum(np.maximum(0.45 - X, X - 0.93), np.maximum(FLOOR_Z - Z, Z - 0.56)))
    # rear bulkhead lower part
    bulk = np.maximum(np.abs(X + 0.770) - 0.010, np.maximum(yy - 0.80, np.maximum(FLOOR_Z - Z, Z - 0.66)))
    return np.minimum(np.minimum(d, kick), bulk)


def sill(X, Y, Z):
    yy = np.abs(Y)
    d = rbox3(X, yy, Z, (0.0, 0.745, 0.295), (0.60, 0.095, 0.045), 0.015)
    return d


def sill_plate(X, Y, Z):
    """Black ribbed step plate with DMC lettering on the door sills."""
    yy = np.abs(Y)
    plate = rbox3(X, yy, Z, (0.02, 0.765, 0.342), (0.46, 0.075, 0.004), 0.003)
    ribs = np.maximum(np.abs(np.mod(yy - 0.69 + 0.006, 0.012) - 0.006) - 0.0028, np.abs(Z - 0.3465) - 0.0015)
    ribs = np.maximum(ribs, np.maximum(np.abs(X - 0.02) - 0.45, np.abs(yy - 0.765) - 0.068))
    return np.minimum(plate, ribs)


def parcel_shelf(X, Y, Z):
    yy = np.abs(Y)
    d = rbox3(X, Y, Z, (-0.715, 0.0, 0.66), (0.055, 0.78, 0.012), 0.008)
    return d


def rear_window(X, Y, Z):
    """Vertical cabin rear window behind the seats (glass)."""
    yy = np.abs(Y)
    d = np.maximum(np.abs(X + 0.785) - 0.0025, np.maximum(0.68 - Z, Z - 1.075))
    d = np.maximum(d, yy - (0.62 - (Z - 0.68) * 0.30))
    return d


def bulkhead_upper(X, Y, Z):
    """Vinyl panel around the rear window (between window and shell)."""
    yy = np.abs(Y)
    s = SX.shell(X, Y, Z)
    d = np.maximum(np.abs(X + 0.792) - 0.006, np.maximum(0.66 - Z, s + 0.02))
    hole = np.maximum(np.maximum(0.70 - Z, Z - 1.06), yy - (0.60 - (Z - 0.68) * 0.30))
    return smax(d, -hole, 0.01)


# the windscreen header (top edge of the glass) runs across at x ~ 0 (body.WS_T)
HEADER_X = float(B.WS_T[0])


def rear_mirror(X, Y, Z):
    m = rbox3(X, Y, Z, (HEADER_X - 0.035, 0.0, 1.030), (0.012, 0.115, 0.032), 0.012)
    stem = cap_x(X, Y, Z, (HEADER_X - 0.025, 0, 1.050), (HEADER_X - 0.045, 0, 1.100), 0.008)
    return smin(m, stem, 0.01)


def sun_visor(X, Y, Z, side=1):
    yy = Y * side
    # hinged along the windshield header; flat padded board lying against the headliner
    xc = HEADER_X - 0.13
    zx = 1.086 + (X - xc) * 0.03
    v = rbox3(X, yy, Z, (xc, 0.30, 1.0), (0.075, 0.19, 0.5), 0.03)
    v = np.maximum(v, np.abs(Z - zx) - 0.009)
    return v


def seatbelt_buckles(X, Y, Z):
    d = np.full(np.shape(X), 1.0)
    for s in (1, -1):
        b = rbox3(X, Y, Z, (-0.32, s * 0.155, 0.40), (0.025, 0.012, 0.040), 0.008)
        d = np.minimum(d, b)
    return d


def belt_buttons(X, Y, Z):
    d = np.full(np.shape(X), 1.0)
    for s in (1, -1):
        d = np.minimum(d, rbox3(X, Y, Z, (-0.32, s * 0.155, 0.442), (0.012, 0.009, 0.006), 0.003))
    return d


def door_strap(X, Y, Z, side=1):
    yy = Y * side
    inner = B.w_crease(X) - 0.075 - (Z - 0.62) * 0.35
    strap = np.maximum(rbox3(X, yy, Z, (0.05, inner - 0.005, 0.79), (0.016, 0.004, 0.09), 0.003), 0.70 - Z)
    return strap


def courtesy_lamp(X, Y, Z, side=1):
    yy = Y * side
    return rbox3(X, yy, Z, (0.12, B.w_crease(X) - 0.050, 0.352), (0.045, 0.018, 0.006), 0.004)
