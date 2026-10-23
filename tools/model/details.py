"""Exterior detail parts (SDF) for the DMC-12: lamps, grille, louvres, mirrors, wipers..."""
import numpy as np
from sdf import smin, smax, interp, cyl_y, poly2d, box, smoothstep
import body as B
import wordmark as W
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
    inner = _rbox2(v, w, hw - 0.0085, HL_HZ - 0.0085, 0.010)       # a thin bright edge, as on the photos
    ring = smax(outer, -inner, 0.0015)
    prof = np.maximum(u + 0.003 + 0.0025 * np.clip(-inner / 0.007, 0, 1), -u - 0.012)      # rounded crown
    return smax(ring, prof, 0.0015)


def headlight_reflector(X, Y, Z, yc, hw):
    """Rectangular sealed-beam reflector: a deep paraboloid bowl inside the lamp's rounded
    rectangle, flat round its corners."""
    u, v, w = _hl_local(X, Y, Z, yc)
    q2 = (v / (hw - 0.010)) ** 2 + (w / (HL_HZ - 0.010)) ** 2        # a smooth paraboloid, flat at the corners
    bowl = -0.014 - 0.034 * np.clip(1 - q2, 0, 1)
    d = np.abs(u - np.minimum(bowl, -0.014)) - 0.0022           # thick enough to extract without holes
    d = np.maximum(d, u + 0.012)
    return smax(d, _rbox2(v, w, hw - 0.010, HL_HZ - 0.010, 0.010), 0.002)


def headlight_bulb(X, Y, Z, yc, hw):
    """Halogen capsule with its round shield cap in front, at the bowl's focus."""
    u, v, w = _hl_local(X, Y, Z, yc)
    bulb = np.sqrt((u + 0.036) ** 2 + v * v + w * w) - 0.008
    cap = np.maximum(np.sqrt(v * v + w * w) - 0.012, np.abs(u + 0.026) - 0.002)
    return smin(bulb, cap, 0.004)


def headlight_bezel(X, Y, Z, yc, hw):
    """Black surround / back plate filling the lamp band around the lamp (the bezels of
    neighbouring lamps and the grille frame meet, so the band reads as one black panel), plus a
    black liner on the band's top wall: the header the photos show under the bonnet edge."""
    u, v, w = _hl_local(X, Y, Z, yc)
    outer = _rbox2(v, w, hw + 0.007, HL_HZ + 0.007, 0.006)
    inner = _rbox2(v, w, hw - 0.006, HL_HZ - 0.006, 0.010)
    ring = smax(outer, -inner, 0.002)
    if yc > 0.6:
        # the outer lamp's surround runs on to the opening's end beyond it (body.x_pocket_end)
        ring = np.minimum(ring, _rbox2(v - (hw + 0.035), w, 0.040, HL_HZ + 0.007, 0.006))
    ring = smax(ring, np.maximum(u + 0.004, -u - 0.034), 0.002)
    # never out through the skin: the outer lamp's surround reaches past its pocket, under the
    # brow where that curves back
    ring = np.maximum(ring, B.body_solid(X, Y, Z) + 0.002)
    head = np.maximum(np.abs(w - (HL_HZ - 0.001)) - 0.004, np.abs(v) - (hw + 0.007))
    head = np.maximum(head, np.maximum(u - 0.03, -u - 0.03))
    # kept well inside the skin: where the brow curves back over the outer lamps the pocket's top
    # wall runs out thin, and a liner flush with it pokes through
    head = np.maximum(head, B.shell(X, Y, Z) + 0.004)
    return np.minimum(ring, head)


