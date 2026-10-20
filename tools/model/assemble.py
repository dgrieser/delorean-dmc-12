"""Blender assembler: NPZ parts + manifest -> GLB (run: blender -b -P assemble.py -- out.glb [--ao])."""
import bpy, bmesh, json, os, sys, time
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
OUTDIR = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
GLB = argv[0] if argv else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'web', 'assets', 'dmc12_raw.glb')
DO_AO = '--ao' in argv
man = json.load(open(f'{OUTDIR}/manifest.json'))

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene


def make_material(name, spec):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    r, g, b = spec['rgb']
    bsdf.inputs['Base Color'].default_value = (r, g, b, 1)
    bsdf.inputs['Metallic'].default_value = spec['metallic']
    bsdf.inputs['Roughness'].default_value = spec['roughness']
    if 'alpha' in spec:
        bsdf.inputs['Alpha'].default_value = spec['alpha']
        m.blend_method = 'BLEND'
    return m


MATS = {k: make_material(k, v) for k, v in man['materials'].items()}


from mathutils import Matrix, Vector


def empty(name, loc, parent=None, rot=None):
    o = bpy.data.objects.new(name, None)
    o.empty_display_size = 0.05
    scene.collection.objects.link(o)
    M = Matrix.Identity(4)
    if rot is not None:
        R = Matrix((rot[0], rot[1], rot[2])).transposed()   # columns = local axes
        M = R.to_4x4()
    M.translation = Vector(loc)
    if parent is not None:
        o.parent = parent
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = parent.matrix_world.inverted() @ M
    else:
        o.matrix_basis = M
    bpy.context.view_layer.update()
    return o


car = empty('Car', (0, 0, 0))
nodes = {'Car': car}
# pivots must be created parent-first
pending = dict(man['pivots'])
while pending:
    for k, v in list(pending.items()):
        if v['parent'] in nodes:
            nodes[k] = empty(k + ('_Pivot' if k != 'Body' else ''), v['loc'], nodes[v['parent']], v.get('rot'))
            del pending[k]
for k, loc in man['markers'].items():
    empty(k, loc, car)


def box_uv(V, F):
    a, b, c = V[F[:, 0]], V[F[:, 1]], V[F[:, 2]]
    fn = np.cross(b - a, c - a)
    ax = np.argmax(np.abs(fn), 1)
    P = V[F]                                  # (nf,3,3)
    U = np.where(ax[:, None] == 0, P[:, :, 1], P[:, :, 0])
    W = np.where(ax[:, None] == 2, P[:, :, 1], P[:, :, 2])
    # keep orientation consistent (mirror on negative-facing faces)
    sgn = np.sign(fn[np.arange(len(F)), ax])
    U = np.where((ax[:, None] == 0) & (sgn[:, None] < 0), -U, U)
    return np.stack([U, W], -1).reshape(-1, 2)


