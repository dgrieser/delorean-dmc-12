"""DMC-12 outer body SDF and panel regions.

Frame: X forward, Y left, Z up, metres. Ground z=0, X=0 at mid wheelbase.
Published figures used: length 4216 mm (166 in), wheelbase 2413 mm (95 in),
height 1140 mm, width 1857 mm, track 1590/1588 mm.

Lines and proportions are measured from the studio reference set (ref/studio): the eight photos
were calibrated together (a bundle adjustment on the wheel centres plus ~25 body landmarks such as
lamp corners, markers, the antenna base and the windscreen corners), and the profiles below were
read off the calibrated side view and back-projected from the three-quarter views. Notable
results: the windscreen is raked at ~21 degrees with its top corners at mid-wheelbase, the
beltline sits at ~0.81 m, the nose is a short wedge behind a deep bumper, and the flanks taper
in plan towards both ends.

Stance: the reference car sits lower than a stock US car, on low-profile tyres (wheel centres
0.271 / 0.298 m above the ground). The body is modelled in its stock frame; the wheel centres
(and the arches around them) sit at R_F / R_R in that frame, and assemble.py lowers the whole
car by STANCE so the tyres stand on z = 0.
"""
import numpy as np
from sdf import smin, smax, interp, cubic_interp, cyl_y, poly2d, box, smoothstep

DEG = np.pi / 180
X_FA, X_RA = 1.2065, -1.2065
STANCE = 0.06
R_F, R_R = 0.271 + STANCE, 0.298 + STANCE    # wheel-centre heights in the body frame (photo hubs + stance)
# wheel arches: wider than tall, as on the reference car (measured on the calibrated side view):
# circles centred a few cm below the hubs, the tyres nearly filling them at the top
ARCH_F, ARCH_R = 0.331, 0.369
ARCH_ZF, ARCH_ZR = R_F - 0.043, R_R - 0.049                # arch centre heights (body frame)
ARCH_LIP = 0.025               # the stainless turns in this far round the arch; black liners beyond
SILL_Z = 0.307                 # lower edge of the stainless along the sills (black rocker below)
TRACK_F, TRACK_R = 1.590, 1.588


# ---- longitudinal control functions -------------------------------------------------
def z_crease(X):
    return interp(X, [-2.2, -1.2, 0.0, 0.9, 1.5, 2.2], [0.575, 0.580, 0.572, 0.560, 0.545, 0.530])


# half-width at the crease: widest over the rear wheels, tapering in plan towards both ends
# (side markers sit at |y| 0.86-0.90 just ahead of / behind the arches)
_WC_X = [-2.16, -2.02, -1.88, -1.70, -1.55, -1.40, -1.20, -0.90, 0.00, 0.90, 1.25, 1.50, 1.62, 1.80, 1.95, 2.12]
_WC_W = [0.740, 0.822, 0.853, 0.882, 0.905, 0.928, 0.935, 0.927, 0.920, 0.916, 0.912, 0.902, 0.893, 0.862, 0.822, 0.760]


def w_crease(X):
    return cubic_interp(X, _WC_X, _WC_W)


TUCK = 9 * DEG
LEAN_UP = 21 * DEG          # nominal tumblehome above the crease (see lean_up for the measured run)
CONVEX = 0.25               # the upper flank rolls in towards the beltline (m^-1)


def lean_up(X):
    """Upper-flank lean: ~17.5 deg on the doors (beltline at 0.81 m), more on the wings."""
    return interp(X, [-2.1, -1.0, -0.72, 0.62, 1.2, 2.1], [24.0, 22.0, 17.5, 17.5, 23.0, 25.0]) * DEG


# lower-body top: rear deck, cowl and bonnet (centreline; crown() drops it towards the sides)
_TOP_X = [-2.10, -2.06, -2.03, -1.99, -1.94, -1.88, -1.50, -1.00, -0.75, 0.0, 0.50, 0.70, 0.80, 0.97, 1.16, 1.39, 1.63, 1.80, 1.87, 1.93, 2.00]
_TOP_Z = [0.640, 0.735, 0.790, 0.838, 0.866, 0.882, 0.886, 0.876, 0.862, 0.855, 0.857, 0.858, 0.840, 0.821, 0.802, 0.775, 0.747, 0.725, 0.713, 0.697, 0.672]


def z_top_c(X):
    return cubic_interp(X, _TOP_X, _TOP_Z)


def crown(X, yy):
    # the bonnet and wings are well domed across at the scuttle (antenna base, calibrated views)
    # and flatten towards the nose, whose brow stays level over the lamps (bonnet-corner landmarks
    # at X 1.932: 5 mm below the centreline)
    k = interp(X, [-2.2, 0.45, 0.75, 1.30, 1.93], [0.010, 0.010, 0.050, 0.040, 0.008])
    return k * (yy / 0.85) ** 2


