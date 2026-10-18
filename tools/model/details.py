"""Exterior detail parts (SDF) for the DMC-12: lamps, grille, louvres, mirrors, wipers..."""
import numpy as np
from sdf import smin, smax, interp, cyl_y, poly2d, box
import body as B
from body import _rbox2

DEG = np.pi / 180


def rbox3(px, py, pz, c, h, r):
    qx = np.abs(px - c[0]) - h[0] + r
    qy = np.abs(py - c[1]) - h[1] + r
    qz = np.abs(pz - c[2]) - h[2] + r
    o = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return o + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0) - r


def cap_x(px, py, pz, a, b, r):
    """Capsule between points a,b."""
    a = np.asarray(a)
    b = np.asarray(b)
    ba = b - a
    wx, wy, wz = px - a[0], py - a[1], pz - a[2]
    t = np.clip((wx * ba[0] + wy * ba[1] + wz * ba[2]) / (ba @ ba), 0, 1)
    dx, dy, dz = wx - ba[0] * t, wy - ba[1] * t, wz - ba[2] * t
    return np.sqrt(dx * dx + dy * dy + dz * dz) - r


# ======================================================================================
# Headlights (US quad rectangular sealed beams in the nose recesses)
HL_ZC = 0.5 * (B.HL_Z[0] + B.HL_Z[1])
HL_HZ = 0.5 * (B.HL_Z[1] - B.HL_Z[0])
NOSE_TILT = np.arctan(0.20)


def _hl_local(X, Y, Z, yc):
    """Local lamp coords: u = depth behind nose face (+ = forward), v lateral, w vertical."""
    yy = np.abs(Y)
    u = (X - B.x_nose(Z)) * np.cos(NOSE_TILT)
    return u, yy - yc, Z - HL_ZC


def headlight_lens(X, Y, Z, yc, hw):
    u, v, w = _hl_local(X, Y, Z, yc)
    face = -0.010 + 0.004 * (1 - (v / hw) ** 2 * 0.6 - (w / HL_HZ) ** 2 * 0.6)
    d = np.maximum(u - face, -(u - face) - 0.004)
    return smax(d, _rbox2(v, w, hw - 0.006, HL_HZ - 0.006, 0.010), 0.002)


def headlight_reflector(X, Y, Z, yc, hw):
    u, v, w = _hl_local(X, Y, Z, yc)
    # parabolic bowl, focal ~25mm, rim at u=-0.016
    bowl = -0.016 - 0.030 + (v * v + w * w * 1.3) / (4 * 0.028)
    d = np.abs(u - np.minimum(bowl, -0.016)) - 0.0012
    d = np.maximum(d, u + 0.015)
    return smax(d, _rbox2(v, w, hw - 0.007, HL_HZ - 0.007, 0.010), 0.002)


def headlight_bulb(X, Y, Z, yc, hw):
    u, v, w = _hl_local(X, Y, Z, yc)
    return np.sqrt((u + 0.038) ** 2 + v * v + w * w) - 0.007


def headlight_bezel(X, Y, Z, yc, hw):
    """Black surround / back plate filling the recess around the lamp."""
    u, v, w = _hl_local(X, Y, Z, yc)
    outer = _rbox2(v, w, hw + 0.004, HL_HZ + 0.004, 0.008)
    inner = _rbox2(v, w, hw - 0.007, HL_HZ - 0.007, 0.010)
    ring = smax(outer, -inner, 0.002)
    return smax(ring, np.maximum(u + 0.012, -u - 0.034), 0.002)


