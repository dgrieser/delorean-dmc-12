"""DMC-12 wheel assemblies (turbine alloy wheel, tyre with modelled tread, vented disc,
caliper) built procedurally in Blender and exported to tools/out/wheels.glb.

Run:  blender -b -P tools/model/wheels.py  [-- --preview]

Blender frame per assembly: axle along +Y (outward for a LEFT wheel), wheel centre at the
origin, Z up, metres. After glTF export (+Y up) Blender +Y becomes glTF -Z, i.e. the
left-wheel outward direction is -Z in three.js and the spin axis is the local Z axis.
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector, Matrix

OUT_DIR = '/home/user/delorean-dmc-12/tools/out'
TAU = 2 * math.pi


# ----------------------------------------------------------------------------- helpers
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def make_mat(name, base, metallic=0.0, rough=0.5, spec=0.5):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get('Principled BSDF')
    p.inputs['Base Color'].default_value = (*base, 1.0)
    p.inputs['Metallic'].default_value = metallic
    p.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in p.inputs:
        p.inputs['Specular IOR Level'].default_value = spec
    m.diffuse_color = (*base, 1.0)
    m.use_backface_culling = False
    return m


def mats():
    return {
        'rubber': make_mat('Tyre_Rubber', (0.02, 0.02, 0.02), 0.0, 0.85),
        'alloy': make_mat('Wheel_Alloy', (0.85, 0.85, 0.86), 1.0, 0.25),
        'dark': make_mat('Wheel_SlotDark', (0.035, 0.036, 0.04), 0.3, 0.6),
        'disc': make_mat('Brake_Disc', (0.55, 0.55, 0.56), 1.0, 0.45),
        'caliper': make_mat('Brake_Caliper', (0.04, 0.04, 0.045), 0.2, 0.5),
        'chrome': make_mat('Lug_Chrome', (0.9, 0.9, 0.92), 1.0, 0.15),
    }


def obj_from_bm(name, bm, materials, smooth_angle=35.0, parent=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for m in materials:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = True
    me.use_auto_smooth = True
    me.auto_smooth_angle = math.radians(smooth_angle)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    if parent is not None:
        ob.parent = parent
    return ob


def catmull(points, n_per):
    """Catmull-Rom through 2D points, returns dense list (open curve)."""
    P = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = (Vector(P[i - 1]), Vector(P[i]), Vector(P[i + 1]), Vector(P[i + 2]))
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            v = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3)
            out.append((v.x, v.y))
    out.append(tuple(points[-1]))
    return out


def lathe_into(bm, uv, prof, segs, mat_idx=None, closed=False, a0=0.0, a1=TAU, caps=False, flip=False):
    """Revolve profile [(r, y)] about the Y axis. Full revolution shares vertices across the
    seam (UVs are per-loop so u wraps to 1.0). mat_idx: per-segment material indices."""
    full = abs((a1 - a0) - TAU) < 1e-9
    ncol = segs if full else segs + 1
    rows = []
    for j, (r, y) in enumerate(prof):
        row = []
        for i in range(ncol):
            a = a0 + (a1 - a0) * i / segs
            row.append(bm.verts.new((r * math.cos(a), y, r * math.sin(a))))
        rows.append(row)
    # cumulative profile length for v
    L = [0.0]
    np_ = len(prof) + (1 if closed else 0)
    for j in range(1, np_):
        a, b = prof[(j - 1) % len(prof)], prof[j % len(prof)]
        L.append(L[-1] + math.hypot(a[0] - b[0], a[1] - b[1]))
    tot = L[-1] or 1.0
    nseg_prof = len(prof) if closed else len(prof) - 1
    faces = []
    for j in range(nseg_prof):
        j2 = (j + 1) % len(prof)
        for i in range(segs):
            i2 = (i + 1) % ncol if full else i + 1
            q = [rows[j][i], rows[j][i2], rows[j2][i2], rows[j2][i]]
            if flip:
                q = q[::-1]
            try:
                f = bm.faces.new(q)
            except ValueError:
                continue
            if mat_idx is not None:
                f.material_index = mat_idx[j] if isinstance(mat_idx, (list, tuple)) else mat_idx
            uvs = [(i / segs, L[j] / tot), ((i + 1) / segs, L[j] / tot),
                   ((i + 1) / segs, L[j + 1] / tot), (i / segs, L[j + 1] / tot)]
            if flip:
                uvs = uvs[::-1]
            for loop, t in zip(f.loops, uvs):
                loop[uv].uv = t
            faces.append(f)
    if caps and not full and closed:
        for i in (0, ncol - 1):
            vs = [rows[j][i] for j in range(len(prof))]
            if i == 0:
                vs = vs[::-1]
            try:
                f = bm.faces.new(vs)
                if mat_idx is not None:
                    f.material_index = mat_idx[0] if isinstance(mat_idx, (list, tuple)) else mat_idx
            except ValueError:
                pass
    return rows


def evaluated_copy(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = bpy.data.meshes.new_from_object(ev)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)


def apply_boolean(ob, cutter, material_transfer=True):
    mod = ob.modifiers.new('bool', 'BOOLEAN')
    mod.operation = 'DIFFERENCE'
    mod.solver = 'EXACT'
    mod.object = cutter
    if material_transfer and hasattr(mod, 'material_mode'):
        mod.material_mode = 'TRANSFER'
    evaluated_copy(ob)


def apply_bevel(ob, width, segs=2, angle=40.0):
    mod = ob.modifiers.new('bev', 'BEVEL')
    mod.width = width
    mod.segments = segs
    mod.limit_method = 'ANGLE'
    mod.angle_limit = math.radians(angle)
    mod.harden_normals = True
    mod.miter_outer = 'MITER_ARC'
    evaluated_copy(ob)


# ----------------------------------------------------------------------------- wheel spec
SPEC = {
    'F': dict(R=0.2950, W=0.195, rim_r=0.3556 / 2, rim_w=0.1524, tread_w=0.150, pitches=68),
    'R': dict(R=0.3315, W=0.235, rim_r=0.3810 / 2, rim_w=0.2032, tread_w=0.186, pitches=74),
}


def rim_geometry(s):
    """Key rim dimensions (all y measured outward from the tyre mid-plane)."""
    rb = s['rim_r']
    yi = s['rim_w'] / 2            # flange inner face
    yo = yi + 0.0062               # flange outer face
    rf = rb + 0.0178               # flange top radius
    return rb, yi, yo, rf


# ----------------------------------------------------------------------------- tyre
def build_tyre(tag, s, M, parent):
    R, W, tw = s['R'], s['W'], s['tread_w']
    rb, yi, yo, rf = rim_geometry(s)
    d = 0.0082                      # tread depth
    hw, ht = W / 2, tw / 2
    segs = 144

    def r_top(y):
        a = abs(y) / ht
        r = R - 0.0045 * a * a
        edge = ht - 0.014
        if abs(y) > edge:
            t = (abs(y) - edge) / (ht + 0.003 - edge)
            r -= (d + 0.0005) * (t ** 1.8) - 0.0005 * t
        return r

    def r_carc(y):
        return r_top(y) - d if abs(y) < ht - 0.001 else r_top(y) - d

    # carcass half profile from bead (inside rim) to tread centre, then mirror
    rm = rb + 0.42 * (R - rb)
    side = [
        (rb + 0.003, yi - 0.004),
        (rf - 0.004, yi + 0.0005),
        (rf + 0.0012, yo - 0.0016),
        (rf + 0.0050, yo + 0.0022),
        (rf + 0.0085, yo + 0.0050),        # rim protector ridge
        (rf + 0.0120, yo + 0.0046),
        (rm - 0.020, hw - 0.0035),
        (rm, hw),
        (rm + 0.028, hw - 0.0030),
        (R - 0.034, hw - 0.0105),
        (R - 0.018, ht + 0.0105),
        (r_top(ht + 0.003) - 0.0004, ht + 0.0030),
    ]
    half = catmull(side, 3)
    ys = [ht - 0.003 - k * (ht - 0.003) / 5 for k in range(1, 6)]
    half += [(r_carc(y) - 0.0004, y) for y in ys]          # under-tread, y -> 0
    # full profile: inner (-y) side reversed to outer (+y) side
    prof = [(r, -y) for (r, y) in half] + [(r, y) for (r, y) in reversed(half[:-1])]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    lathe_into(bm, uv, prof, segs, 0, flip=True)

    # ---- tread blocks
    P = s['pitches']
    pitch = TAU / P
    g1 = 0.145 * ht      # centre groove half-offset from the mid-plane edge of centre rib
    ribs = []
    # (y0, y1, kind)  kinds: 'centre' continuous with sipes, 'mid' skewed blocks, 'shoulder'
    c_half = 0.115 * ht
    gw1, gw2 = 0.0085, 0.0080
    m0 = c_half + gw1
    m1 = 0.62 * ht
    s0 = m1 + gw2
    s1 = ht + 0.003
    ribs = [(-c_half, c_half, 'centre', 0.0),
            (m0, m1, 'mid', 0.0), (-m1, -m0, 'mid', 0.5),
            (s0, s1, 'shoulder', 0.25), (-s1, -s0, 'shoulder', 0.75)]

    def add_block(ya, yb, ua_fn, ub_fn, nu, nv, depth_scale=1.0):
        grid = []
        for jv in range(nv + 1):
            y = ya + (yb - ya) * jv / nv
            ua, ub = ua_fn(y), ub_fn(y)
            row = []
            for iu in range(nu + 1):
                a = ua + (ub - ua) * iu / nu
                rt = r_top(y)
                rb_ = r_carc(y) - 0.0012
                if depth_scale < 1.0:
                    rb_ = rt - (rt - rb_) * depth_scale
                top = bm.verts.new((rt * math.cos(a), y, rt * math.sin(a)))
                bot = bm.verts.new((rb_ * math.cos(a), y, rb_ * math.sin(a)))
                row.append((top, bot, a, y))
            grid.append(row)

        def face(vs, uvs):
            try:
                f = bm.faces.new(vs)
            except ValueError:
                return
            f.material_index = 0
            for loop, t in zip(f.loops, uvs):
                loop[uv].uv = t

        def U(a):
            return (a % TAU) / TAU

        def V(y):
            return 0.5 + y / W * 0.3

        for jv in range(nv):
            for iu in range(nu):
                a = grid[jv][iu]; b = grid[jv][iu + 1]; c = grid[jv + 1][iu + 1]; e = grid[jv + 1][iu]
                face([a[0], e[0], c[0], b[0]], [(U(a[2]), V(a[3])), (U(e[2]), V(e[3])), (U(c[2]), V(c[3])), (U(b[2]), V(b[3]))])
        # walls (radial)
        def wall(p, q):
            face([p[0], q[0], q[1], p[1]], [(U(p[2]), V(p[3])), (U(q[2]), V(q[3])), (U(q[2]), V(q[3]) - 0.01), (U(p[2]), V(p[3]) - 0.01)])
        for iu in range(nu):
            wall(grid[0][iu], grid[0][iu + 1])              # y=ya side
            wall(grid[nv][iu + 1], grid[nv][iu])            # y=yb side
        for jv in range(nv):
            wall(grid[jv + 1][0], grid[jv][0])              # leading
            wall(grid[jv][nu], grid[jv + 1][nu])            # trailing

    for (ya, yb, kind, phase) in ribs:
        nv = max(2, int(math.ceil((yb - ya) / 0.010)))
        if kind == 'centre':
            # continuous rib split into pitch segments separated by thin shallow sipes
            for k in range(P):
                a0 = k * pitch
                add_block(ya, yb, lambda y, a0=a0: a0 + 0.0015, lambda y, a0=a0: a0 + pitch - 0.0015, 1, nv,
                          depth_scale=0.35 if True else 1.0)
        elif kind == 'mid':
            sk = 1.2 if ya > 0 else -1.2      # skewed lateral grooves (radians per metre of y)
            gap = 0.0042 / R
            for k in range(P):
                a0 = (k + phase) * pitch
                add_block(ya, yb, lambda y, a0=a0: a0 + sk * (y - ya), lambda y, a0=a0: a0 + pitch - gap + sk * (y - ya), 1, nv)
        else:
            gap = 0.0055 / R
            for k in range(P):
                a0 = (k + phase) * pitch
                add_block(ya, yb, lambda y, a0=a0: a0, lambda y, a0=a0: a0 + pitch - gap, 1, nv)

    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    ob = obj_from_bm(f'Tyre_{tag}', bm, [M['rubber']], smooth_angle=30.0, parent=parent)
    return ob


# ----------------------------------------------------------------------------- rim + face
def build_rim(tag, s, M, parent):
    rb, yi, yo, rf = rim_geometry(s)
    t = 0.0048          # barrel wall thickness
    well = rb - 0.022
    prof = [
        # outer polished lip (outer face of outboard flange) going over the curl
        (rf - 0.0125, yo - 0.0015), (rf - 0.0105, yo), (rf - 0.006, yo + 0.0004), (rf - 0.0015, yo - 0.0004), (rf + 0.0002, yo - 0.0030),
        (rf - 0.0010, yi + 0.0006), (rf - 0.0070, yi), (rb + 0.0010, yi - 0.0004),
        (rb, yi - 0.0080), (rb + 0.0010, yi - 0.0150),            # bead hump
        (rb, yi - 0.0260), (well, yi - 0.040), (well, -yi + 0.040), (rb, -yi + 0.026),
        (rb + 0.0010, -yi + 0.0150), (rb, -yi + 0.0080),
        (rb + 0.0010, -yi + 0.0004), (rf - 0.0070, -yi), (rf - 0.0010, -yi - 0.0006),
        (rf + 0.0002, -yo + 0.0030), (rf - 0.0015, -yo + 0.0004), (rf - 0.006, -yo - 0.0004), (rb - 0.002, -yo),
        # barrel inside surface back to the outboard side
        (rb - t, -yi + 0.004), (well - t, -yi + 0.040), (well - t, yi - 0.040), (rb - t, yi - 0.026), (rb - t, yo - 0.006),
    ]
    # materials: lip+tyre-side alloy, inner barrel dark
    n = len(prof)
    mi = [0] * n
    for j in range(21, n):
        mi[j] = 1
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    lathe_into(bm, uv, prof, 128, mi, closed=True, flip=False)
    ob_rim = obj_from_bm(f'Rim_{tag}', bm, [M['alloy'], M['dark']], smooth_angle=40.0, parent=parent)

    # ---- face (solid ring) with turbine slots
    y_out = yo - 0.0040         # outer edge of fin field
    y_in = yo - 0.0150          # inner edge (dished)
    y_hub = yo - 0.0095         # raised hub plate
    th = 0.0125
    r_out = rf - 0.0105
    r_slot0, r_slot1 = 0.088 * (rb / 0.1778) ** 0.5, r_out - 0.009
    r_hub = r_slot0 - 0.007
    face = [
        (r_out, y_out - 0.0010), (r_out - 0.004, y_out), (r_slot1 + 0.002, y_out - 0.0008),
        (r_slot0 - 0.001, y_in), (r_hub + 0.0015, y_in), (r_hub, y_in + 0.0018), (r_hub - 0.0020, y_hub),
        (0.0340, y_hub), (0.0335, y_hub - 0.0030), (0.0335, y_hub - th - 0.004),
        (r_hub, y_in - th), (r_slot1, y_in - th), (r_out - 0.002, y_in - th + 0.004), (r_out, y_out - 0.010),
    ]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    lathe_into(bm, uv, face, 132, 0, closed=True, flip=True)
    ob_face = obj_from_bm(f'Face_{tag}', bm, [M['alloy']], smooth_angle=30.0, parent=parent)

    # slot cutter: tapered rounded slots
    NS = 44
    bm = bmesh.new()
    for k in range(NS):
        phi = TAU * k / NS
        w0, w1 = 0.0050 * (rb / 0.1778), 0.0102 * (rb / 0.1778)
        pts = []
        # outline in (radial r, tangential t) then rotate
        nc = 8
        for q in range(nc + 1):       # outer semicircle
            a = -math.pi / 2 + math.pi * q / nc
            pts.append((r_slot1 - w1 / 2 + w1 / 2 * math.cos(a), w1 / 2 * math.sin(a)))
        for q in range(nc + 1):       # inner semicircle
            a = math.pi / 2 + math.pi * q / nc
            pts.append((r_slot0 + w0 / 2 + w0 / 2 * math.cos(a), w0 / 2 * math.sin(a)))
        ring_lo, ring_hi = [], []
        for (r, tt) in pts:
            x = r * math.cos(phi) - tt * math.sin(phi)
            z = r * math.sin(phi) + tt * math.cos(phi)
            ring_lo.append(bm.verts.new((x, y_in - th + 0.0045, z)))
            ring_hi.append(bm.verts.new((x, y_out + 0.03, z)))
        m = len(pts)
        bm.faces.new(ring_hi)
        bm.faces.new(ring_lo[::-1])
        for q in range(m):
            q2 = (q + 1) % m
            bm.faces.new([ring_lo[q], ring_lo[q2], ring_hi[q2], ring_hi[q]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    cutter = obj_from_bm(f'SlotCutter_{tag}', bm, [M['dark']])
    apply_boolean(ob_face, cutter)
    bpy.data.objects.remove(cutter)

    # lug pockets in the hub plate (alloy walls)
    bm = bmesh.new()
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        cx, cz = 0.050 * math.cos(a), 0.050 * math.sin(a)
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=24, radius1=0.0155, radius2=0.0155, depth=0.03)
        for v in res['verts']:
            v.co = Vector((v.co.x + cx, v.co.z, v.co.y + cz))
            v.co.y += y_hub + 0.015 - 0.0075
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    pc = obj_from_bm(f'PocketCutter_{tag}', bm, [M['alloy']])
    apply_boolean(ob_face, pc)
    bpy.data.objects.remove(pc)
    try:
        apply_bevel(ob_face, 0.0007, 2, 35.0)
    except Exception as e:
        print('bevel failed', e)
    # merge face into rim object
    ob_face.select_set(True)
    return ob_rim, ob_face, (y_hub, y_in - th)


def join(objs, name):
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.join()
    ob = bpy.context.view_layer.objects.active
    ob.name = name
    ob.data.name = name
    return ob


def build_cap(tag, y_hub, M, parent):
    yb = y_hub - 0.008
    prof = [(0.0, y_hub + 0.0042), (0.012, y_hub + 0.0040), (0.0205, y_hub + 0.0035), (0.0215, y_hub + 0.0020),
            (0.0235, y_hub + 0.0020), (0.0245, y_hub + 0.0034), (0.0300, y_hub + 0.0030), (0.0318, y_hub + 0.0012),
            (0.0322, yb), (0.0, yb)]
    mi = [0, 0, 1, 1, 1, 0, 0, 0, 0, 0]
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    lathe_into(bm, uv, prof, 64, mi, closed=False, flip=True)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return obj_from_bm(f'Cap_{tag}', bm, [M['alloy'], M['dark']], smooth_angle=30.0, parent=parent)


def build_lugs(tag, y_hub, M, parent):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    seat = y_hub - 0.0095
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        cx, cz = 0.050 * math.cos(a), 0.050 * math.sin(a)
        # hex body via 6-segment lathe with chamfered top, plus conical seat & stud tip
        prof = [(0.0, seat + 0.0175), (0.0055, seat + 0.0175), (0.0065, seat + 0.0168),
                (0.0105, seat + 0.0150), (0.0110, seat + 0.0140), (0.0110, seat + 0.0045),
                (0.0090, seat + 0.0030), (0.0072, seat)]
        start = len(bm.verts)
        lathe_into(bm, uv, prof, 6, 0, closed=False, flip=True, a0=math.pi / 6, a1=math.pi / 6 + TAU)
        new = bm.verts[:] if False else None
        bm.verts.ensure_lookup_table()
        for v in bm.verts[start:]:
            v.co.x += cx
            v.co.z += cz
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    return obj_from_bm(f'Lugs_{tag}', bm, [M['chrome']], smooth_angle=20.0, parent=parent)


def build_disc(tag, s, y_mount, M, parent):
    ro, ri = 0.127, 0.078
    yc = y_mount - 0.050 if tag == 'F' else y_mount - 0.062
    pt, gap = 0.0065, 0.0095
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    # outer plate, inner plate (closed rectangles), hat (closed profile)
    for y0 in (yc + gap / 2, yc - gap / 2 - pt):
        lathe_into(bm, uv, [(ri, y0), (ro, y0), (ro, y0 + pt), (ri, y0 + pt)], 96, 0, closed=True, flip=True)
    hat = [(0.024, y_mount), (0.072, y_mount), (0.075, y_mount - 0.003), (0.075, yc + gap / 2 + pt),
           (ri + 0.002, yc + gap / 2 + pt), (ri + 0.002, yc + gap / 2), (0.069, yc + gap / 2), (0.069, y_mount - 0.006),
           (0.024, y_mount - 0.006)]
    lathe_into(bm, uv, hat, 96, 0, closed=True, flip=True)
    # vanes
    NV = 30
    for k in range(NV):
        a = TAU * (k + 0.5) / NV
        c = Vector((math.cos(a), 0, math.sin(a)))
        t = Vector((-math.sin(a), 0, math.cos(a)))
        r0, r1, hw = ri + 0.004, ro - 0.002, 0.0028
        quad = []
        for (r, tt) in [(r0, -hw), (r1, -hw), (r1, hw), (r0, hw)]:
            quad.append(c * r + t * tt)
        lo = [bm.verts.new(p + Vector((0, yc - gap / 2, 0))) for p in quad]
        hi = [bm.verts.new(p + Vector((0, yc + gap / 2, 0))) for p in quad]
        for q in range(4):
            q2 = (q + 1) % 4
            bm.faces.new([lo[q], lo[q2], hi[q2], hi[q]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return obj_from_bm(f'Disc_{tag}', bm, [M['disc']], smooth_angle=30.0, parent=parent), yc


def build_caliper(tag, yc, M, parent):
    bm = bmesh.new()
    uv = bm.loops.layers.uv.new('UVMap')
    span = math.radians(26)
    a0, a1 = math.pi - span, math.pi + span     # centred on -X (rear of the disc)
    half_gap = 0.0125
    # outboard half, inboard half, bridge over the disc edge
    blocks = [
        [(0.096, yc + half_gap), (0.137, yc + half_gap), (0.137, yc + half_gap + 0.017), (0.096, yc + half_gap + 0.012)],
        [(0.092, yc - half_gap - 0.026), (0.137, yc - half_gap - 0.026), (0.137, yc - half_gap), (0.092, yc - half_gap)],
        [(0.131, yc - half_gap - 0.022), (0.149, yc - half_gap - 0.020), (0.149, yc + half_gap + 0.015), (0.131, yc + half_gap + 0.015)],
    ]
    for b in blocks:
        lathe_into(bm, uv, b, 14, 0, closed=True, a0=a0, a1=a1, caps=True, flip=True)
    # bleed nipple & mounting lugs (small cylinders) for detail
    for (r, ang) in [(0.142, math.pi - span * 0.6), (0.142, math.pi + span * 0.6)]:
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=16, radius1=0.006, radius2=0.006, depth=0.012)
        for v in res['verts']:
            v.co = Vector((v.co.x + r * math.cos(ang), v.co.z + yc - half_gap - 0.032, v.co.y + r * math.sin(ang)))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-6)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    ob = obj_from_bm(f'Caliper_{tag}', bm, [M['caliper']], smooth_angle=35.0, parent=parent)
    try:
        apply_bevel(ob, 0.0015, 2, 40.0)
    except Exception as e:
        print('caliper bevel failed', e)
    return ob


def build_assembly(tag, M):
    s = SPEC[tag]
    asm = bpy.data.objects.new(f'WheelAsm_{tag}', None)
    bpy.context.scene.collection.objects.link(asm)
    spin = bpy.data.objects.new(f'Wheel_{tag}', None)
    bpy.context.scene.collection.objects.link(spin)
    spin.parent = asm
    tyre = build_tyre(tag, s, M, spin)
    rim, face, (y_hub, y_back) = build_rim(tag, s, M, spin)
    rimj = join([rim, face], f'Rim_{tag}')
    rimj.parent = spin
    cap = build_cap(tag, y_hub, M, spin)
    lugs = build_lugs(tag, y_hub, M, spin)
    disc, yc = build_disc(tag, s, y_back, M, spin)
    cal = build_caliper(tag, yc, M, asm)
    return asm


def tri_count(ob):
    me = ob.data
    return sum(len(p.vertices) - 2 for p in me.polygons)


def preview(path):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 96
    sc.cycles.use_denoising = False
    sc.render.resolution_x, sc.render.resolution_y = 960, 540
    world = bpy.data.worlds.new('W')
    sc.world = world
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_elevation = math.radians(35)
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 0.06
    sky.sun_intensity = 0.4
    # ground
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -0.3315))
    g = bpy.context.active_object
    g.data.materials.append(make_mat('Ground', (0.25, 0.25, 0.25), 0, 0.8))
    # offset the rear assembly for the preview only
    rear = bpy.data.objects['WheelAsm_R']
    front = bpy.data.objects['WheelAsm_F']
    rear.location = (-0.9, 0, 0.0365)
    front.location = (0.0, 0, 0.0)
    cam_d = bpy.data.cameras.new('cam')
    cam = bpy.data.objects.new('cam', cam_d)
    sc.collection.objects.link(cam)
    import os as _os
    cl = [float(v) for v in _os.environ.get('CAM', '0.9,2.1,0.35').split(',')]
    tg = [float(v) for v in _os.environ.get('TGT', '-0.45,0,0').split(',')]
    cam.location = cl
    look = Vector(tg) - cam.location
    cam.rotation_euler = look.to_track_quat('-Z', 'Y').to_euler()
    cam_d.lens = 50
    sc.camera = cam
    sun = bpy.data.lights.new('sun', 'SUN')
    sun.energy = 1.5
    so = bpy.data.objects.new('sun', sun)
    so.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(so)
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    rear.location = (0, 0, 0)


def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    clear_scene()
    M = mats()
    build_assembly('F', M)
    build_assembly('R', M)
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            bm = bmesh.new()
            bm.from_mesh(ob.data)
            bmesh.ops.triangulate(bm, faces=bm.faces, quad_method='BEAUTY', ngon_method='BEAUTY')
            bm.to_mesh(ob.data)
            bm.free()
    total = 0
    for ob in bpy.data.objects:
        if ob.type == 'MESH':
            n = tri_count(ob)
            total += n
            print(f'  {ob.name:12s} {n:7d} tris  parent={ob.parent.name if ob.parent else None}')
    print('TOTAL TRIS', total)
    os.makedirs(OUT_DIR, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=os.path.join(OUT_DIR, 'wheels.glb'), export_format='GLB',
                              export_apply=True, export_normals=True, export_tangents=True,
                              export_texcoords=True, export_materials='EXPORT', export_yup=True,
                              export_extras=False)
    print('EXPORTED', os.path.getsize(os.path.join(OUT_DIR, 'wheels.glb')))
    if '--preview' in argv:
        preview(os.path.join(OUT_DIR, 'wheels_preview.png'))
    if '--blend' in argv:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT_DIR, 'wheels.blend'))


main()