# The nose panel's top carries the bonnet line on forward from the bonnet's split to a rounded
# brow over the lamps and grille; the brow curves back towards the corners (top view and the
# calibrated bonnet corners: X 2.000 on the centreline, 1.932 at |y| 0.736). Below it the face
# leans out a little down to the bumper.
NOSE_EDGE = (2.000, 0.068)


def x_nose(Z, yy=0.0):
    # The lamp plane stays nearly upright, but the outer cheeks rake forward towards the
    # bumper: side photo 07 puts the cheek at X 1.93 / 2.00, Z 0.68 / 0.55.
    rake = 0.12 + 0.48 * smoothstep(0.70, 0.79, yy)
    # Carry the rounded cheek forward below the brow. The plan fillet otherwise pulls
    # this surface back, exposing the centre of the brow as a hook in the side silhouette.
    cheek = smoothstep(0.66, 0.75, yy) * cubic_interp(
        Z, [0.54, 0.60, 0.65, 0.68], [0.030, 0.040, 0.045, 0.0])
    face = NOSE_EDGE[0] - NOSE_EDGE[1] * (yy / 0.736) ** 2 + (0.672 - np.maximum(Z, 0.540)) * rake + cheek
    # The fascia turns forward below the sealed beams into a continuous ledge above
    # the bumper (studio 01/04). Keep the cheeks' measured rake above this return.
    lip = smoothstep(0.595, 0.540, Z) * smoothstep(0.518, 0.533, Z)
    edge = x_fbump(yy) - 0.012 + 0.015 * smoothstep(0.66, 0.78, yy)
    return face + (edge - face) * lip


def x_tail(Z):
    return -2.022 - (0.80 - Z) * 0.05


CORNER_R = 0.016             # the flanks meet the tail in a crisp vertical crease
NOSE_CORNER_R = 0.08         # the nose panel wraps round its corners without a fold (front photo)


def corner_r(X):
    return CORNER_R + (NOSE_CORNER_R - CORNER_R) * smoothstep(1.0, 1.5, X)


def front_lower_edge(X, yy):
    """Continuous wing/valance joint measured in side view 07 (body-frame metres).

    It rises from the wheel to the bumper, then wraps into the lower, level front strip.
    Both the steel and the air dam use this edge so their corner cannot develop a step.
    """
    side = interp(X, [1.50, 1.815, 2.07], [0.322, 0.387, 0.421])
    return side - 0.024 * smoothstep(0.65, 0.0, yy) * smoothstep(1.82, 2.04, X)


def z_bot(X, yy=None):
    """Lower edge of the stainless skin: the sills, rising under the nose and behind the rear wheels.
    At the tail only the middle carries a stainless strip below the bumper; the corners end behind it
    (the black valance wraps round them)."""
    z = interp(X, [-2.12, -1.87, -1.56, 1.35, 1.50], [0.345, 0.350, 0.250, 0.272, 0.322])
    z = np.where(X >= 1.50, front_lower_edge(X, 0.0 if yy is None else yy), z)
    if yy is None:
        return z
    corner = smoothstep(0.66, 0.74, yy) * smoothstep(-1.80, -1.90, X)
    return z + (RB_Z[0] + 0.012 - z) * corner


# ---- greenhouse ------------------------------------------------------------------------
WS_B = np.array([0.700, 0.858])            # windscreen base on the centreline
WS_T = np.array([0.000, 1.126])            # top edge reaches the roof at mid-wheelbase (~21 deg rake)
_ws_dir = WS_T - WS_B
WS_N = np.array([_ws_dir[1], -_ws_dir[0]])
if WS_N[1] < 0:
    WS_N = -WS_N
WS_N = WS_N / np.linalg.norm(WS_N)          # (+x, +z) outward
WS_WRAP = 0.15
GS_Y0, GS_Z0 = 0.790, 0.850
GS_LEAN = 50 * DEG
# behind the doors the side glass / sail surface twists (top view): the quarter lights stand more
# upright towards the tail and their top edges run almost parallel to the car, while the beltline
# tapers in; near the tail the sails flare out to the tail-lamp corners
_GS_X = [-2.30, -1.95, -1.80, -1.59, -1.40, -1.17, -0.92, -0.60, 2.30]
_GS_Y = [0.840, 0.790, 0.748, 0.719, 0.734, 0.751, 0.764, 0.790, 0.790]
_GS_L = [34.0, 34.0, 34.5, 36.3, 38.3, 40.8, 43.3, 50.0, 50.0]


def gs_y0(X):
    return cubic_interp(X, _GS_X, _GS_Y)


def gs_lean(X):
    return cubic_interp(X, _GS_X, _GS_L) * DEG
ROOF_Z, ROOF_K = 1.135, 0.11

