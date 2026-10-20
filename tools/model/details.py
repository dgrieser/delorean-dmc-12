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
# Headlights (US quad 4x6 in. rectangular sealed beams on a near-vertical black lamp panel,
# set into the wedge nose: clear fluted glass in a bright chrome rim, black surrounds)
HL_ZC = 0.5 * (B.HL_Z[0] + B.HL_Z[1])
HL_HZ = 0.5 * (B.HL_Z[1] - B.HL_Z[0])
LAMP_TILT = np.arctan(0.15)
NOSE_TILT = LAMP_TILT


def _hl_local(X, Y, Z, yc):
    """Local lamp coords: u = depth along the lamp-panel normal (+ = forward), v lateral, w vertical."""
    yy = np.abs(Y)
    u = (X - B.x_lamp(Z, yy)) * np.cos(LAMP_TILT)
    return u, yy - yc, Z - HL_ZC


def headlight_lens(X, Y, Z, yc, hw):
    u, v, w = _hl_local(X, Y, Z, yc)
    face = -0.0075 + 0.004 * (1 - (v / hw) ** 2 * 0.6 - (w / HL_HZ) ** 2 * 0.6)
    d = np.maximum(u - face, -(u - face) - 0.004)
    return smax(d, _rbox2(v, w, hw - 0.010, HL_HZ - 0.010, 0.010), 0.002)


def headlight_rim(X, Y, Z, yc, hw):
    """Chrome retaining rim around the sealed-beam glass."""
    u, v, w = _hl_local(X, Y, Z, yc)
    outer = _rbox2(v, w, hw - 0.004, HL_HZ - 0.004, 0.012)
    inner = _rbox2(v, w, hw - 0.011, HL_HZ - 0.011, 0.009)
    ring = smax(outer, -inner, 0.0015)
    prof = np.maximum(u + 0.003 + 0.0025 * np.clip(-inner / 0.007, 0, 1), -u - 0.012)      # rounded crown
    return smax(ring, prof, 0.0015)


def headlight_reflector(X, Y, Z, yc, hw):
    """Rectangular sealed-beam reflector: a deep bowl whose rim follows the lamp's rounded
    rectangle (superellipse depth profile), not a round dish."""
    u, v, w = _hl_local(X, Y, Z, yc)
    q = ((np.abs(v) / (hw - 0.010)) ** 4 + (np.abs(w) / (HL_HZ - 0.010)) ** 4) ** 0.25
    bowl = -0.014 - 0.034 * np.clip(1 - q * q, 0, 1)
    d = np.abs(u - np.minimum(bowl, -0.014)) - 0.0012
    d = np.maximum(d, u + 0.013)
    return smax(d, _rbox2(v, w, hw - 0.010, HL_HZ - 0.010, 0.010), 0.002)


def headlight_bulb(X, Y, Z, yc, hw):
    u, v, w = _hl_local(X, Y, Z, yc)
    return np.sqrt((u + 0.036) ** 2 + v * v + w * w) - 0.007


def headlight_bezel(X, Y, Z, yc, hw):
    """Black surround / back plate filling the lamp band around the lamp (the bezels of
    neighbouring lamps and the grille frame meet, so the band reads as one black panel), plus a
    black liner on the band's top wall: the header the photos show under the bonnet edge."""
    u, v, w = _hl_local(X, Y, Z, yc)
    outer = _rbox2(v, w, hw + 0.007, HL_HZ + 0.007, 0.006)
    inner = _rbox2(v, w, hw - 0.006, HL_HZ - 0.006, 0.010)
    ring = smax(outer, -inner, 0.002)
    ring = smax(ring, np.maximum(u + 0.004, -u - 0.034), 0.002)
    head = np.maximum(np.abs(w - (HL_HZ - 0.001)) - 0.004, np.abs(v) - (hw + 0.007))
    head = np.maximum(head, np.maximum(u - 0.07, -u - 0.03))
    head = np.maximum(head, B.shell(X, Y, Z) + 0.0015)
    return np.minimum(ring, head)