# ======================================================================================
# Grille between the inner headlights: horizontal black slats + badge
def grille_slats(X, Y, Z):
    yy = np.abs(Y)
    u = (X - B.x_nose(Z)) * np.cos(NOSE_TILT)
    zc = HL_ZC
    n = 9
    pitch = (2 * HL_HZ - 0.006) / n
    k = np.clip(np.round((Z - zc) / pitch), -(n // 2), n // 2)
    dz = Z - (zc + k * pitch)
    # slats tilt down-forward
    s = np.abs(dz + (u + 0.015) * 0.25) - 0.0035
    d = np.maximum(s, np.maximum(u + 0.010, -u - 0.030))
    d = np.maximum(d, yy - (B.GRILLE_Y - 0.004))
    frame = _rbox2(Y, Z - zc, B.GRILLE_Y + 0.003, HL_HZ + 0.003, 0.008)
    inner = _rbox2(Y, Z - zc, B.GRILLE_Y - 0.006, HL_HZ - 0.006, 0.006)
    fr = smax(frame, -inner, 0.0015)
    fr = np.maximum(fr, np.maximum(u + 0.009, -u - 0.034))
    back = np.maximum(_rbox2(Y, Z - zc, B.GRILLE_Y, HL_HZ, 0.006), np.abs(u + 0.032) - 0.002)
    return np.minimum(np.minimum(d, fr), back)


# DMC logotype polygons (letters drawn on a 1.0 x 0.26 em grid, centred)
def _dmc_polys():
    # letter shapes approximate the DMC badge: reversed-C 'D', 'M' with two slots, 'C'
    polys = []
    # 'D' : like a reversed C
    polys.append([(-0.50, 0.13), (-0.21, 0.13), (-0.18, 0.10), (-0.18, -0.10), (-0.21, -0.13), (-0.50, -0.13),
                  (-0.50, -0.055), (-0.265, -0.055), (-0.265, 0.055), (-0.50, 0.055)])
    # 'M'
    polys.append([(-0.155, 0.13), (0.135, 0.13), (0.165, 0.10), (0.165, -0.13), (0.085, -0.13), (0.085, 0.06),
                  (0.045, 0.06), (0.045, -0.13), (-0.035, -0.13), (-0.035, 0.06), (-0.075, 0.06), (-0.075, -0.13),
                  (-0.155, -0.13)])
    # 'C'
    polys.append([(0.50, 0.13), (0.22, 0.13), (0.19, 0.10), (0.19, -0.10), (0.22, -0.13), (0.50, -0.13),
                  (0.50, -0.055), (0.275, -0.055), (0.275, 0.055), (0.50, 0.055)])
    return [np.array(p) for p in polys]


DMC_POLYS = _dmc_polys()


def dmc_logo_2d(u, v, scale):
    d = np.full(np.shape(u), 1.0)
    for p in DMC_POLYS:
        d = np.minimum(d, poly2d(u / scale, v / scale, p) * scale)
    return d


def grille_badge_plate(X, Y, Z):
    u = (X - B.x_nose(Z)) * np.cos(NOSE_TILT)
    zc = HL_ZC + 0.005
    plate = _rbox2(Y, Z - zc, 0.082, 0.020, 0.003)
    return np.maximum(plate, np.maximum(u + 0.010, -u - 0.016))


def grille_badge_letters(X, Y, Z):
    u = (X - B.x_nose(Z)) * np.cos(NOSE_TILT)
    zc = HL_ZC + 0.005
    lt = dmc_logo_2d(-Y, Z - zc, 0.150)
    return smax(lt, np.maximum(u + 0.0075, -u - 0.0105), 0.0008)


# ======================================================================================
# Front indicators in bumper pockets + side markers
def front_turn_lens(X, Y, Z):
    yy = np.abs(Y)
    xb = 2.117 - 0.055 * (yy / 0.8) ** 2
    r = _rbox2(yy - 0.585, Z - 0.455, 0.083, 0.026, 0.004)
    face = xb - 0.004
    d = np.maximum(X - face, (face - 0.006) - X)
    return smax(d, r, 0.0015)


def side_marker_front(X, Y, Z):
    yy = np.abs(Y)
    w = B.w_crease(X) + 0.010
    r = _rbox2(X - 1.73, Z - 0.572, 0.10, 0.011, 0.006)
    d = np.maximum(yy - (w + 0.003), (w - 0.006) - yy)
    return smax(d, r, 0.0015)


def side_marker_rear(X, Y, Z):
    yy = np.abs(Y)
    w = B.w_crease(X) + 0.010
    r = _rbox2(X + 1.80, Z - 0.605, 0.085, 0.011, 0.006)
    d = np.maximum(yy - (w + 0.003), (w - 0.006) - yy)
    return smax(d, r, 0.0015)


# ======================================================================================
# Tail lamps: segmented lens grid inside the tail recess
TL_ROWS = [(0.6405, 0.6965), (0.6995, 0.7555), (0.7585, 0.8115)]


def _tl_cols():
    cols = [('Turn', 0.707, 0.781)]
    w = (0.701 - 0.366) / 4
    for i in range(4):
        cols.append(('Tail', 0.701 - (i + 1) * w + 0.0015, 0.701 - i * w - 0.0015))
    cols.append(('Reverse', 0.300, 0.362))
    return cols


TL_COLS = _tl_cols()


def tail_cells(X, Y, Z, kind):
    yy = np.abs(Y)
    face = B.x_tail(Z) + 0.006
    d = np.full(np.shape(X), 1.0)
    for k, a, b in TL_COLS:
        if k != kind:
            continue
        for z0, z1 in TL_ROWS:
            dome = 0.0025 * (1 - ((yy - 0.5 * (a + b)) / (0.5 * (b - a))) ** 2) * (1 - ((Z - 0.5 * (z0 + z1)) / (0.5 * (z1 - z0))) ** 2)
            r = _rbox2(yy - 0.5 * (a + b), Z - 0.5 * (z0 + z1), 0.5 * (b - a), 0.5 * (z1 - z0), 0.004)
            s = np.maximum(face - X - np.maximum(dome, 0), X - (face + 0.008))
            d = np.minimum(d, smax(s, r, 0.0012))
    return d


def tail_housing(X, Y, Z):
    """Dark grid/back plate behind the cells and the recessed plate panel."""
    yy = np.abs(Y)
    zc = 0.5 * (B.TL_Z[0] + B.TL_Z[1])
    hz = 0.5 * (B.TL_Z[1] - B.TL_Z[0])
    face = B.x_tail(Z)
    r = _rbox2(Y, Z - zc, B.TL_Y - 0.001, hz - 0.001, 0.018)
    back = np.maximum(r, np.maximum(face + 0.030 - X, X - (face + 0.034)))
    # grid webs between cells (slightly recessed from cell faces)
    web = np.maximum(r, np.maximum(face + 0.007 - X, X - (face + 0.034)))
    web = np.maximum(web, yy - 0.786)
    web = np.maximum(web, 0.293 - yy)
    # plate panel: recessed plate area
    plate = np.maximum(_rbox2(Y, Z - zc, 0.270, hz - 0.010, 0.010), np.maximum(face + 0.022 - X, X - (face + 0.034)))
    return np.minimum(np.minimum(back, web), plate)


# ======================================================================================
# Engine lid: black frame + level louvre slats + centre rib
LID_GAP = 0.004


def _fb_z(X):
    return B.FB_R1[1] + (X - B.FB_R1[0]) * (-B.FB_N[0] / B.FB_N[1])


LID_SLATS = 5


def lid_frame(X, Y, Z):
    yy = np.abs(Y)
    fb = B.d_fastback(X, yy, Z)
    reg = poly2d(X, Y, B.LID_POLY) + LID_GAP / 2
    inner = poly2d(X, Y, B.LID_POLY) + 0.040
    d = smax(reg, -inner, 0.003)
    d = smax(d, np.maximum(fb + 0.0005, -fb - 0.030), 0.003)
    return d


def lid_slats(X, Y, Z):
    yy = np.abs(Y)
    x0, x1 = -0.790, -1.885
    pitch = (x0 - x1) / LID_SLATS
    k = np.clip(np.floor((x0 - X) / pitch), 0, LID_SLATS - 1)
    xr = x0 - (k + 1) * pitch + 0.018         # rear edge of slat k
    xf = x0 - k * pitch + 0.030                # front edge (tucks under the previous slat)
    ztop = _fb_z(xr) - 0.002
    s = np.maximum(Z - ztop, (ztop - 0.007) - Z)
    s = np.maximum(s, np.maximum(xr - X, X - xf))
    inner = poly2d(X, Y, B.LID_POLY) + 0.030
    s = smax(s, inner, 0.002)
    rib = np.maximum(np.abs(Y) - 0.012, np.maximum(B.d_fastback(X, yy, Z) + 0.001, -B.d_fastback(X, yy, Z) - 0.05))
    rib = np.maximum(rib, inner)
    return np.minimum(s, rib)


def lid_under(X, Y, Z):
    """Dark mesh/pan below the louvres (engine-cover inner skin) - perforated look via texture."""
    yy = np.abs(Y)
    fb = B.d_fastback(X, yy, Z)
    inner = poly2d(X, Y, B.LID_POLY) + 0.030
    d = np.maximum(np.abs(fb + 0.075) - 0.0015, inner)
    return d


LID_HINGE = (-0.762, float(_fb_z(-0.762)) - 0.012)


# ======================================================================================
# B-pillar vent inserts (black vanes inside the slots)
def bpillar_insert(X, Y, Z):
    yy = np.abs(Y)
    u = X + 0.800 + (Z - 0.94) * 0.12
    slot = _rbox2(u, Z - 0.945, 0.0185, 0.1015, 0.014)
    gs = B.d_glass_side(X, yy, Z)
    back = np.maximum(slot, np.abs(gs + 0.026) - 0.002)
    vanes = np.maximum(np.maximum(slot, np.abs(np.mod(Z + 0.0075, 0.015) - 0.0075) - 0.0018), np.maximum(gs + 0.026, -gs - 0.006))
    return np.minimum(back, vanes)


# ======================================================================================
# Mirrors (black housings on the door front corners)
MIRROR_C = np.array([0.500, 0.925, 0.925])


def mirror_housing(X, Y, Z, side=1):
    Ys = Y * side
    c = MIRROR_C
    # head: rounded box, glass faces rearward (-X)
    # head: rounded box, wedge-shaped (deeper at the outer end), glass faces rearward (-X)
    hx = 0.030 + 0.010 * np.clip((Ys - c[1]) / 0.068, -1, 1)
    head = rbox3(X, Ys, Z, (c[0] + 0.004, c[1], c[2]), (1.0, 0.068, 0.044), 0.016)
    head = np.maximum(head, np.abs(X - (c[0] + 0.004)) - hx)
    cavity = rbox3(X, Ys, Z, (c[0] - 0.034, c[1], c[2]), (0.012, 0.060, 0.036), 0.008)
    head = smax(head, -cavity, 0.002)
    # short stalk to a triangular foot on the door's front-top corner
    stalk = cap_x(X, Ys, Z, (c[0] + 0.012, 0.815, 0.885), (c[0] + 0.012, c[1] - 0.04, c[2] - 0.01), 0.013)
    foot = rbox3(X, Ys, Z, (c[0] + 0.035, 0.800, 0.872), (0.055, 0.016, 0.024), 0.010)
    d = smin(smin(head, stalk, 0.015), foot, 0.015)
    return d


def mirror_glass(X, Y, Z, side=1):
    Ys = Y * side
    c = MIRROR_C
    return rbox3(X, Ys, Z, (c[0] - 0.030, c[1], c[2]), (0.0022, 0.0585, 0.0345), 0.007)


# ======================================================================================
# Wheel-well liners and underbody
def well_liner(X, Y, Z, front=True):
    yy = np.abs(Y)
    cx, cz, r = (B.X_FA, B.R_F, B.ARCH_F) if front else (B.X_RA, B.R_R, B.ARCH_R)
    d = np.abs(np.sqrt((X - cx) ** 2 + (Z - cz) ** 2) - (r + 0.010)) - 0.003
    d = np.maximum(d, np.maximum(yy - (B.w_crease(X) - 0.012), 0.52 - yy))
    d = np.maximum(d, (cz - 0.12) - Z)
    inner_wall = np.maximum(np.abs(yy - 0.53) - 0.003, np.sqrt((X - cx) ** 2 + (Z - cz) ** 2) - (r + 0.012))
    inner_wall = np.maximum(inner_wall, (cz - 0.12) - Z)
    return np.minimum(d, inner_wall)


def underbody(X, Y, Z):
    yy = np.abs(Y)
    pan = np.maximum(np.abs(Z - 0.215) - 0.006, np.maximum(yy - 0.88, np.maximum(X - 2.02, -1.98 - X)))
    pan = smax(pan, -B.arch_cyl(X, Y, Z, 0.02), 0.002)
    # backbone tunnel
    bb = rbox3(X, Y, Z, (0.1, 0, 0.24), (1.5, 0.11, 0.03), 0.02)
    return np.minimum(pan, bb)


# ======================================================================================
# Exhaust tips and muffler
def exhaust(X, Y, Z):
    yy = np.abs(Y)
    d = 1.0
    tip = np.sqrt((yy - 0.540) ** 2 + (Z - 0.300) ** 2)
    pipe = np.maximum(np.abs(tip - 0.026) - 0.0018, np.maximum(X + 2.105, -1.80 - X))
    muff = rbox3(X, Y, Z, (-1.80, 0, 0.30), (0.12, 0.45, 0.07), 0.05)
    return np.minimum(pipe, muff)


# ======================================================================================
# Door pull (small black recess pull below the strip near the rear of the door)
def door_handle(X, Y, Z, side=1):
    yy = Y * side
    zc = 0.578
    w = B.w_crease(X) - (B.z_crease(X) - zc) * np.tan(B.TUCK)
    face = rbox3(X, yy, Z, (-0.515, w + 0.002, zc), (0.060, 0.010, 0.012), 0.006)
    grip = rbox3(X, yy, Z, (-0.515, w + 0.006, zc - 0.006), (0.048, 0.010, 0.004), 0.003)
    return smax(face, -grip, 0.002)


# ======================================================================================
# "DeLorean" lettering embossed on the rear bumper (left side)
def _delorean_glyphs():
    # glyph boxes in a 1.0-high em; each glyph = list of rounded boxes (cx, cy, hx, hy) to union,
    # minus list of slots. DMC typeface: square, rounded, with horizontal slits.
    G = {
        'D': ([(0.0, 0.0, 0.33, 0.5)], [(-0.10, 0.0, 0.24, 0.17)]),
        'e': ([(0.0, -0.13, 0.33, 0.37)], [(0.05, -0.02, 0.29, 0.045), (0.15, -0.30, 0.20, 0.06)]),
        'L': ([(-0.20, 0.0, 0.13, 0.5), (0.0, -0.40, 0.33, 0.10)], []),
        'o': ([(0.0, -0.13, 0.33, 0.37)], [(0.0, -0.13, 0.17, 0.13)]),
        'r': ([(-0.20, -0.13, 0.13, 0.37), (0.0, 0.14, 0.30, 0.10)], []),
        'a': ([(0.0, -0.13, 0.33, 0.37)], [(-0.05, -0.06, 0.29, 0.045), (0.0, -0.32, 0.17, 0.06)]),
        'n': ([(0.0, -0.13, 0.33, 0.37)], [(0.0, -0.25, 0.17, 0.30)]),
    }
    text = 'DeLorean'
    adv = 0.78
    out = []
    x = 0.0
    for ch in text:
        adds, subs = G[ch]
        out.append(([(x + a, b, c, d) for a, b, c, d in adds], [(x + a, b, c, d) for a, b, c, d in subs]))
        x += adv
    return out, x - adv


DEL_GLYPHS, DEL_W = _delorean_glyphs()


def bumper_letters(X, Y, Z):
    yy = Y
    H = 0.050
    u = (-(Y - 0.38)) / H + DEL_W / 2         # reads left->right when seen from behind
    v = (Z - 0.488) / H
    d = np.full(np.shape(X), 1.0)
    for adds, subs in DEL_GLYPHS:
        g = np.full(np.shape(X), 1.0)
        for cx, cy, hx, hy in adds:
            g = np.minimum(g, _rbox2(u - cx, v - cy, hx, hy, 0.09))
        for cx, cy, hx, hy in subs:
            g = np.maximum(g, -_rbox2(u - cx, v - cy, hx, hy, 0.04))
        d = np.minimum(d, g)
    d = d * H
    xb = -2.097 + 0.05 * (np.abs(Y) / 0.85) ** 2
    slab = np.maximum((xb - 0.0025) - X, X - (xb + 0.004))
    return smax(d, slab, 0.0006)