# fastback / engine-cover centreline (from the side photo), meeting the roof behind the doors
FB_X = [-0.50, -0.62, -0.72, -0.84, -0.94, -1.13, -1.32, -1.46, -1.60, -1.70, -1.84, -1.96]
FB_ZS = [1.135, 1.133, 1.127, 1.113, 1.093, 1.050, 1.013, 0.984, 0.955, 0.932, 0.896, 0.866]
FB_R1 = np.array([FB_X[0], FB_ZS[0]])
FB_R2 = np.array([FB_X[-1], FB_ZS[-1]])


def z_fb(X):
    return cubic_interp(X, FB_X[::-1], FB_ZS[::-1])


def d_windshield(X, yy, Z):
    Xe = X + WS_WRAP * yy ** 2
    return (Xe - WS_B[0]) * WS_N[0] + (Z - WS_B[1]) * WS_N[1]


def d_roof(X, yy, Z):
    return Z - (ROOF_Z - ROOF_K * yy ** 2)


def d_glass_side(X, yy, Z):
    a = gs_lean(X)
    return (yy - gs_y0(X)) * np.cos(a) + (Z - GS_Z0) * np.sin(a)


def d_fastback(X, yy, Z):
    return (Z - z_fb(X)) * 0.97


def cabin_top(X, Y, Z):
    """Roof, windscreen and fastback (unbounded below; the flanks trim it)."""
    yy = np.abs(Y)
    d = smax(d_roof(X, yy, Z), d_windshield(X, yy, Z), 0.05)
    d = smax(d, d_fastback(X, yy, Z), 0.03)
    return smax(d, -1.93 - X, 0.04)          # the engine cover ends at the tail lip; the deck rounds over


def greenhouse(X, Y, Z):
    yy = np.abs(Y)
    d = smax(cabin_top(X, Y, Z), d_glass_side(X, yy, Z), 0.02)
    d = smax(d, 0.78 - Z, 0.01)
    return smax(d, x_tail(Z) - X, 0.01)


def pillar_x(Z):
    """X of the A-pillar edge (windshield ∩ side glass) at height Z, and its half-width."""
    yy = GS_Y0 - (Z - GS_Z0) * np.tan(GS_LEAN)
    Xe = WS_B[0] - (Z - WS_B[1]) * WS_N[1] / WS_N[0]
    return Xe - WS_WRAP * yy ** 2, yy


def cpillar_edge(X):
    """(yy, z) of the fastback ∩ side-glass edge at X."""
    z = z_fb(X)
    yy = gs_y0(X) - (z - GS_Z0) * np.tan(gs_lean(X))
    return yy, z


# ---- body ------------------------------------------------------------------------------
FLARE_F, FLARE_R = 0.022, 0.020        # wheel-arch flares: the flank bulges out over each wheel (top view)


def arch_flare(X, Z):
    """Outward bulge of the flank round the wheel arches: full height at the arch lip, gone
    ~12 cm out, and fading out below the hub line (where the flank tucks under)."""
    out = np.zeros(np.shape(X))
    for cx, cz, r, a in ((X_FA, ARCH_ZF, ARCH_F, FLARE_F), (X_RA, ARCH_ZR, ARCH_R, FLARE_R)):
        d = np.sqrt((X - cx) ** 2 + (Z - cz) ** 2) - r
        t = np.clip(1 - d / 0.13, 0, 1)
        out = np.maximum(out, a * t * t * (3 - 2 * t) * np.clip((Z - cz + 0.05) / 0.15, 0, 1))
    return out


def flanks(X, Y, Z):
    """Crease line, tumblehome above it, tuck-under below it, and the side-glass plane on top."""
    # Carry the fascia's lower ledge around the cheeks to the flank seam. The
    # rounded return is above the bumper, not a second strip attached to it.
    nose_lip = (0.010 * smoothstep(1.815, 1.850, X)
                * smoothstep(0.568, 0.543, Z) * smoothstep(0.520, 0.534, Z))
    yy = np.abs(Y) - arch_flare(X, Z) - nose_lip
    zc, wc, a = z_crease(X), w_crease(X), lean_up(X)
    t = np.maximum(Z - zc, 0.0)
    d_su = (yy - (wc - t * np.tan(a) - CONVEX * t * t)) * np.cos(a)
    d_sl = (yy - wc) * np.cos(TUCK) - (Z - zc) * np.sin(TUCK)
    d = smax(d_su, d_sl, 0.005)
    return smax(d, d_glass_side(X, yy, Z), 0.010)          # beltline


def lower_body(X, Y, Z):
    """Kept for the parts that clip against the old lower body: flanks + deck/bonnet top + ends."""
    yy = np.abs(Y)
    d = smax(flanks(X, Y, Z), (X - x_nose(Z, yy)) * 0.985, corner_r(X))
    d = smax(d, (x_tail(Z) - X) * 0.999, CORNER_R)
    d = smax(d, (Z - (z_top_c(X) - crown(X, yy))) * 0.994, 0.009)
    return smax(d, z_bot(X, yy) - Z, 0.015)