def make_mesh(name, V, F, N, mat, parent, local=False, uvmode='box'):
    me = bpy.data.meshes.new(name)
    nv, nf = len(V), len(F)
    me.vertices.add(nv)
    me.vertices.foreach_set('co', V.astype(np.float32).ravel())
    me.loops.add(nf * 3)
    me.loops.foreach_set('vertex_index', F.astype(np.int32).ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set('loop_start', np.arange(0, nf * 3, 3, dtype=np.int32))
    me.polygons.foreach_set('loop_total', np.full(nf, 3, np.int32))
    me.update(calc_edges=True)
    if me.validate(verbose=False):
        print('  cleaned', name)
    nf = len(me.polygons)
    me.polygons.foreach_set('use_smooth', np.ones(nf, bool))
    if hasattr(me, 'use_auto_smooth'):          # Blender < 4.1; later versions keep custom normals as is
        me.use_auto_smooth = True
    me.normals_split_custom_set_from_vertices(N.astype(np.float32))
    if uvmode in ('brush', 'lens'):
        uv = me.uv_layers.new(name='UVMap')
        Fv = np.zeros(nf * 3, np.int32)
        me.loops.foreach_get('vertex_index', Fv)
        uv.data.foreach_set('uv', box_uv(V, Fv.reshape(-1, 3)).astype(np.float32).ravel())
    me.materials.append(MATS[mat])
    o = bpy.data.objects.new(name, me)
    scene.collection.objects.link(o)
    o.parent = parent
    if local:
        o.matrix_parent_inverse = Matrix.Identity(4)
        o.matrix_basis = Matrix.Identity(4)
    else:
        o.matrix_parent_inverse = parent.matrix_world.inverted()
    return o


t0 = time.time()
objs = []
for name, spec in man['parts'].items():
    fn = f'{OUTDIR}/{name}.npz'
    if not os.path.exists(fn):
        print('missing', name)
        continue
    d = np.load(fn)
    o = make_mesh(name, d['V'], d['F'], d['N'], spec['material'], nodes[spec['parent']], spec['uv'] == 'local', spec['uv'])
    objs.append(o)
print('meshes built', len(objs), time.time() - t0)

# ---------------------------------------------------------------------------------------------
# Ambient occlusion bake to vertex attributes: _AO (doors closed) and _AO2 (doors open)
def bake_ao(tag, samples=64, dist=0.6, door_angle=0.0):
    """Bake AO once on a combined world-space copy of all occluders, then scatter per part."""
    import math
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    if sc.world is None:
        sc.world = bpy.data.worlds.new('W')
    sc.world.light_settings.distance = dist
    bake = [o for o in objs if not NOAO(o)]
    Vs, Fs, offs = [], [], []
    off = 0
    rotL = Matrix.Rotation(math.radians(door_angle), 4, 'X')
    rotR = Matrix.Rotation(math.radians(-door_angle), 4, 'X')
    for o in bake:
        me = o.data
        n = len(me.vertices)
        v = np.zeros(n * 3, np.float32); me.vertices.foreach_get('co', v); v = v.reshape(-1, 3)
        M = o.matrix_world.copy()
        p = o.parent
        while p is not None:
            if p.name in ('Door_L_Pivot', 'Door_R_Pivot') and door_angle:
                pw = p.matrix_world
                M = pw @ (rotL if p.name == 'Door_L_Pivot' else rotR) @ pw.inverted() @ M
                break
            p = p.parent
        Mn = np.array(M)
        v = v @ Mn[:3, :3].T + Mn[:3, 3]
        lv = np.zeros(len(me.loops), np.int32); me.loops.foreach_get('vertex_index', lv)
        Vs.append(v); Fs.append(lv.reshape(-1, 3) + off); offs.append((o, off, n)); off += n
    V = np.concatenate(Vs); F = np.concatenate(Fs)
    cm = bpy.data.meshes.new('AOBAKE')
    cm.vertices.add(len(V)); cm.vertices.foreach_set('co', V.astype(np.float32).ravel())
    cm.loops.add(len(F) * 3); cm.loops.foreach_set('vertex_index', F.ravel().astype(np.int32))
    cm.polygons.add(len(F)); cm.polygons.foreach_set('loop_start', np.arange(0, len(F) * 3, 3, dtype=np.int32))
    cm.polygons.foreach_set('loop_total', np.full(len(F), 3, np.int32))
    cm.update()
    cm.polygons.foreach_set('use_smooth', np.ones(len(F), bool))
    cm.materials.append(bpy.data.materials.new('AOBAKE_M'))
    co = bpy.data.objects.new('AOBAKE', cm)
    scene.collection.objects.link(co)
    cm.color_attributes.new('aobake', 'FLOAT_COLOR', 'POINT')
    cm.color_attributes.active_color = cm.color_attributes['aobake']
    for o in objs:
        o.hide_render = True
        o.hide_set(True)
    bpy.ops.object.select_all(action='DESELECT')
    co.select_set(True)
    bpy.context.view_layer.objects.active = co
    t = time.time()
    bpy.ops.object.bake(type='AO', target='VERTEX_COLORS', margin=0)
    print('baked', tag, len(V), 'verts', round(time.time() - t, 1), 's', flush=True)
    buf = np.zeros(len(V) * 4, np.float32)
    cm.color_attributes['aobake'].data.foreach_get('color', buf)
    ao = buf[0::4].astype(np.float64)
    # per-vertex Monte Carlo noise shows as fuzz on dense trim: two light neighbour-averaging passes
    # (parts share no vertices, so this never bleeds across a gap between parts)
    E = np.concatenate([F[:, [0, 1]], F[:, [1, 2]], F[:, [2, 0]]])
    deg = np.bincount(E[:, 0], minlength=len(V)) + np.bincount(E[:, 1], minlength=len(V))
    for _ in range(2):
        nsum = np.bincount(E[:, 0], ao[E[:, 1]], len(V)) + np.bincount(E[:, 1], ao[E[:, 0]], len(V))
        ao = 0.5 * ao + 0.5 * np.where(deg > 0, nsum / np.maximum(deg, 1), ao)
    ao = ao.astype(np.float32)
    for o, s0, n in offs:
        me = o.data
        if tag not in me.attributes:
            me.attributes.new(tag, 'FLOAT', 'POINT')
        me.attributes[tag].data.foreach_set('value', ao[s0:s0 + n])
    for o in objs:
        if NOAO(o):
            me = o.data
            if tag not in me.attributes:
                me.attributes.new(tag, 'FLOAT', 'POINT')
            me.attributes[tag].data.foreach_set('value', np.ones(len(me.vertices), np.float32))
        o.hide_render = False
        o.hide_set(False)
    bpy.data.objects.remove(co)
    bpy.data.meshes.remove(cm)


def NOAO(o):
    m = o.data.materials[0].name if o.data.materials else ''
    return m.startswith(('Glass', 'Lamp_HeadLens', 'Lamp_Turn', 'Lamp_Marker', 'Lamp_Tail', 'Lamp_Reverse', 'MirrorGlass'))


if DO_AO:
    bake_ao('_AO', door_angle=0.0)
    bake_ao('_AO2', door_angle=69.0)          # web/js/car.js doorP.max

# the body is modelled in its stock frame; lower the whole car (wheel pivots included, which sit
# STANCE higher in that frame) so the tyres stand on the ground
car.location.z = -man.get('stance', 0.0)
bpy.context.view_layer.update()

# external GLB assets (wheels) are merged by the app; nothing else here.
opts = dict(filepath=GLB, export_format='GLB', export_normals=True, export_tangents=True, export_apply=True,
            export_yup=True, export_extras=True, export_attributes=True, export_materials='EXPORT')
props = bpy.ops.export_scene.gltf.get_rna_type().properties
if 'export_colors' in props:                  # Blender < 4.2
    opts['export_colors'] = False
elif 'export_vertex_color' in props:
    opts['export_vertex_color'] = 'NONE'
bpy.ops.export_scene.gltf(**opts)
print('exported', GLB, time.time() - t0)
