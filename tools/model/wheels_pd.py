"""DMC-12 wheels and tyres from Peter_D's "DeLorean wheels" (Sketchfab, CC BY 4.0,
https://sketchfab.com/3d-models/delorean-wheels-813336c9381a4772a8a1ed1e7c6fae42), fitted to
the rig of wheels.py: our procedural vented discs and calipers stay, the turbine rims and
Goodyear tyres are replaced by the scanned-quality model, decimated for the web.

Run:  blender -b -P tools/model/wheels_pd.py -- <downloaded wheels.glb> [--preview]
Writes tools/out/wheels.glb (pack it with tools/pack.py) and the textures used by
web/js/materials.js to web/assets/tex/pd_*.jpg.

The source holds one front (WHEEL_FL) and one rear (WHEEL_RL) assembly at arbitrary poses.
Each is re-framed from its own geometry: the tyre's axis of symmetry (smallest principal
axis) becomes the axle, the side carrying the hub (centre cap, lugs) is outward, and the tyre
mid-plane sits on the wheel centre. The source dimensions already match the car (front
195/60 R14: R 0.293 m, rear 235/60 R15: R 0.330 m), so nothing is scaled.
"""
import bpy
import os
import sys
import numpy as np
from mathutils import Matrix

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wheels as W  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TEX_OUT = os.path.join(ROOT, 'web', 'assets', 'tex')
SRC = {'F': 'WHEEL_FL', 'R': 'WHEEL_RL'}
# decimation ratios (source: ~425k tris per tyre, ~79k per rim)
RATIO = {'tyre': 0.07, 'rim': 0.40}
MAT = {'mat_tire_front': 'Tyre_PD_F', 'mat_tire_back': 'Tyre_PD_R', 'mat_wheel': 'Wheel_PD'}


def meshes_under(name):
    root = bpy.data.objects[name]
    out = []
    def walk(o):
        for c in o.children:
            if c.type == 'MESH':
                out.append(c)
            walk(c)
    walk(root)
    return out


def world_verts(ob):
    m = np.array(ob.matrix_world)
    v = np.empty(len(ob.data.vertices) * 3)
    ob.data.vertices.foreach_get('co', v)
    v = v.reshape(-1, 3)
    return v @ m[:3, :3].T + m[:3, 3]


def frame_for(tyres, rims):
    """Matrix taking source world space into the wheel frame (axle +Y outward, Z up)."""
    t = np.concatenate([world_verts(o) for o in tyres])
    c = t.mean(0)
    _, vecs = np.linalg.eigh(np.cov((t - c).T))
    ax = vecs[:, 0]
    r = np.concatenate([world_verts(o) for o in rims]) - c
    radial = np.linalg.norm(r - np.outer(r @ ax, ax), axis=1)
    if (r @ ax)[radial < 0.06].mean() < 0:      # hub (cap + lugs) faces outward
        ax = -ax
    a = (t - c) @ ax
    c = c + ax * 0.5 * (a.max() + a.min())      # tyre mid-plane
    up = np.array([0.0, 0.0, 1.0]) - ax * ax[2]
    up /= np.linalg.norm(up)
    x = np.cross(ax, up)
    R = np.eye(4)
    R[0, :3], R[1, :3], R[2, :3] = x, ax, up    # rows: new basis -> (x, y = axle, z = up)
    T = np.eye(4)
    T[:3, 3] = -c
    return Matrix((R @ T).tolist())


def bake_into(ob, M):
    """Bake world transform + M into the mesh data and unparent."""
    me = ob.data
    me.transform(ob.matrix_world)
    me.transform(M)
    ob.parent = None
    ob.matrix_world = Matrix.Identity(4)
    if me.has_custom_normals:
        me.free_normals_split() if hasattr(me, 'free_normals_split') else None
        bpy.context.view_layer.objects.active = ob
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.mesh.customdata_custom_splitnormals_clear()


def join(objs, name):
    with bpy.context.temp_override(active_object=objs[0], selected_editable_objects=objs, object=objs[0]):
        bpy.ops.object.join()
    ob = objs[0]
    ob.name = ob.data.name = name
    return ob