def body_solid(X, Y, Z):
    yy = np.abs(Y)
    plan = smax(flanks(X, Y, Z), (X - x_nose(Z, yy)) * 0.985, corner_r(X))
    plan = smax(plan, (x_tail(Z) - X) * 0.999, CORNER_R)
    top = smin((Z - (z_top_c(X) - crown(X, yy))) * 0.994, cabin_top(X, Y, Z), 0.012)
    # the nose panel's brow over the lamps is rolled a little rounder than the shoulders
    d = smax(plan, top, 0.009 + 0.031 * smoothstep(1.88, 1.93, X))
    return smax(d, z_bot(X, yy) - Z, 0.015)


# ---- arches ------------------------------------------------------------------------------
def arch_cyl(X, Y, Z, grow=0.0):
    a = np.minimum(cyl_y(X, Y, Z, X_FA, ARCH_ZF, ARCH_F + grow), cyl_y(X, Y, Z, X_RA, ARCH_ZR, ARCH_R + grow))
    return np.maximum(a, 0.55 - np.abs(Y))


# ---- recessed features in the shell -----------------------------------------------------
# quad 4x6 in. sealed beams and the grille share one black band in the nose (lens rims at
# |y| 0.365-0.523 and 0.547-0.705, 0.558-0.656 m high; the pockets are 6 mm larger)
HL_Z = (0.552, 0.662)
HL_Y = [(0.359, 0.529), (0.541, 0.711)]
GRILLE_Y = 0.351
TL_Z = (0.648, 0.806)          # black tail panel band (lens grid 0.658-0.796)
TL_Y = 0.742                   # its half-width at the bottom; the outer ends lean in towards the top
TL_Y_TOP = 0.688


def x_lamp(Z, yy=0.0):
    """Face of the lamp/grille band: near-vertical, tucked under the nose panel's brow and curving
    back with it, so the outer lamps stay recessed in the skin (calibrated inner lamp corners at
    X 1.962)."""
    return 1.978 - 0.045 * (yy / 0.7) ** 2 - (Z - 0.607) * 0.15


def _rbox2(u, v, hu, hv, r):
    qu = np.abs(u) - hu + r
    qv = np.abs(v) - hv + r
    return np.sqrt(np.maximum(qu, 0) ** 2 + np.maximum(qv, 0) ** 2) + np.minimum(np.maximum(qu, qv), 0) - r


def x_pocket_end(Z):
    """Outer edge of the opening: a narrow surround beyond the lamps, almost upright
    in the front photo. It joins the lower ledge without a triangular scoop."""
    return 0.730 + (0.607 - Z) * 0.08


def nose_recesses(X, Y, Z):
    """One pocket for the lamps and grille in the nose (negative inside the pocket). Its top is the
    lamps' rim line: the brow comes down onto the lamps with no slot above them. At the ends the
    opening runs on past the outer lamps into the corners' wrap: the panel has no forward face
    beside them."""
    yy = np.abs(Y)
    top = HL_Z[1] - 0.004
    zc = 0.5 * (HL_Z[0] + top)
    hz = 0.5 * (top - HL_Z[0])
    d = _rbox2(Y, Z - zc, x_pocket_end(Z), hz, 0.010)
    depth = X - (x_lamp(Z, yy) - 0.06)          # deep enough for the sealed beams' bowls (4.8 cm)
    return np.maximum(d, -depth)


def tail_band(Y, Z, grow=0.0):
    """2D outline of the black tail panel (lamps + plate) in the y-z plane of the tail face."""
    zc = 0.5 * (TL_Z[0] + TL_Z[1])
    hz = 0.5 * (TL_Z[1] - TL_Z[0])
    s = (Z - TL_Z[0]) / (TL_Z[1] - TL_Z[0])
    half = TL_Y + (TL_Y_TOP - TL_Y) * np.clip(s, 0, 1)
    return _rbox2(Y, Z - zc, half + grow, hz + grow, 0.018 + grow)


def tail_recess(X, Y, Z):
    r = tail_band(Y, Z)
    depth = (x_tail(Z) + 0.03) - X
    return np.maximum(r, -depth)


BV_X, BV_Z, BV_HZ, BV_HU = -0.836, 0.943, 0.129, 0.036


def bpillar_vents(X, Y, Z):
    """Vertical intake slot behind each door on the rear-quarter sail."""
    yy = np.abs(Y)
    u = X - BV_X + (Z - BV_Z) * 0.124
    slot = _rbox2(u, Z - BV_Z, BV_HU, BV_HZ, 0.022)
    depth = d_glass_side(X, yy, Z) + 0.03
    return np.maximum(slot, -depth)


def rear_slots(X, Y, Z):
    """Row of slots in the stainless strip between the rear bumper and the lower valance."""
    yy = np.abs(Y)
    u = np.mod(yy - 0.135 + 0.045, 0.090) - 0.045          # three slots each side of the exhaust
    slots = np.maximum(_rbox2(u, Z - RB_SLOT_Z, 0.030, 0.0055, 0.004), np.abs(yy - 0.225) - 0.125)
    return np.maximum(slots, -((x_tail(Z) + 0.012) - X))