# ======================================================================================
# Grille between the inner headlights: nine horizontal black slats, tilted down at the front, with
# rounded noses; the DMC letters sit on them. There are no side bars: the slats' ends show next to
# the inner lamps as a comb (reference photos 01, 02).
def grille_slats(X, Y, Z):
    yy = np.abs(Y)
    u = (X - B.x_lamp(Z, yy)) * np.cos(LAMP_TILT)
    zc = HL_ZC
    n = 9
    pitch = (2 * HL_HZ - 0.008) / n
    k = np.clip(np.round((Z - zc) / pitch), -(n // 2), n // 2)
    dz = Z - (zc + k * pitch)
    s = np.abs(dz + (u + 0.010) * 0.20) - 0.0040
    d = smax(s, np.maximum(u + 0.003, -u - 0.026), 0.003)
    d = smax(d, yy - (B.GRILLE_Y - 0.001), 0.0015)
    # top and bottom rails only
    frame = _rbox2(Y, Z - zc, B.GRILLE_Y - 0.001, HL_HZ + 0.007, 0.004)
    inner = np.abs(Z - zc) - (HL_HZ - 0.004)
    fr = smax(frame, -inner, 0.0015)
    fr = np.maximum(fr, np.maximum(u + 0.002, -u - 0.034))
    back = np.maximum(_rbox2(Y, Z - zc, B.GRILLE_Y + 0.004, HL_HZ, 0.006), np.abs(u + 0.028) - 0.002)
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
TURN_BEZEL = (0.073, 0.025)        # dark grey lens frame (with its two screws) inside the housing


def _turn_local(X, Y, Z):
    yy = np.abs(Y)
    xb = B.x_fbump(yy)
    return X - xb, yy - B.TURN_Y, Z - B.TURN_Z           # u: depth (0 = bumper face, - = in)


def front_turn_lens(X, Y, Z):
    """Fluted amber lens, set ~2 cm into its housing (the flutes are a normal map)."""
    u, v, w = _turn_local(X, Y, Z)
    r = _rbox2(v, w, B.TURN_HY, B.TURN_HZ, 0.004)
    face = -0.020 + 0.002 * np.clip(1 - (v / B.TURN_HY) ** 2, 0, 1)
    d = np.maximum(u - face, (face - 0.005) - u)
    return smax(d, r, 0.0015)


def front_turn_bezel(X, Y, Z):
    u, v, w = _turn_local(X, Y, Z)
    outer = _rbox2(v, w, TURN_BEZEL[0], TURN_BEZEL[1], 0.004)
    inner = _rbox2(v, w, B.TURN_HY - 0.001, B.TURN_HZ - 0.001, 0.003)
    ring = smax(outer, -inner, 0.001)
    ring = np.maximum(ring, np.maximum(u + 0.017, -u - 0.030))
    screws = np.minimum(np.sqrt((np.abs(v) - 0.067) ** 2 + w * w) - 0.003, 1.0)
    screws = np.maximum(screws, np.maximum(u + 0.0165, -u - 0.020))
    return np.minimum(ring, screws)


def front_turn_reflector(X, Y, Z):
    """Bright reflector bowl behind the lens (it shows through the amber)."""
    u, v, w = _turn_local(X, Y, Z)
    bowl = -0.026 - 0.010 * np.clip(1 - (v / B.TURN_HY) ** 2 - (w / B.TURN_HZ) ** 2, 0, 1)
    d = np.abs(u - bowl) - 0.001
    return smax(d, _rbox2(v, w, B.TURN_HY, B.TURN_HZ, 0.004), 0.001)


def front_turn_housing(X, Y, Z):
    """Deep black housing lining the bumper pocket round the indicator."""
    u, v, w = _turn_local(X, Y, Z)
    hy, hz = B.TURN_HOUSE
    outer = _rbox2(v, w, hy - 0.0005, hz - 0.0005, 0.010)
    walls = np.maximum(np.abs(outer + 0.0015) - 0.0015, np.maximum(u + 0.0005, -u - 0.040))
    back = np.maximum(outer, np.abs(u + 0.039) - 0.002)
    return np.minimum(walls, back)


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
TL_ROWS = [(0.659, 0.7025), (0.7065, 0.7505), (0.7545, 0.793)]
TL_COLS = [('Reverse', 0.286, 0.337), ('Tail', 0.342, 0.428), ('Tail', 0.432, 0.518), ('Tail', 0.522, 0.607),
           ('Turn', 0.611, 0.668), ('Turn', 0.672, 0.741)]


def tail_cell_outline(Y, Z, a, b, z0, z1, inset=0.0):
    yy = np.abs(Y)
    r = _rbox2(yy - (a+b)/2, Z - (z0+z1)/2, (b-a)/2-inset, (z1-z0)/2-inset, 0.002)
    # The outer amber cells follow the same rounded perimeter as their bezel.
    return np.maximum(r, B.tail_band(Y, Z, -0.008 - inset))


def tail_cells(X, Y, Z, kind):
    face = B.x_tail(Z)
    d = np.full(np.shape(X), 1.0)
    for k, a, b in TL_COLS:
        if k != kind:
            continue
        for z0, z1 in TL_ROWS:
            u = (np.abs(Y) - (a+b)/2) / ((b-a)/2)
            v = (Z - (z0+z1)/2) / ((z1-z0)/2)
            dome = 0.0020 * np.clip(1-u*u, 0, 1) * np.clip(1-v*v, 0, 1)
            depth = np.maximum(face + 0.012 - dome - X, X - face - 0.017)
            d = np.minimum(d, smax(tail_cell_outline(Y, Z, a, b, z0, z1), depth, 0.0008))
    return d


def tail_housing(X, Y, Z):
    """Separate recessed carriers and a central moulded licence-panel cassette."""
    face = B.x_tail(Z)
    band = B.tail_band(Y, Z, -0.003)
    back = np.maximum(band, np.maximum(face+0.042-X, X-face-0.050))
    centre = _rbox2(Y, Z-0.727, 0.276, 0.078, 0.008)
    plate = np.maximum(centre, np.maximum(face+0.025-X, X-face-0.048))
    pads = np.full(np.shape(X), 1.0)
    for y in [0.190, 0.242]:
        for z in [0.677, 0.726, 0.775]:
            pad = _rbox2(np.abs(Y)-y, Z-z, 0.023, 0.022, 0.0025)
            pads = np.minimum(pads, np.maximum(pad, np.maximum(face+0.019-X, X-face-0.030)))
    return np.minimum(back, np.minimum(plate, pads))


def tail_bezel(X, Y, Z):
    face = B.x_tail(Z)
    outline = np.maximum(B.tail_band(Y, Z, -0.003), 0.280-np.abs(Y))
    holes = np.full(np.shape(X), 1.0)
    for _, a, b in TL_COLS:
        for z0, z1 in TL_ROWS:
            holes = np.minimum(holes, tail_cell_outline(Y, Z, a, b, z0, z1, 0.0002))
    grille = np.maximum(outline, -holes)
    # Rounded, raised moulded ribs stand 8 mm ahead of the lens faces.
    # The old flush, square-edged grid disappeared against the dark lenses.
    grille = smax(grille, np.maximum(face+0.004-X, X-face-0.032), 0.0018)
    # Perimeter lip round the centre cassette; 3 mm seams separate it from both lamps.
    rim = np.maximum(_rbox2(Y, Z-0.727, 0.276, 0.079, 0.008),
                     -_rbox2(Y, Z-0.727, 0.270, 0.073, 0.005))
    rim = smax(rim, np.maximum(face+0.007-X, X-face-0.034), 0.0015)
    return np.minimum(grille, rim)


def tail_gasket(X, Y, Z):
    ring = np.maximum(B.tail_band(Y, Z, 0.002), -B.tail_band(Y, Z, -0.003))
    face = B.x_tail(Z)
    return np.maximum(ring, np.maximum(face+0.004-X, X-face-0.018))


def tail_reflectors(X, Y, Z):
    d = np.full(np.shape(X), 1.0)
    face = B.x_tail(Z)
    for _, a, b in TL_COLS:
        for z0, z1 in TL_ROWS:
            u=(np.abs(Y)-(a+b)/2)/((b-a)/2); v=(Z-(z0+z1)/2)/((z1-z0)/2)
            bowl=0.005*np.clip(1-u*u,0,1)*np.clip(1-v*v,0,1)
            d=np.minimum(d, np.maximum(tail_cell_outline(Y,Z,a,b,z0,z1,0.001),
                                      np.abs(X-face-0.030-bowl)-0.002))
    return d


PLATE_W, PLATE_H, PLATE_ZC = 0.305, 0.142, 0.729       # visible plate face within the recessed tail-panel surround


def licence_plate(X, Y, Z):
    face = B.x_tail(Z)
    d = _rbox2(Y, Z - PLATE_ZC, 0.5 * PLATE_W, 0.5 * PLATE_H, 0.008)
    return np.maximum(d, np.maximum(face + 0.014 - X, X - (face + 0.020)))


# ======================================================================================
# Engine cover: black frame + stepped louvre blades following the fastback + centre rib
LID_GAP = 0.004


def _fb_z(X):
    return B.z_fb(X)


# four stepped blades and a rear panel with two slatted grilles (top view of the reference car)
LID_BLADES = [-0.925, -1.105, -1.300, -1.484, -1.670, -1.905]      # blade front/rear edges (x)
LID_GRILLE = (-1.705, -1.860, 0.035, 0.400)                         # grilles in the last blade: x range, |y| range


def lid_frame(X, Y, Z):
    yy = np.abs(Y)
    fb = B.d_fastback(X, yy, Z)
    reg = poly2d(X, Y, B.LID_POLY) + LID_GAP / 2
    inner = poly2d(X, Y, B.LID_POLY) + 0.022
    d = smax(reg, -inner, 0.003)
    # deep enough to meet the pan below the blades, so nothing shows past the blades' ends
    d = smax(d, np.maximum(fb + 0.0005, -fb - 0.085), 0.003)
    return d


def lid_slats(X, Y, Z):
    """Five stepped blades; the last one carries two slatted grilles either side of a centre bar."""
    yy = np.abs(Y)
    inner = poly2d(X, Y, B.LID_POLY) + 0.020
    blades = np.full(np.shape(X), 1.0)
    # Each blade is a continuous solid. Selecting a blade by X made the field
    # discontinuous at every step and left sawtooth normals in the extracted mesh.
    for i, (front, xr) in enumerate(zip(LID_BLADES[:-1], LID_BLADES[1:])):
        xf = front + (0.010 if i == 0 else 0.030)
        # A shallow crown catches the broad, soft highlight visible on each blade.
        u = (X - (xf+xr)*0.5) / ((xf-xr)*0.5)
        ztop = _fb_z(xr) - 0.002 + (X - xr) * 0.05 + 0.0025*np.clip(1-u*u,0,1) + 0.0015*np.clip(1-(Y/.57)**2,0,1)
        s = smax(np.abs(Z - ztop + 0.004) - 0.004,
                 np.maximum(xr - X, X - xf), 0.003)
        rise = np.maximum(np.abs(X - (xf - 0.004)) - 0.003,
                          np.maximum(Z - ztop, (ztop - 0.008) - Z))
        blades = np.minimum(blades, np.minimum(s, rise))
    blades = smax(blades, inner, 0.006)
    gx0, gx1, gy0, gy1 = LID_GRILLE
    hole = _rbox2(X - 0.5 * (gx0 + gx1), yy - 0.5 * (gy0 + gy1), 0.5 * (gx0 - gx1), 0.5 * (gy1 - gy0), 0.006)
    zt = _fb_z(LID_BLADES[-1]) - 0.002 + (X - LID_BLADES[-1]) * 0.05
    blades = smax(blades, -np.maximum(hole, np.abs(Z - zt + 0.004) - 0.02), 0.0015)
    bars = np.maximum(hole, np.abs(np.mod(X + 0.010, 0.020) - 0.010) - 0.0028)
    bars = np.maximum(bars, np.maximum(Z - (zt - 0.003), (zt - 0.030) - Z))
    # Each grille has a narrow central cross brace and a rolled perimeter lip.
    brace = np.maximum(hole,np.abs(yy-0.5*(gy0+gy1))-.0025)
    brace = np.maximum(brace,np.maximum(Z-(zt-.006),(zt-.023)-Z))
    rim = np.maximum(np.abs(hole)-.0025,np.abs(Z-zt+.002)-.003)
    return np.minimum(blades,np.minimum(bars,np.minimum(brace,rim)))


def lid_under(X, Y, Z):
    """Narrow underside return on the frame, leaving the louvre gaps open."""
    yy = np.abs(Y)
    fb = B.d_fastback(X, yy, Z)
    inner = poly2d(X, Y, B.LID_POLY) + 0.010
    rim = np.maximum(inner,-(inner+0.012))
    d = np.maximum(np.abs(fb + 0.082) - 0.005, rim)
    # A recessed black baffle sits only under the two rear ventilation grilles.
    # It leaves the long sight lines between the louvre blades unobstructed.
    baffle = np.maximum(inner,np.maximum(X+1.705,np.abs(fb+.072)-.004))
    return np.minimum(d,baffle)


LID_HINGE = (B.LID_X0 + 0.02, float(_fb_z(B.LID_X0 + 0.02)) - 0.012)


# ======================================================================================
# Rear quarter-window inserts: four curved, swept vanes inside the rounded tail tip.
def _quarter_vent_region(X, Z):
    return np.maximum(poly2d(X, Z, B.QUARTER_POLY) + 0.004, X - B.quarter_vent_split(Z))


def quarter_vent_frame(X, Y, Z):
    gs = B.shell(X, Y, Z)
    region = _quarter_vent_region(X, Z)
    rim = np.maximum(region, -region - 0.0035)
    return smax(rim, np.maximum(gs - 0.002, -gs - 0.025), 0.001)


def quarter_vent_fins(X, Y, Z):
    gs = B.shell(X, Y, Z)
    d = np.full(np.shape(X), 1.0)
    for offset in [0.025, 0.050, 0.075, 0.100]:
        # Each vane sweeps aft as it turns inboard: thin edges from the side,
        # broad curved faces from the rear and overhead reference cameras.
        u = X - B.quarter_vent_split(Z) + offset - 0.35 * gs
        vane = smax(np.abs(u) * 0.94 - 0.0017, np.maximum(gs - 0.0015, -gs - 0.016), 0.0012)
        d = np.minimum(d, vane)
    return smax(d, _quarter_vent_region(X, Z), 0.0008)


def quarter_vent_back(X, Y, Z):
    gs = B.shell(X, Y, Z)
    return np.maximum(_quarter_vent_region(X, Z), np.abs(gs + 0.030) - 0.003)


# # B-pillar vent inserts: a black liner with a centre divider inside each slot
def bpillar_insert(X, Y, Z):
    yy = np.abs(Y)
    u = X - B.BV_X + (Z - B.BV_Z) * 0.124
    slot = _rbox2(u, Z - B.BV_Z, B.BV_HU + 0.0015, B.BV_HZ + 0.0015, 0.022)
    gs = B.d_glass_side(X, yy, Z)
    back = np.maximum(slot, np.abs(gs + 0.026) - 0.002)
    divider = np.maximum(np.maximum(slot, np.abs(u) - 0.003), np.maximum(gs + 0.026, -gs - 0.004))
    walls = np.maximum(np.maximum(slot, -(slot + 0.004)), np.maximum(gs + 0.026, -gs - 0.002))
    return np.minimum(np.minimum(back, divider), walls)


# ======================================================================================
# Mirrors: black wedge housings on the door's front-top corner, just behind the A-pillar base
# (outer-top corner measured at x 0.29, |y| 0.98, z 0.87)
# Measured on the calibrated front and top views: a rounded black housing ~18 x 10.5 x 6 cm,
# swept back ~30 deg, its inboard end on a flat triangular sail that covers the door window's
# front lower corner (no stalk).
MIRROR_P0 = np.array([0.405, 0.800])        # inboard end of the housing axis (x, |y|)
MIRROR_P1 = np.array([0.300, 0.968])        # outboard end
MIRROR_Z = (0.765, 0.870)                   # housing bottom / top
MIRROR_D = 0.060                            # housing depth (fore-aft)


def _mirror_local(X, Y, Z, side):
    Ys = Y * side
    a = MIRROR_P1 - MIRROR_P0
    L = np.linalg.norm(a)
    a = a / L
    n = np.array([a[1], -a[0]])                      # plan normal pointing forward (+x)
    if n[0] < 0:
        n = -n
    dx, dy = X - MIRROR_P0[0], Ys - MIRROR_P0[1]
    s = dx * a[0] + dy * a[1]                         # along the housing, 0 = inboard end
    t = dx * n[0] + dy * n[1]                         # fore-aft across it, + = forward
    return s, t, Z - 0.5 * (MIRROR_Z[0] + MIRROR_Z[1]), L


def mirror_housing(X, Y, Z, side=1):
    s, t, w, L = _mirror_local(X, Y, Z, side)
    hh = 0.5 * (MIRROR_Z[1] - MIRROR_Z[0])
    # rounded box; the front half rounder than the flat back that carries the glass
    head = rbox3(s, t, w, (0.5 * L, 0.0, 0.0), (0.5 * L + 0.012, 0.5 * MIRROR_D, hh), 0.020)
    nose = rbox3(s, t, w, (0.5 * L, 0.012, 0.0), (0.5 * L + 0.006, 0.5 * MIRROR_D - 0.008, hh - 0.004), 0.030)
    head = smin(head, nose, 0.006)
    cavity = rbox3(s, t, w, (0.5 * L + 0.002, -0.5 * MIRROR_D - 0.004, 0.0), (0.5 * L - 0.008, 0.010, hh - 0.013), 0.008)
    head = smax(head, -cavity, 0.002)
    # sail: a flat triangle lying on the window's front lower corner, joined to the housing's end
    Ys = Y * side
    tri = poly2d(X, Z, np.array([(0.470, 0.805), (0.370, 0.805), (0.395, 0.885)]))
    gs = B.d_glass_side(X, np.abs(Y), Z)
    sail = np.maximum(tri - 0.004, np.maximum(-gs - 0.004, gs - 0.016))
    sail = np.maximum(sail, 0.795 - Z)
    return smin(head, sail, 0.012)


def mirror_glass(X, Y, Z, side=1):
    s, t, w, L = _mirror_local(X, Y, Z, side)
    hh = 0.5 * (MIRROR_Z[1] - MIRROR_Z[0])
    return rbox3(s, t, w, (0.5 * L + 0.002, -0.5 * MIRROR_D + 0.004, 0.0), (0.5 * L - 0.012, 0.0022, hh - 0.017), 0.006)


# ======================================================================================
# Wheel-well liners and underbody
def well_liner(X, Y, Z, front=True):
    yy = np.abs(Y)
    cx, cz, r = (B.X_FA, B.ARCH_ZF, B.ARCH_F) if front else (B.X_RA, B.ARCH_ZR, B.ARCH_R)
    d = np.abs(np.sqrt((X - cx) ** 2 + (Z - cz) ** 2) - (r + 0.010)) - 0.003
    # out to just inside the stainless lip (the flanks tuck under, so follow them, not the crease)
    d = np.maximum(d, np.maximum(B.flanks(X, Y, Z) + 0.008, 0.52 - yy))
    d = np.maximum(d, (cz - 0.12) - Z)
    inner_wall = np.maximum(np.abs(yy - 0.53) - 0.003, np.sqrt((X - cx) ** 2 + (Z - cz) ** 2) - (r + 0.012))
    inner_wall = np.maximum(inner_wall, (cz - 0.12) - Z)
    return np.minimum(d, inner_wall)


def underbody(X, Y, Z):
    yy = np.abs(Y)
    # kept inside the tucked-in lower flanks so no edge shows past the sills or bumpers
    # the floor pan stops at the engine: from behind and below the engine, rear frame and running
    # gear show, as on the reference car
    # at the front it rises to just above the air dam's lip and stays clear of its swept-up corners
    zp = 0.215 + 0.040 * smoothstep(1.0, 1.5, X)
    pan = np.maximum(np.abs(Z - zp) - 0.006, np.maximum(yy - 0.76, np.maximum(X - 1.72, -0.90 - X)))
    pan = np.maximum(pan, np.minimum(yy - 0.55, 1.50 - X))
    pan = smax(pan, -B.arch_cyl(X, Y, Z, 0.02), 0.002)
    # backbone tunnel
    bb = rbox3(X, Y, Z, (0.1, 0, 0.24), (1.5, 0.11, 0.03), 0.02)
    return np.minimum(pan, bb)


# ======================================================================================
# Air-dam intake: a wire mesh across the opening and the radiator core behind it
def intake_mesh(X, Y, Z):
    zc, hz, hy = B.AD_SLOT
    xm = B.x_airdam(np.abs(Y), zc) - 0.035
    r = _rbox2(Y, Z - zc, hy + 0.004, hz + 0.004, 0.012)
    return np.maximum(r, np.abs(X - xm) - 0.0012)


def radiator(X, Y, Z):
    zc, hz, hy = B.AD_SLOT
    xm = B.x_airdam(np.abs(Y), zc) - 0.11
    r = _rbox2(Y, Z - zc, 0.345, hz + 0.010, 0.01)
    return np.maximum(r, np.abs(X - xm) - 0.012)


def intake_supports(X, Y, Z):
    """Radiator end tanks and retaining rail, visible behind the square intake mesh."""
    zc, hz, hy = B.AD_SLOT
    xm = B.x_airdam(np.abs(Y), zc) - 0.085
    uprights = np.maximum(np.abs(np.abs(Y) - 0.345) - 0.010, np.abs(Z - zc) - 0.050)
    rail = np.maximum(np.abs(Z - zc + 0.029) - 0.004, np.abs(Y) - 0.355)
    return smax(np.minimum(uprights, rail), np.abs(X - xm) - 0.007, 0.003)


# ======================================================================================
# Cowl vent: black slatted grille across the car between the bonnet and the windscreen (fore-aft
# slots, as on the reference car's top view), moulded as one piece filling the plenum, with a black
# lip that runs on up the windscreen's foot to under the glass (it all reads black in the photos)
def cowl_vent(X, Y, Z):
    yy = np.abs(Y)
    xe = X + B.WS_WRAP * yy ** 2
    xc, hx = B.cowl_span(yy)
    hy, dz = B.COWL[1], B.COWL[2]
    top = B.z_top_c(X) - B.crown(X, yy)                    # the bonnet line the plenum is sunk below
    lo, hi = top - dz - 0.004, top - 0.003
    d = np.maximum(_rbox2(xe - xc, yy, hx - 0.0015, hy - 0.002, 0.003), np.abs(Z - (lo + hi) / 2) - (hi - lo) / 2)
    u = np.mod(yy + 0.007, 0.014) - 0.007
    slot = np.maximum(np.maximum(np.abs(u) - 0.0038, np.abs(xe - xc) - (hx - 0.008)), (top - 0.010) - Z)
    d = smax(d, -slot, 0.0008)
    # the lip: a skin on the shell from just under the glass's bottom edge to the plenum
    lip = np.maximum(np.abs(B.shell(X, Y, Z) - 0.0018) - 0.0015,
                     np.maximum((B.xe_ws_bottom(yy) - 0.004) - xe, xe - (xc - hx + 0.004)))
    return np.minimum(d, np.maximum(lip, yy - hy))


# ======================================================================================
# Power antenna on the right front wing beside the windscreen (base and tip measured from the
# reference photos: it rakes back and out)
ANT_BASE = np.array([0.765, -0.795, 0.800])
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
EXH_TIPS = tuple((y, B.EXHAUST_Z) for y in B.EXHAUST_Y)


def exhaust(X, Y, Z):
    d = np.full(np.shape(X), 1.0)
    for ty, tz in EXH_TIPS:
        tip = np.sqrt((Y - ty) ** 2 + (Z - tz) ** 2)
        tube = np.maximum(np.abs(tip - 0.035) - 0.0020, np.maximum(-2.12 - X, X + 1.94))
        # Rolled outlet lip; the bore stays open rather than ending in a solid cap.
        rim = np.sqrt((tip - 0.035) ** 2 + (X + 2.116) ** 2) - 0.003
        d = np.minimum(d, np.minimum(tube, rim))
        neck = cap_x(X, Y, Z, (-1.955, ty, tz), (-1.955, ty, 0.47), 0.032)
        d = np.minimum(d, neck)
    # Tucked behind the bumper, clear of the crankcase and sump. The former low
    # box intersected the engine and hid it from the photographed rear angle.
    muff = rbox3(X, Y, Z, (-1.96, 0, 0.49), (0.045, 0.12, 0.035), 0.03)
    return np.minimum(d, muff)


def sill_details(X, Y, Z):
    """Circular sill access plug and the small lower-trim fixings in side photo 07."""
    yy = np.abs(Y)
    face = B.w_crease(X) - (B.z_crease(X) - Z) * np.tan(B.TUCK) - 0.014
    r = np.sqrt((X + 0.283) ** 2 + (Z - 0.192) ** 2)
    plug = np.maximum(r - 0.024, np.abs(yy - face - 0.001) - 0.002)
    ring = np.sqrt((r - 0.024) ** 2 + (yy - face - 0.003) ** 2) - 0.002
    d = np.minimum(plug, ring)
    for x in [-0.76, -0.60, -0.12, 0.25, 0.66]:
        screw = np.maximum(np.sqrt((X - x) ** 2 + (Z - 0.205) ** 2) - 0.0025,
                           np.abs(yy - face - 0.002) - 0.002)
        d = np.minimum(d, screw)
    return d


def rear_slot_back(X, Y, Z):
    """Dark recess behind the six slots in the lower stainless band."""
    yy = np.abs(Y)
    u = np.mod(yy - 0.135 + 0.045, 0.090) - 0.045
    slots = np.maximum(_rbox2(u, Z - B.RB_SLOT_Z, 0.029, 0.0048, 0.003),
                       np.abs(yy - 0.225) - 0.125)
    return np.maximum(slots, np.abs(X - B.x_rbump(yy) - 0.025) - 0.002)


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
# Recessed "DeLorean" wordmark on the rear bumper (left side)
def bumper_letters(X, Y, Z):
    """Inset letter floors; the bumper itself supplies their moulded bevels."""
    xb = B.rear_bumper_face(Y,Z)
    floor = np.abs(X-xb-(W.DEPTH-0.0004))-0.0005
    return smax(W.letters(Y,Z)+0.0010, floor, 0.0002)