def decimate(ob, ratio, smooth_deg):
    mod = ob.modifiers.new('dec', 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = ratio
    mod.use_collapse_triangulate = True
    with bpy.context.temp_override(object=ob, active_object=ob):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    for p in ob.data.polygons:
        p.use_smooth = True
    ob.data.use_auto_smooth = True
    ob.data.auto_smooth_angle = np.radians(smooth_deg)


def export_textures():
    """Write the source PBR maps as JPEG for the viewer (base colour, ORM, normal)."""
    os.makedirs(TEX_OUT, exist_ok=True)
    done = set()
    for src, dst in MAT.items():
        m = bpy.data.materials.get(dst)
        if not m:
            continue
        p = next(n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        def img_of(sock):
            seen = [sock]
            while seen:
                s = seen.pop()
                for l in s.links:
                    n = l.from_node
                    if n.type == 'TEX_IMAGE':
                        return n.image
                    seen += [i for i in n.inputs if i.is_linked]
            return None
        maps = {'base': img_of(p.inputs['Base Color']), 'orm': img_of(p.inputs['Roughness']),
                'normal': img_of(p.inputs['Normal'])}
        for k, im in maps.items():
            if im is None or (dst, k) in done:
                continue
            out = os.path.join(TEX_OUT, f"pd_{dst.lower().replace('_pd', '')}_{k}.jpg")
            im.file_format = 'JPEG'
            sc = bpy.context.scene
            sc.render.image_settings.file_format = 'JPEG'
            sc.render.image_settings.quality = 90
            sc.render.image_settings.color_mode = 'RGB'
            im.save_render(out, scene=sc)
            done.add((dst, k))
            print('texture', out, os.path.getsize(out))


def main():
    argv = sys.argv[sys.argv.index('--') + 1:]
    src = argv[0]
    W.clear_scene()
    M = W.mats()
    for tag in 'FR':
        W.build_assembly(tag, M)
    # keep our discs and calipers; the source supplies rim, centre cap, lugs and tyre
    for tag in 'FR':
        for n in (f'Tyre_{tag}', f'Rim_{tag}', f'Cap_{tag}', f'Lugs_{tag}'):
            ob = bpy.data.objects.get(n)
            if ob:
                bpy.data.objects.remove(ob, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=src)
    for m in bpy.data.materials:
        if m.name in MAT:
            m.name = MAT[m.name]
    for tag, grp in SRC.items():
        ms = meshes_under(grp)
        tyres = [o for o in ms if o.name.startswith('tire')]
        rims = [o for o in ms if o.name.startswith('wheel')]
        F = frame_for(tyres, rims)
        for o in ms:
            bake_into(o, F)
        tyre = join(tyres, f'Tyre_{tag}')
        # the lettered sidewall faces the hub side in the source: turn the tyre round (not mirror)
        tyre.data.transform(Matrix.Rotation(np.pi, 4, 'Z'))
        rim = join(rims, f'Rim_{tag}') if len(rims) > 1 else rims[0]
        rim.name = rim.data.name = f'Rim_{tag}'
        decimate(tyre, RATIO['tyre'], 35.0)
        decimate(rim, RATIO['rim'], 40.0)
        spin = bpy.data.objects[f'Wheel_{tag}']
        for o in (tyre, rim):
            o.parent = spin
            o.matrix_parent_inverse = Matrix.Identity(4)
    # drop the source scene graph (empties, unused meshes)
    keep = {o for o in bpy.data.objects if o.name.startswith(('WheelAsm_', 'Wheel_', 'Tyre_', 'Rim_', 'Disc_', 'Caliper_'))}
    for o in list(bpy.data.objects):
        if o not in keep:
            bpy.data.objects.remove(o, do_unlink=True)
    W.triangulate_all()
    export_textures()
    W.export(os.path.join(W.OUT_DIR, 'wheels.glb'))
    if '--preview' in argv:
        W.preview(os.path.join(W.OUT_DIR, 'wheels_preview.png'))


main()