COWL = (0.781, 0.66, 0.015)    # plenum between bonnet and windscreen: front edge (wrapped X), half-width, depth
COWL_GAP = 0.017               # from the glass's bottom edge to the plenum


def cowl_span(yy):
    """Wrapped-X centre and half-length of the plenum at yy. Its rear edge follows the glass's
    bottom edge, which comes forwards towards the pillars as the bonnet line drops with its crown,
    so the plenum narrows towards its ends."""
    rear = xe_ws_bottom(yy) + COWL_GAP
    return (rear + COWL[0]) / 2, np.maximum((COWL[0] - rear) / 2, 0.004)


def cowl_recess(X, Y, Z):
    """The cowl vent sits in a shallow plenum below the bonnet's rear edge (hidden from the front)."""
    yy = np.abs(Y)
    xc, hx = cowl_span(yy)
    r = _rbox2(X + WS_WRAP * yy ** 2 - xc, yy, hx, COWL[1], 0.004)
    return np.maximum(r, (z_top_c(X) - crown(X, yy) - COWL[2]) - Z)


def shell(X, Y, Z):
    d = body_solid(X, Y, Z)
    d = smax(d, -cowl_recess(X, Y, Z), 0.004)
    d = smax(d, -arch_cyl(X, Y, Z), 0.006)
    d = smax(d, -nose_recesses(X, Y, Z), 0.007)          # the panel rolls into the lamp opening
    d = smax(d, -tail_recess(X, Y, Z), 0.005)
    d = smax(d, -rear_slots(X, Y, Z), 0.002)
    d = smax(d, -bpillar_vents(X, Y, Z), 0.004)
    return d


BODY_BMIN = (-2.08, -0.95, 0.24)
BODY_BMAX = (2.12, 0.95, 1.16)


# ---- panel regions (negative inside) ----------------------------------------------------
HEADER_DOOR_X = float(WS_T[0]) - 0.045


def _door_poly():
    pts = [(0.405, 0.24), (0.470, 0.38), (0.557, 0.52), (0.618, 0.70), (0.640, 0.80)]
    for z in [0.86, 0.92, 0.98, 1.04]:
        x, _ = pillar_x(z)
        pts.append((float(x) - 0.028, z))
    # the roof keeps a ~5 cm header strip behind the windscreen's top edge
    pts += [(HEADER_DOOR_X, 1.085), (HEADER_DOOR_X, 1.25), (-0.712, 1.25), (-0.715, 1.06),
            (-0.745, 0.93), (-0.745, 0.80), (-0.715, 0.70), (-0.675, 0.625), (-0.400, 0.24)]
    return np.array(pts)


DOOR_POLY = _door_poly()
SPINE_Y = 0.118


def r_door(X, Y, Z, side=1):
    d = poly2d(X, Z, DOOR_POLY)
    d = np.maximum(d, SPINE_Y - side * Y)
    # never reach forward into the windshield (the outline is a 2D shape extruded across the car)
    return np.maximum(d, d_windshield(X, np.abs(Y), Z) + 0.012)


HOOD_Y = 0.735


SPLIT = (1.865, 0.040)          # the bonnet's front edge: X on the centreline, setback at its corners


def _hood_poly():
    """Bonnet: from the cowl to its split from the nose panel (three-quarter photos: X ~1.865 across
    the middle), between the shoulder seams."""
    r = 0.06

    def xf(y):
        return SPLIT[0] - SPLIT[1] * (y / HOOD_Y) ** 2

    xc = xf(HOOD_Y - r) - r
    front = [(xc + r * np.sin(a), -(HOOD_Y - r) - r * np.cos(a)) for a in np.linspace(0, np.pi / 2, 7)]
    front += [(xf(y), y) for y in np.linspace(-(HOOD_Y - r), HOOD_Y - r, 15)[1:-1]]
    front += [(xc + r * np.sin(a), (HOOD_Y - r) - r * np.cos(a)) for a in np.linspace(np.pi / 2, np.pi, 7)]
    ys = np.linspace(HOOD_Y, -HOOD_Y, 21)
    rear = [(0.80 - WS_WRAP * y * y - 0.005, y) for y in ys]
    return np.array(front + rear)


HOOD_POLY = _hood_poly()


def r_hood(X, Y, Z):
    d = poly2d(X, Y, HOOD_POLY)
    return np.maximum(d, 0.65 - Z)          # clear of the front wheel-arch tops (0.631)


LID_X0, LID_X1 = -0.915, -1.925
_LID_W = ([-1.925, -1.62, -1.39, -1.16, -0.915], [0.578, 0.550, 0.530, 0.510, 0.490])   # half-width (top view)