# ======================================================================================
# Grille between the inner headlights: horizontal black ribs; the DMC letters sit on them
def grille_slats(X, Y, Z):
    yy = np.abs(Y)
    u = (X - B.x_lamp(Z, yy)) * np.cos(LAMP_TILT)
    zc = HL_ZC
    n = 11
    pitch = (2 * HL_HZ - 0.008) / n
    k = np.clip(np.round((Z - zc) / pitch), -(n // 2), n // 2)
    dz = Z - (zc + k * pitch)
    s = np.abs(dz + (u + 0.010) * 0.20) - 0.0032
    d = np.maximum(s, np.maximum(u + 0.003, -u - 0.026))
    d = np.maximum(d, yy - (B.GRILLE_Y - 0.004))
    frame = _rbox2(Y, Z - zc, B.GRILLE_Y + 0.004, HL_HZ + 0.007, 0.006)
    inner = _rbox2(Y, Z - zc, B.GRILLE_Y - 0.006, HL_HZ - 0.006, 0.006)
    fr = smax(frame, -inner, 0.0015)
    fr = np.maximum(fr, np.maximum(u + 0.002, -u - 0.034))
    back = np.maximum(_rbox2(Y, Z - zc, B.GRILLE_Y, HL_HZ, 0.006), np.abs(u + 0.028) - 0.002)
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


def dmc_logo_2d(u, v, scale, vscale=None):
    vs = scale if vscale is None else vscale
    d = np.full(np.shape(u), 1.0)
    for p in DMC_POLYS:
        d = np.minimum(d, poly2d(u / scale, v / vs, p) * min(scale, vs))
    return d


BADGE_W, BADGE_H = 0.163, 0.031      # the badge on the reference car: 163 x 31 mm
BADGE_ZC = HL_ZC - 0.010


def grille_badge_letters(X, Y, Z):
    yy = np.abs(Y)
    u = (X - B.x_lamp(Z, yy)) * np.cos(LAMP_TILT)
    lt = dmc_logo_2d(-Y, Z - BADGE_ZC, BADGE_W, BADGE_H / 0.26)
    return smax(lt, np.maximum(u - 0.0025, -u - 0.004), 0.0008)


# ======================================================================================
# Front indicators in bumper pockets + side markers
def front_turn_lens(X, Y, Z):
    yy = np.abs(Y)
    xb = B.x_fbump(yy)
    r = _rbox2(yy - B.TURN_Y, Z - B.TURN_Z, B.TURN_HY, B.TURN_HZ, 0.004)
    face = xb - 0.014
    d = np.maximum(X - face, (face - 0.006) - X)
    return smax(d, r, 0.0015)


def front_turn_housing(X, Y, Z):
    """Black housing lining the bumper pocket round the indicator lens."""
    yy = np.abs(Y)
    xb = B.x_fbump(yy)
    outer = _rbox2(yy - B.TURN_Y, Z - B.TURN_Z, B.TURN_HY + B.TURN_RIM - 0.0005, B.TURN_HZ + B.TURN_RIM - 0.0005, 0.008)
    inner = _rbox2(yy - B.TURN_Y, Z - B.TURN_Z, B.TURN_HY - 0.001, B.TURN_HZ - 0.001, 0.004)
    ring = smax(outer, -inner, 0.0015)
    ring = np.maximum(ring, np.maximum(X - (xb - 0.004), (xb - 0.024) - X))
    back = np.maximum(outer, np.abs(X - (xb - 0.026)) - 0.002)
    return np.minimum(ring, back)


SMF_X, SMR_X = 1.686, -1.777        # marker centres (lens ends measured at 1.58 / 1.79 and -1.88 / -1.68)


def _marker(X, Y, Z, xc, hx):
    yy = np.abs(Y)
    xs = np.clip(X, xc - hx, xc + hx)
    w = B.w_crease(xs) + 0.008
    r = _rbox2(X - xc, Z - B.z_crease(X), hx, 0.0105, 0.006)
    d = np.maximum(yy - (w + 0.003), (w - 0.008) - yy)
    return smax(d, r, 0.0015)


def side_marker_front(X, Y, Z):
    # on the stainless wing ahead of the arch, in line with the rubbing strip
    return _marker(X, Y, Z, SMF_X, 0.098)


def side_marker_rear(X, Y, Z):
    return _marker(X, Y, Z, SMR_X, 0.096)


# ======================================================================================
# Tail lamps: 3 rows x 6 columns per side in one black tail panel (measured on the reference car:
# inner white reverse column, three red tail/stop columns, two amber indicator columns whose
# outer edge leans in with the body corner); the licence-plate panel between them
TL_ROWS = [(0.658, 0.703), (0.709, 0.751), (0.756, 0.796)]
TL_COLS = [('Reverse', 0.286, 0.335), ('Tail', 0.344, 0.426), ('Tail', 0.435, 0.516), ('Tail', 0.525, 0.604),
           ('Turn', 0.612, 0.666), ('Turn', 0.673, 0.740)]


def tl_outer(Z):
    """Outer edge of the lens grid: leans in towards the top with the rear corner."""
    return 0.737 - (Z - 0.658) * 0.52


def tail_cells(X, Y, Z, kind):
    yy = np.abs(Y)
    face = B.x_tail(Z) + 0.006
    edge = tl_outer(Z) - yy
    d = np.full(np.shape(X), 1.0)
    for k, a, b in TL_COLS:
        if k != kind:
            continue
        for z0, z1 in TL_ROWS:
            ym, hy = 0.5 * (a + b), 0.5 * (b - a)
            zm, hz = 0.5 * (z0 + z1), 0.5 * (z1 - z0)
            dome = 0.0025 * np.clip(1 - ((yy - ym) / hy) ** 2, 0, 1) * np.clip(1 - ((Z - zm) / hz) ** 2, 0, 1)
            r = _rbox2(yy - ym, Z - zm, hy, hz, 0.004)
            r = smax(r, -edge, 0.004)
            s = np.maximum(face - X - dome, X - (face + 0.008))
            d = np.minimum(d, smax(s, r, 0.0012))
    return d


def tail_housing(X, Y, Z):
    """Black tail panel: back plate and grid webs behind the cells, and the plate panel with its
    two moulded pads of square bosses either side of the plate."""
    yy = np.abs(Y)
    face = B.x_tail(Z)
    band = B.tail_band(Y, Z, -0.001)
    back = np.maximum(band, np.maximum(face + 0.030 - X, X - (face + 0.034)))
    # grid webs between cells (slightly recessed from cell faces)
    web = np.maximum(band, np.maximum(face + 0.009 - X, X - (face + 0.034)))
    web = np.maximum(web, 0.279 - yy)
    # plate panel and its pads
    zc = 0.5 * (B.TL_Z[0] + B.TL_Z[1])
    hz = 0.5 * (B.TL_Z[1] - B.TL_Z[0])
    plate = np.maximum(_rbox2(Y, Z - zc, 0.274, hz - 0.004, 0.010), np.maximum(face + 0.016 - X, X - (face + 0.034)))
    cu = np.mod(yy - 0.170 + 0.025, 0.050) - 0.025
    cv = np.mod(Z - 0.660 + 0.0245, 0.049) - 0.0245
    boss = np.maximum(_rbox2(cu, cv, 0.0215, 0.021, 0.004), np.maximum(np.abs(yy - 0.220) - 0.050, np.abs(Z - 0.7275) - 0.0735))
    boss = np.maximum(boss, np.maximum(face + 0.011 - X, X - (face + 0.034)))
    return np.minimum(np.minimum(back, web), np.minimum(plate, boss))


# ======================================================================================
# Engine cover: black frame + stepped louvre blades following the fastback + centre rib
LID_GAP = 0.004


def _fb_z(X):
    return B.z_fb(X)


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
    x0, x1 = -0.88, -1.86
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


LID_HINGE = (-0.84, float(_fb_z(-0.84)) - 0.012)


# ======================================================================================
# B-pillar vent inserts: a black liner with a centre divider inside each slot
def bpillar_insert(X, Y, Z):
    yy = np.abs(Y)
    u = X - B.BV_X + (Z - B.BV_Z) * 0.124
    slot = _rbox2(u, Z - B.BV_Z, B.BV_HU + 0.0015, B.BV_HZ + 0.0015, 0.022)
    gs = B.d_glass_side(X, yy, Z)
    back = np.maximum(slot, np.abs(gs + 0.026) - 0.002)
    divider = np.maximum(np.maximum(slot, np.abs(u) - 0.004), np.maximum(gs + 0.026, -gs - 0.004))
    walls = np.maximum(np.maximum(slot, -(slot + 0.004)), np.maximum(gs + 0.026, -gs - 0.002))
    return np.minimum(np.minimum(back, divider), walls)


# ======================================================================================
# Mirrors: black wedge housings on the door's front-top corner, just behind the A-pillar base
# (outer-top corner measured at x 0.29, |y| 0.98, z 0.87)
MIRROR_C = np.array([0.315, 0.915, 0.833])


def mirror_housing(X, Y, Z, side=1):
    Ys = Y * side
    c = MIRROR_C
    # head: rounded box, glass faces rearward (-X), deeper at the outer end, swept back outboard
    t = np.clip((Ys - c[1]) / 0.065, -1, 1)
    xs = X - 0.035 * t
    hx = 0.034 + 0.008 * t
    head = rbox3(xs, Ys, Z, (c[0], c[1], c[2]), (1.0, 0.066, 0.040), 0.016)
    head = np.maximum(head, np.abs(xs - c[0]) - hx)
    cavity = rbox3(xs, Ys, Z, (c[0] - hx - 0.004, c[1], c[2]), (0.010, 0.058, 0.032), 0.008)
    head = smax(head, -cavity, 0.002)
    # tapered stalk down to a triangular foot on the door skin at the window's front corner
    stalk = cap_x(X, Ys, Z, (c[0] + 0.035, 0.835, 0.815), (c[0] + 0.012, c[1] - 0.045, c[2] - 0.006), 0.014)
    foot = rbox3(X, Ys, Z, (c[0] + 0.075, 0.822, 0.808), (0.060, 0.014, 0.026), 0.010)
    d = smin(smin(head, stalk, 0.015), foot, 0.015)
    return d


def mirror_glass(X, Y, Z, side=1):
    Ys = Y * side
    c = MIRROR_C
    t = np.clip((Ys - c[1]) / 0.065, -1, 1)
    xs = X - 0.035 * t
    hx = 0.034 + 0.008 * t
    return rbox3(xs, Ys, Z, (c[0] - hx + 0.004, c[1], c[2]), (0.0022, 0.0575, 0.0315), 0.007)


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
    # kept inside the tucked-in lower flanks so no edge shows past the sills or bumpers
    pan = np.maximum(np.abs(Z - 0.215) - 0.006, np.maximum(yy - 0.76, np.maximum(X - 1.80, -1.90 - X)))
    pan = smax(pan, -B.arch_cyl(X, Y, Z, 0.02), 0.002)
    # backbone tunnel
    bb = rbox3(X, Y, Z, (0.1, 0, 0.24), (1.5, 0.11, 0.03), 0.02)
    return np.minimum(pan, bb)


# ======================================================================================
# Power antenna on the right front wing beside the windscreen (base and tip measured from the
# reference photos: it rakes back and out)
ANT_BASE = np.array([0.765, -0.795, 0.818])
ANT_TIP = np.array([0.660, -0.850, 1.60])


def antenna_mast(X, Y, Z):
    t = np.clip(((X - ANT_BASE[0]) * (ANT_TIP - ANT_BASE)[0] + (Y - ANT_BASE[1]) * (ANT_TIP - ANT_BASE)[1]
                 + (Z - ANT_BASE[2]) * (ANT_TIP - ANT_BASE)[2]) / np.sum((ANT_TIP - ANT_BASE) ** 2), 0, 1)
    r = 0.0032 - 0.0014 * t + 0.0015 * (t < 0.42)          # telescoping sections
    return cap_x(X, Y, Z, ANT_BASE, ANT_TIP, 0.0) - r


def antenna_base(X, Y, Z):
    ax = (ANT_TIP - ANT_BASE) / np.linalg.norm(ANT_TIP - ANT_BASE)
    wx, wy, wz = X - ANT_BASE[0], Y - ANT_BASE[1], Z - ANT_BASE[2]
    h = wx * ax[0] + wy * ax[1] + wz * ax[2]
    rad = np.sqrt(np.maximum(wx * wx + wy * wy + wz * wz - h * h, 0))
    nut = np.maximum(rad - 0.011, np.abs(h - 0.006) - 0.008)
    return np.maximum(nut, -B.shell(X, Y, Z) - 0.004)


# ======================================================================================
# Exhaust tips and muffler
EXH_TIPS = ((0.018, 0.325), (-0.046, 0.325))     # twin tips under the bumper centre (y, z)


def exhaust(X, Y, Z):
    d = np.full(np.shape(X), 1.0)
    for ty, tz in EXH_TIPS:
        tip = np.sqrt((Y - ty) ** 2 + (Z - tz) ** 2)
        d = np.minimum(d, np.maximum(np.abs(tip - 0.027) - 0.0018, np.maximum(X + 2.075, -1.66 - X)))
    # silencer tucked up under the engine, ahead of the rear valance
    muff = rbox3(X, Y, Z, (-1.56, 0, 0.31), (0.11, 0.30, 0.06), 0.05)
    return np.minimum(d, muff)


# ======================================================================================
# Door pull (small black recess pull below the strip near the rear of the door)
def door_handle(X, Y, Z, side=1):
    yy = Y * side
    zc = B.z_crease(X) - 0.040
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


DEL_YC, DEL_ZC, DEL_HU, DEL_HV = 0.495, 0.488, 0.0735, 0.055     # 0.45 m wide, 55 mm tall on the left


def bumper_letters(X, Y, Z):
    H = DEL_HV
    u = (-(Y - DEL_YC)) / DEL_HU + DEL_W / 2         # reads left->right when seen from behind
    v = (Z - DEL_ZC) / H
    d = np.full(np.shape(X), 1.0)
    for adds, subs in DEL_GLYPHS:
        g = np.full(np.shape(X), 1.0)
        for cx, cy, hx, hy in adds:
            g = np.minimum(g, _rbox2(u - cx, v - cy, hx, hy, 0.09))
        for cx, cy, hx, hy in subs:
            g = np.maximum(g, -_rbox2(u - cx, v - cy, hx, hy, 0.04))
        d = np.minimum(d, g)
    d = d * min(DEL_HU, DEL_HV)
    xb = B.x_rbump(np.abs(Y))
    slab = np.maximum((xb - 0.0025) - X, X - (xb + 0.004))
    return smax(d, slab, 0.0006)