def _lid_poly():
    xs = np.linspace(LID_X0, LID_X1, 12)
    side = [(x, float(np.interp(x, *_LID_W))) for x in xs]
    return np.array(side + [(x, -y) for x, y in side[::-1]])


LID_POLY = _lid_poly()


def r_lid(X, Y, Z):
    d = poly2d(X, Y, LID_POLY)
    return np.maximum(d, 0.82 - Z)


# Nose and tail panels: separate pieces of a darker grade of steel (web/js/materials.js) round the
# lamps, wrapping round the corners to near-vertical seams on the flanks (side photo: X 1.815 at the
# bottom to 1.837 at the top in front, -1.827 at the back). The nose panel takes the front of the
# bonnet line ahead of the bonnet's split and ends above the front bumper; the tail panel reaches
# from the deck lip down behind the rear bumper.
NOSE_SEAM = ((0.43, 1.815), (0.68, 1.837))
TAIL_SEAM = -1.827
TAIL_TOP = 0.86


def x_nose_seam(Z):
    (z0, x0), (z1, x1) = NOSE_SEAM
    return x0 + (Z - z0) * (x1 - x0) / (z1 - z0)


def r_nose(X, Y, Z):
    # ahead of the flank seams and the bonnet's split (the split runs on into the seams)
    # Finish above the bumper: extending this skin down behind its top lets the raked
    # cheeks protrude over the bumper's face at the corners.
    d = np.maximum(x_nose_seam(Z) - X, (FB_Z[1] + 0.003) - Z)
    return np.maximum(d, -r_hood(X, Y, Z))


def r_tail(X, Y, Z):
    d = np.maximum(X - TAIL_SEAM, Z - TAIL_TOP)
    d = np.maximum(d, (RB_Z[1] - 0.02) - Z)
    return np.maximum(d, -r_lid(X, Y, Z))


_WS_G = (WS_T - WS_B) / np.linalg.norm(WS_T - WS_B)         # up the glass, in the (X, Z) plane
WS_BOT = 0.006                     # glass bottom edge over the bonnet line


def xe_ws_bottom(yy):
    """Wrapped X (X + WS_WRAP * yy^2) of the windscreen glass's bottom edge."""
    z = z_top_c(WS_B[0]) - crown(WS_B[0], yy) + WS_BOT
    return WS_B[0] - (z - WS_B[1]) * WS_N[1] / WS_N[0]


def r_windshield(X, Y, Z):
    """Windshield glass opening: inset from pillar/roof/cowl edges.

    The top and bottom limits are measured along the glass (3 cm under the roof line; at the
    bottom WS_BOT over the bonnet line, dropping with its crown towards the pillars, so the glass
    runs down to the cowl plenum as in the top view), so off the glass they stand square to it:
    cuts made with them through the layers just under the glass (trims, the skin's own edge walls)
    stay clean."""
    yy = np.abs(Y)
    ws = d_windshield(X, yy, Z)
    s = (X + WS_WRAP * yy ** 2 - WS_B[0]) * _WS_G[0] + (Z - WS_B[1]) * _WS_G[1]
    s_top = (ROOF_Z - ROOF_K * yy ** 2 - 0.03 - WS_B[1]) / _WS_G[1]
    s_bot = (z_top_c(WS_B[0]) - crown(WS_B[0], yy) + WS_BOT - WS_B[1]) / _WS_G[1]
    m = np.maximum(np.maximum(s - s_top, s_bot - s), d_glass_side(X, yy, Z) + 0.035)
    return np.maximum(m, -ws - 0.05)


def _door_glass_poly():
    pts = [(0.57, 0.824)]                    # 4 cm inside the door's front seam
    for z in [0.90, 0.97, 1.04]:
        x, _ = pillar_x(z)
        pts.append((float(x) - 0.075, z))
    x, _ = pillar_x(1.075)
    pts += [(float(x) - 0.10, 1.068), (-0.50, 1.068), (-0.585, 1.052), (-0.628, 0.99), (-0.635, 0.87), (-0.61, 0.824)]
    return np.array(pts)


DOOR_GLASS_POLY = _door_glass_poly()


def r_door_glass(X, Y, Z, side=1):
    d = poly2d(X, Z, DOOR_GLASS_POLY)
    return np.maximum(d, np.maximum(0.3 - side * Y, 0.80 - Z))


def _quarter_poly():
    xs = np.linspace(-0.925, -1.70, 9)
    top = [(x, float(cpillar_edge(x)[1]) - 0.032) for x in xs]
    return np.array(top + [(-1.765, 0.835), (-1.70, 0.812), (-0.93, 0.812)])


QUARTER_POLY = _quarter_poly()


def r_quarter(X, Y, Z):
    d = poly2d(X, Z, QUARTER_POLY)
    return np.maximum(d, 0.5 - np.abs(Y))


# ---- bumpers (grey urethane) -------------------------------------------------------------
# Deep rounded bands: their rolled top and bottom edges catch the studio light as the bright
# lines the photos show above and below them. The front one stands proud of a recessed black
# air dam; the rear one sits low on the tail over a slotted stainless strip.
FB_Z = (0.426, 0.528)          # front bumper bottom / top (a steel strip shows between the lamps and it)
FB_X_SIDE = 1.825              # the front bumper wraps round the corners back to the nose panel's seam
FB_X0 = 2.110
RB_Z = (0.390, 0.575)
RB_X_SIDE = -1.83              # back to the tail panel's seam
RB_X0 = -2.092
RB_SLOT_Z = 0.368              # centre of the slotted stainless strip under the rear bumper
TURN_Z = 0.475
TURN_Y, TURN_HY, TURN_HZ = 0.509, 0.060, 0.021    # amber lens (front view: 12 x 4 cm)
TURN_HOUSE = (0.100, 0.037)    # deep black housing round it (20 x 7.4 cm)


def _wrap(yy, y0, y1):
    t = np.clip((yy - y0) / (y1 - y0), 0, 1)
    return t * t * (3 - 2 * t)


def x_fbump(yy):
    return FB_X0 - 0.10 * (yy / 0.85) ** 2


def front_bumper(X, Y, Z):
    yy = np.abs(Y)
    wc = w_crease(X)
    zc = z_crease(X)
    xb = x_fbump(yy)
    d_front = X - xb
    # the sides run back flush with the nose panel to its seam (side photo)
    d_side = (yy - arch_flare(X, Z) - (wc + 0.006)) * np.cos(TUCK) - np.minimum(Z - zc, 0) * np.sin(TUCK)
    d_top = Z - FB_Z[1]
    # The visible side end tapers upwards towards the front, rather than forming a box.
    bottom = FB_Z[0] + 0.010 * smoothstep(1.83, 2.03, X) * smoothstep(0.60, 0.78, yy)
    d_bot = bottom - Z
    d_back = FB_X_SIDE - X
    d = smax(d_front, d_side, 0.13)
    d = smax(d, d_top, 0.018)
    d = smax(d, d_bot, 0.038)
    d = smax(d, d_back, 0.012)
    d = smax(d, -np.maximum(cyl_y(X, Y, Z, X_FA, ARCH_ZF, ARCH_F), 0.55 - yy), 0.006)
    # turn-signal pockets
    ts = _rbox2(yy - TURN_Y, Z - TURN_Z, TURN_HOUSE[0], TURN_HOUSE[1], 0.010)
    pocket = np.maximum(ts, -(X - (xb - 0.040)))
    d = smax(d, -pocket, 0.003)
    return d


def x_rbump(yy):
    return RB_X0 + 0.04 * (yy / 0.85) ** 2


def rear_bumper(X, Y, Z):
    yy = np.abs(Y)
    wc = w_crease(X)
    zc = z_crease(X)
    xb = x_rbump(yy)
    d_rear = xb - X
    d_side = (yy - arch_flare(X, Z) - (wc + 0.008)) * np.cos(TUCK) - np.minimum(Z - zc, 0) * np.sin(TUCK)
    d_top = Z - RB_Z[1]
    d_front = X - RB_X_SIDE
    d_bot = RB_Z[0] - Z
    d = smax(d_rear, d_side, 0.08)
    d = smax(d, d_top, 0.030)
    d = smax(d, d_bot, 0.035)
    d = smax(d, d_front, 0.012)
    d = smax(d, -np.maximum(cyl_y(X, Y, Z, X_RA, ARCH_ZR, ARCH_R), 0.55 - yy), 0.006)
    return d


FBUMP_BMIN = (1.76, -0.98, 0.37)
FBUMP_BMAX = (2.14, 0.98, 0.58)
RBUMP_BMIN = (-2.12, -0.99, 0.35)
RBUMP_BMAX = (-1.80, 0.99, 0.62)


def rear_valance(X, Y, Z):
    """Black lower valance across the tail, under the slotted strip, with exhaust cut-outs."""
    yy = np.abs(Y)
    xt = x_tail(Z)
    d = np.maximum((xt + 0.025) - X, X - (xt + 0.16))
    d = smax(d, yy - (w_crease(X) - 0.03), 0.06)
    # below the stainless strip in the middle; up behind the bumper round the corners
    ztop = (RB_SLOT_Z - 0.018) + (RB_Z[0] + 0.02 - (RB_SLOT_Z - 0.018)) * smoothstep(0.62, 0.72, yy)
    d = smax(d, np.maximum(Z - ztop, 0.305 - Z), 0.008)
    tip = np.sqrt((yy - 0.540) ** 2 + (Z - 0.300) ** 2) - 0.034
    return smax(d, -tip, 0.003)


RVAL_BMIN = (-2.10, -0.90, 0.22)
RVAL_BMAX = (-1.84, 0.90, 0.42)


def rocker(X, Y, Z):
    """Black sill cover under the doors, between the arches."""
    yy = np.abs(Y)
    zc = z_crease(X)
    wc = w_crease(X)
    w = wc - (zc - Z) * np.tan(TUCK) - 0.004
    d = np.maximum(yy - w, 0.62 - yy)
    d = smax(d, np.maximum(Z - SILL_Z, 0.180 - Z), 0.008)
    d = smax(d, np.maximum(X - 0.86, -1.59 - X), 0.0)
    d = smax(d, -arch_cyl(X, Y, Z, 0.0), 0.004)
    return d


ROCKER_BMIN = (-1.62, -0.95, 0.16)
ROCKER_BMAX = (0.86, 0.95, 0.33)

def front_strip(X, Y, Z):
    """Stainless strip between the front bumper and the air dam: a band set a little behind the
    bumper's face and wrapping round the corners to the bumper's ends, its rounded lower edge
    catching the light (front and three-quarter photos; behind the bumper the wing's own lower
    edge runs down to the air dam, side photo)."""
    yy = np.abs(Y)
    d = X - (x_fbump(yy) - 0.045)
    d = smax(d, yy - arch_flare(X, Z) - (w_crease(X) + 0.002), 0.08)
    bottom = front_lower_edge(X, yy)
    top = FB_Z[0] + 0.006 + 0.010 * smoothstep(1.83, 2.03, X) * smoothstep(0.60, 0.78, yy)
    d = smax(d, np.maximum(Z - top, bottom - Z), 0.008)
    return smax(d, FB_X_SIDE - 0.02 - X, 0.006)


FSTRIP_BMIN = (1.76, -0.98, 0.370)
FSTRIP_BMAX = (2.10, 0.98, 0.475)


AD_Z = (0.245, 0.400)          # air dam bottom lip / top (a stainless strip shows between it and the bumper)
AD_SLOT = (0.323, 0.041, 0.490)  # intake centre z, half height, half width (front photo: a 3.5 cm lip below it)


def x_airdam(yy, Z):
    """Recessed, concave air-dam face with a rounded chin projecting about 5 cm.

    The outer ends sweep back to the wheels; the separate upper return meets the bumper.
    """
    chin = cubic_interp(Z, [0.245, 0.260, 0.280, 0.320, 0.360, 0.400],
                        [0.048, 0.043, 0.022, 0.0, 0.0, 0.014])
    return x_fbump(yy) - 0.225 + 0.025 * smoothstep(0.55, 0.78, yy) + chin


def airdam(X, Y, Z):
    """Black lower valance / chin spoiler under the front bumper with the full-width intake slot.
    Its sides run back flush with the flanks to the front wheels, their top edge under the wing's
    lower edge, which drops towards the arch (side photo)."""
    yy = np.abs(Y)
    xb = x_airdam(yy, Z)
    d = (X - xb) * 0.6            # the face leans up to ~50 deg at the lip: keep the field a bound
    top = front_lower_edge(X, yy) + 0.012
    bot = interp(X, [1.50, 1.90], [0.232, AD_Z[0]])
    # The cheek is moulded with a shallow waist and rolled edges, not a flat wedge.
    t = np.clip((Z - bot) / np.maximum(top - bot, 0.01), 0, 1)
    waist = 0.016 * np.sin(np.pi * t) ** 2
    d = smax(d, yy - arch_flare(X, Z) - (w_crease(X) + 0.004) + waist, 0.080)
    d = smax(d, np.maximum(Z - top, bot - Z), 0.024)
    # the outer lower corners are cut away on a slant up to the wheel arches (front view)
    d = smax(d, ((yy - 0.78) * 0.12 - (Z - AD_Z[0]) * 0.115) / 0.166, 0.060)
    # A rolled upper return joins the recessed chin to the strip beneath the bumper.
    # Without it the side view sees daylight through the corner above the spoiler.
    upper = np.abs(Z - (front_lower_edge(X, yy) - 0.009)) - 0.014
    upper = smax(upper, X - (x_fbump(yy) - 0.045), 0.010)
    upper = smax(upper, yy - arch_flare(X, Z) - (w_crease(X) - 0.006), 0.020)
    d = smin(d, upper, 0.012)
    d = smax(d, 1.42 - X, 0.0)
    d = smax(d, -np.maximum(cyl_y(X, Y, Z, X_FA, ARCH_ZF, ARCH_F + 0.01), 0.55 - yy), 0.01)
    zc, hz, hy = AD_SLOT
    slot = _rbox2(Y, Z - zc, hy, hz, 0.020)
    # the intake: open through (the wire mesh and the radiator behind it are details.py parts)
    return smax(d, -np.maximum(slot, -(X - (xb - 0.12))), 0.004)


AIRDAM_BMIN = (1.40, -0.97, 0.22)
AIRDAM_BMAX = (2.10, 0.97, 0.46)
