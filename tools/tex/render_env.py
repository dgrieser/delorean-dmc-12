"""Render equirectangular HDR environments for the DMC-12 viewer in Blender/Cycles.

Usage: blender -b -P render_env.py -- <studio|day|night> <out.hdr> [width] [samples]

Blender world (X fwd, Y left, Z up) maps to three.js (X, Z, -Y). The panorama camera is
rotated (90, 0, -90) so the image centre looks along +X (car front) and u=0.75 is three.js +Z,
which matches three.js' equirect lookup (u = atan2(z, x) / 2pi + 0.5).
"""
import bpy, math, sys, random

argv = sys.argv[sys.argv.index('--') + 1:]
SCENE = argv[0]
OUTP = argv[1]
WIDTH = int(argv[2]) if len(argv) > 2 else 2048
SAMPLES = int(argv[3]) if len(argv) > 3 else 256
random.seed(1985)

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'
sc.cycles.samples = SAMPLES
sc.cycles.use_adaptive_sampling = True
sc.cycles.adaptive_threshold = 0.015
sc.cycles.use_denoising = False
sc.cycles.max_bounces = 6
sc.cycles.diffuse_bounces = 3
sc.cycles.glossy_bounces = 3
sc.cycles.sample_clamp_indirect = 8.0
try:
    sc.cycles.use_light_tree = True
except Exception:
    pass
sc.render.resolution_x = WIDTH
sc.render.resolution_y = WIDTH // 2
sc.render.resolution_percentage = 100
sc.view_settings.view_transform = 'Standard'
sc.view_settings.look = 'None'
sc.render.image_settings.file_format = 'HDR'
sc.render.filepath = OUTP
sc.render.threads_mode = 'AUTO'

cam = bpy.data.cameras.new('pano')
cam.type = 'PANO'
try:
    cam.panorama_type = 'EQUIRECTANGULAR'
except Exception:
    cam.cycles.panorama_type = 'EQUIRECTANGULAR'
camo = bpy.data.objects.new('pano', cam)
sc.collection.objects.link(camo)
sc.camera = camo
camo.rotation_euler = (math.radians(90), 0, math.radians(-90))
camo.location = (0, 0, 1.0)


# ------------------------------------------------------------------ helpers
def mat_principled(name, color, rough=0.5, metal=0.0, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Metallic'].default_value = metal
    try:
        p.inputs['Specular IOR Level'].default_value = spec
    except KeyError:
        p.inputs['Specular'].default_value = spec
    return m


def mat_emit(name, strength, kelvin=None, color=(1, 1, 1)):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs['Strength'].default_value = strength
    if kelvin:
        bb = nt.nodes.new('ShaderNodeBlackbody')
        bb.inputs[0].default_value = kelvin
        mix = nt.nodes.new('ShaderNodeMixRGB')
        mix.blend_type = 'MULTIPLY'
        mix.inputs[0].default_value = 1.0
        nt.links.new(bb.outputs[0], mix.inputs[1])
        mix.inputs[2].default_value = (*color, 1)
        nt.links.new(mix.outputs[0], e.inputs['Color'])
    else:
        e.inputs['Color'].default_value = (*color, 1)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], out.inputs[0])
    return m


def plane(name, size, loc, rot, mat):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = (size[0], size[1], 1)
    o.data.materials.append(mat)
    return o


def cube(name, size, loc, mat, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    o = bpy.context.object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    return o


def world_color(rgb, strength=1.0):
    w = bpy.data.worlds.new('world')
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*rgb, 1)
    bg.inputs[1].default_value = strength
    return w


def emissive_softbox(name, w, h, loc, rot, strength, kelvin=5500):
    """Softbox: emitting face plus a thin dark frame so edges read as real fixtures."""
    o = plane(name, (w, h), loc, rot, mat_emit(name + '_e', strength, kelvin))
    return o


# ------------------------------------------------------------------ studio
def build_studio():
    world_color((0, 0, 0), 0)
    floor = mat_principled('floor', (0.030, 0.030, 0.032), rough=0.32, spec=0.5)
    wall = mat_principled('wall', (0.055, 0.055, 0.058), rough=0.9)
    ceil = mat_principled('ceil', (0.020, 0.020, 0.022), rough=0.9)
    board = mat_principled('board', (0.75, 0.75, 0.75), rough=0.95)
    L, W, Hh = 36.0, 28.0, 9.0
    plane('floor', (L, W), (0, 0, 0), (0, 0, 0), floor)
    plane('ceiling', (L, W), (0, 0, Hh), (math.pi, 0, 0), ceil)
    plane('wall_f', (W, Hh), (L / 2, 0, Hh / 2), (0, -math.pi / 2, 0), wall)
    plane('wall_b', (W, Hh), (-L / 2, 0, Hh / 2), (0, math.pi / 2, 0), wall)
    plane('wall_l', (L, Hh), (0, W / 2, Hh / 2), (math.pi / 2, 0, 0), wall)
    plane('wall_r', (L, Hh), (0, -W / 2, Hh / 2), (-math.pi / 2, 0, 0), wall)
    for p in ['wall_f', 'wall_b']:
        o = bpy.data.objects[p]
        o.scale = (Hh, W, 1)
    for p in ['wall_l', 'wall_r']:
        o = bpy.data.objects[p]
        o.scale = (L, Hh, 1)
    # overhead: big diffuser + two crisp strips running the car's length (X)
    emissive_softbox('top_main', 8.0, 3.2, (0, 0, 6.6), (math.pi, 0, 0), 7.0)
    emissive_softbox('top_strip_l', 11.0, 0.45, (0, 3.6, 5.6), (math.pi, 0, 0), 22.0)
    emissive_softbox('top_strip_r', 11.0, 0.45, (0, -3.6, 5.6), (math.pi, 0, 0), 22.0)
    # side panels: long horizontal bands -> highlight line along the flanks
    emissive_softbox('side_l', 9.0, 2.4, (0.5, 9.0, 1.9), (math.pi / 2, 0, 0), 5.5)
    emissive_softbox('side_r', 9.0, 2.4, (-0.5, -9.0, 1.9), (-math.pi / 2, 0, 0), 5.5)
    # front / rear fill
    emissive_softbox('front', 5.0, 2.6, (12.0, 0, 2.2), (0, -math.pi / 2, 0), 3.0)
    emissive_softbox('rear', 5.0, 2.6, (-12.0, 0, 2.2), (0, math.pi / 2, 0), 2.2)
    # tall kicker strips at the corners
    emissive_softbox('kick_fl', 0.7, 4.5, (8.5, 6.5, 2.6), (math.pi / 2, 0, math.radians(-35)), 12.0)
    emissive_softbox('kick_rr', 0.7, 4.5, (-8.5, -6.5, 2.6), (-math.pi / 2, 0, math.radians(-35)), 9.0)
    # white bounce boards (catch light, add mid-tones to reflections)
    plane('board_l', (4.0, 3.0), (-6.0, 7.5, 1.6), (math.pi / 2, 0, math.radians(20)), board)
    plane('board_r', (4.0, 3.0), (6.0, -7.5, 1.6), (-math.pi / 2, 0, math.radians(20)), board)
    # light rig trusses (dark bars) for a bit of structure overhead
    truss = mat_principled('truss', (0.015, 0.015, 0.015), rough=0.6, metal=0.6)
    for y in (-5.0, 5.0):
        cube('truss', (20, 0.25, 0.25), (0, y, 7.6), truss)
    for x in (-7.0, 7.0):
        cube('truss', (0.25, 14, 0.25), (x, 0, 7.6), truss)


# ------------------------------------------------------------------ day
SUN_EL = 35.0
SUN_AZ = 40.0   # degrees from +X (front) towards -Y blender (= three.js +Z, car's right)


def build_day():
    w = bpy.data.worlds.new('world')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    sky = nt.nodes.new('ShaderNodeTexSky')
    sky.sky_type = 'NISHITA'
    sky.sun_disc = False
    sky.sun_elevation = math.radians(SUN_EL)
    # Nishita sun direction (xy) = (sin rot, cos rot); blender azimuth = -SUN_AZ
    sky.sun_rotation = math.radians(90 + SUN_AZ)
    sky.altitude = 0
    sky.air_density = 1.0
    sky.dust_density = 1.4
    sky.ozone_density = 1.0
    nt.links.new(sky.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    # sun lamp matching the sky
    sun = bpy.data.lights.new('sun', 'SUN')
    # sky upper-hemisphere mean radiance ~2.6 at strength 1 -> sun:sky horizontal irradiance ~3:1
    sun.energy = 43.0
    sun.angle = math.radians(0.53)
    so = bpy.data.objects.new('sun', sun)
    sc.collection.objects.link(so)
    el, az = math.radians(SUN_EL), math.radians(SUN_AZ)
    d = (math.cos(el) * math.cos(az), -math.cos(el) * math.sin(az), math.sin(el))   # towards sun
    # sun light points along -d
    import mathutils
    so.rotation_euler = mathutils.Vector((-d[0], -d[1], -d[2])).to_track_quat('-Z', 'Y').to_euler()
    sky_strength_ref['sun_dir'] = d
    # ground: asphalt lot with painted bays, then grass/dirt to the horizon
    asphalt = bpy.data.materials.new('asphalt')
    asphalt.use_nodes = True
    ant = asphalt.node_tree
    p = ant.nodes['Principled BSDF']
    noise = ant.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 3.0
    noise.inputs['Detail'].default_value = 8.0
    ramp = ant.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (0.030, 0.030, 0.032, 1)
    ramp.color_ramp.elements[1].color = (0.075, 0.072, 0.068, 1)
    ant.links.new(noise.outputs['Fac'], ramp.inputs[0])
    ant.links.new(ramp.outputs[0], p.inputs['Base Color'])
    p.inputs['Roughness'].default_value = 0.85
    plane('lot', (70, 70), (0, 0, 0), (0, 0, 0), asphalt)
    grass = mat_principled('grass', (0.045, 0.075, 0.025), rough=0.95)
    plane('field', (5000, 5000), (0, 0, -0.02), (0, 0, 0), grass)
    paint = mat_principled('paint', (0.65, 0.65, 0.62), rough=0.7)
    for i in range(-6, 7):
        if i == 0:
            continue
        plane('line', (0.12, 5.0), (8.0, i * 2.7, 0.003), (0, 0, 0), paint)
        plane('line', (0.12, 5.0), (-8.0, i * 2.7, 0.003), (0, 0, 0), paint)
    curb = mat_principled('curb', (0.35, 0.34, 0.32), rough=0.9)
    for s in (-1, 1):
        cube('curb', (70, 0.3, 0.15), (0, s * 35, 0.075), curb)
        cube('curb', (0.3, 70, 0.15), (s * 35, 0, 0.075), curb)
    # light poles around the lot
    pole = mat_principled('pole', (0.25, 0.25, 0.26), rough=0.5, metal=0.8)
    for x, y in [(18, 14), (-16, 18), (20, -16), (-22, -12), (2, 30), (30, 2)]:
        cube('pole', (0.18, 0.18, 8.0), (x, y, 4.0), pole)
        cube('head', (1.2, 0.35, 0.2), (x, y, 8.0), pole)
    # tree line and buildings on the horizon
    def foliage(name, base):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt_ = m.node_tree
        p_ = nt_.nodes['Principled BSDF']
        p_.inputs['Roughness'].default_value = 0.85
        vor = nt_.nodes.new('ShaderNodeTexVoronoi')
        vor.inputs['Scale'].default_value = 1.6
        noi = nt_.nodes.new('ShaderNodeTexNoise')
        noi.inputs['Scale'].default_value = 0.7
        noi.inputs['Detail'].default_value = 6.0
        rmp = nt_.nodes.new('ShaderNodeValToRGB')
        rmp.color_ramp.elements[0].color = (base[0] * 0.45, base[1] * 0.45, base[2] * 0.45, 1)
        rmp.color_ramp.elements[1].color = (base[0] * 1.35, base[1] * 1.3, base[2] * 1.2, 1)
        nt_.links.new(noi.outputs['Fac'], rmp.inputs[0])
        nt_.links.new(rmp.outputs[0], p_.inputs['Base Color'])
        bmp = nt_.nodes.new('ShaderNodeBump')
        bmp.inputs['Strength'].default_value = 0.9
        bmp.inputs['Distance'].default_value = 0.5
        nt_.links.new(vor.outputs['Distance'], bmp.inputs['Height'])
        nt_.links.new(bmp.outputs['Normal'], p_.inputs['Normal'])
        return m
    leaf = [foliage('leaf%d' % i, c) for i, c in
            enumerate([(0.030, 0.055, 0.018), (0.040, 0.065, 0.022), (0.050, 0.060, 0.028), (0.035, 0.050, 0.025)])]
    bark = mat_principled('bark', (0.05, 0.035, 0.02), rough=0.9)
    for i in range(170):
        a = random.random() * 2 * math.pi
        r = random.uniform(55, 140)
        x, y = r * math.cos(a), r * math.sin(a)
        hgt = random.uniform(7, 16)
        lm = random.choice(leaf)
        for j in range(random.randint(3, 5)):
            jx, jy = random.uniform(-1.6, 1.6), random.uniform(-1.6, 1.6)
            jz = hgt * random.uniform(0.5, 0.8)
            bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=3, radius=1, location=(x + jx, y + jy, jz))
            o = bpy.context.object
            sz = random.uniform(2.0, 3.8)
            o.scale = (sz, sz, sz * random.uniform(0.8, 1.3))
            bpy.ops.object.shade_smooth()
            o.data.materials.append(lm)
        cube('trunk', (0.4, 0.4, hgt * 0.4), (x, y, hgt * 0.2), bark)
    facade = [mat_principled('fac%d' % i, c, rough=0.8) for i, c in
              enumerate([(0.55, 0.52, 0.47), (0.42, 0.42, 0.43), (0.62, 0.6, 0.56), (0.3, 0.31, 0.33)])]
    glassb = mat_principled('bglass', (0.05, 0.06, 0.07), rough=0.08, metal=0.0, spec=1.0)
    for i in range(34):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(170, 320)
        x, y = r * math.cos(a), r * math.sin(a)
        wdt, dep, hgt = random.uniform(15, 45), random.uniform(15, 35), random.uniform(8, 38)
        m = glassb if random.random() < 0.25 else random.choice(facade)
        cube('bldg', (wdt, dep, hgt), (x, y, hgt / 2), m, rot=(0, 0, a))


# ------------------------------------------------------------------ night
def build_night():
    w = bpy.data.worlds.new('world')
    sc.world = w
    w.use_nodes = True
    nt = w.node_tree
    bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    cr = ramp.color_ramp
    cr.elements[0].position = 0.0
    cr.elements[0].color = (0.010, 0.006, 0.0035, 1)      # below horizon / glow
    cr.elements[1].position = 1.0
    cr.elements[1].color = (0.0006, 0.0010, 0.0024, 1)    # zenith
    e = cr.elements.new(0.06)
    e.color = (0.016, 0.009, 0.0050, 1)                   # orange light-pollution band
    e = cr.elements.new(0.25)
    e.color = (0.0030, 0.0030, 0.0045, 1)
    # Generated coords for world are the direction; z in [-1,1] -> map to [0,1] above horizon
    mp = nt.nodes.new('ShaderNodeMapRange')
    mp.inputs['From Min'].default_value = 0.0
    mp.inputs['From Max'].default_value = 1.0
    nt.links.new(sep.outputs['Z'], mp.inputs['Value'])
    nt.links.new(mp.outputs['Result'], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], bg.inputs[0])
    bg.inputs[1].default_value = 1.0
    # wet-ish asphalt with puddle roughness variation
    asphalt = bpy.data.materials.new('asphalt')
    asphalt.use_nodes = True
    ant = asphalt.node_tree
    p = ant.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.05, 0.05, 0.052, 1)
    noise = ant.nodes.new('ShaderNodeTexNoise')
    noise.inputs['Scale'].default_value = 0.35
    noise.inputs['Detail'].default_value = 6.0
    rr = ant.nodes.new('ShaderNodeValToRGB')
    rr.color_ramp.elements[0].position = 0.45
    rr.color_ramp.elements[0].color = (0.05, 0.05, 0.05, 1)
    rr.color_ramp.elements[1].position = 0.62
    rr.color_ramp.elements[1].color = (0.45, 0.45, 0.45, 1)
    ant.links.new(noise.outputs['Fac'], rr.inputs[0])
    ant.links.new(rr.outputs[0], p.inputs['Roughness'])
    plane('lot', (400, 400), (0, 0, 0), (0, 0, 0), asphalt)
    paint = mat_principled('paint', (0.35, 0.35, 0.33), rough=0.6)
    for i in range(-6, 7):
        if i == 0:
            continue
        plane('line', (0.12, 5.0), (8.0, i * 2.7, 0.003), (0, 0, 0), paint)
        plane('line', (0.12, 5.0), (-8.0, i * 2.7, 0.003), (0, 0, 0), paint)
    pole = mat_principled('pole', (0.08, 0.08, 0.085), rough=0.5, metal=0.8)
    lamps = [(16, 12, 2100), (-14, 16, 2100), (18, -14, 2100), (-20, -11, 2100), (3, 28, 4300),
             (30, 1, 2100), (-32, 4, 4300), (40, 30, 2100), (-38, -34, 2100), (6, -36, 2100)]
    for x, y, k in lamps:
        cube('pole', (0.16, 0.16, 7.0), (x, y, 3.5), pole)
        cube('arm', (1.2, 0.15, 0.12), (x - 0.5 * math.copysign(1, x), y, 7.0), pole)
        hx = x - 1.0 * math.copysign(1, x)
        cube('head', (0.7, 0.32, 0.12), (hx, y, 6.94), pole)
        # glowing lens facing down + a spot that pools light on the ground
        plane('lens', (0.6, 0.26), (hx, y, 6.87), (math.pi, 0, 0), mat_emit('lens%d' % k, 90.0, k))
        sp = bpy.data.lights.new('spot', 'SPOT')
        sp.energy = 9000 if k < 3000 else 7000
        sp.spot_size = math.radians(120)
        sp.spot_blend = 0.6
        sp.shadow_soft_size = 0.3
        bb = sp
        if k < 3000:
            bb.color = (1.0, 0.56, 0.20)
        else:
            bb.color = (0.85, 0.92, 1.0)
        spo = bpy.data.objects.new('spot', sp)
        spo.location = (hx, y, 6.8)
        sc.collection.objects.link(spo)
    # buildings with sparse lit windows
    for i in range(26):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(55, 160)
        x, y = r * math.cos(a), r * math.sin(a)
        wdt, dep, hgt = random.uniform(15, 40), random.uniform(12, 30), random.uniform(9, 45)
        m = bpy.data.materials.new('bld%d' % i)
        m.use_nodes = True
        nt2 = m.node_tree
        pr = nt2.nodes['Principled BSDF']
        pr.inputs['Base Color'].default_value = (0.012, 0.012, 0.014, 1)
        pr.inputs['Roughness'].default_value = 0.8
        tco = nt2.nodes.new('ShaderNodeTexCoord')
        brick = nt2.nodes.new('ShaderNodeTexBrick')
        brick.offset = 0.0
        brick.inputs['Scale'].default_value = 1.0
        brick.inputs['Mortar Size'].default_value = 0.55
        brick.inputs['Mortar Smooth'].default_value = 0.0
        brick.inputs['Brick Width'].default_value = 3.0
        brick.inputs['Row Height'].default_value = 3.3
        brick.inputs['Color1'].default_value = (0, 0, 0, 1)
        brick.inputs['Color2'].default_value = (1, 1, 1, 1)
        brick.inputs['Bias'].default_value = 0.0
        # per-face facade coordinates in metres: u = x*|ny| + y*|nx|, v = z
        sepp = nt2.nodes.new('ShaderNodeSeparateXYZ')
        nt2.links.new(tco.outputs['Object'], sepp.inputs[0])
        sepn = nt2.nodes.new('ShaderNodeSeparateXYZ')
        nt2.links.new(tco.outputs['Normal'], sepn.inputs[0])
        def math_node(op, a=None, b=None, va=None, vb=None):
            n_ = nt2.nodes.new('ShaderNodeMath')
            n_.operation = op
            if a is not None: nt2.links.new(a, n_.inputs[0])
            elif va is not None: n_.inputs[0].default_value = va
            if b is not None: nt2.links.new(b, n_.inputs[1])
            elif vb is not None: n_.inputs[1].default_value = vb
            return n_
        anx = math_node('ABSOLUTE', sepn.outputs['X'])
        any_ = math_node('ABSOLUTE', sepn.outputs['Y'])
        xs = math_node('MULTIPLY', sepp.outputs['X'], vb=wdt)
        ys = math_node('MULTIPLY', sepp.outputs['Y'], vb=dep)
        zs = math_node('MULTIPLY', sepp.outputs['Z'], vb=hgt)
        u1 = math_node('MULTIPLY', xs.outputs[0], any_.outputs[0])
        u2 = math_node('MULTIPLY', ys.outputs[0], anx.outputs[0])
        uu = math_node('ADD', u1.outputs[0], u2.outputs[0])
        comb = nt2.nodes.new('ShaderNodeCombineXYZ')
        nt2.links.new(uu.outputs[0], comb.inputs['X'])
        nt2.links.new(zs.outputs[0], comb.inputs['Y'])
        nt2.links.new(comb.outputs[0], brick.inputs['Vector'])
        thr = nt2.nodes.new('ShaderNodeMath')
        thr.operation = 'GREATER_THAN'
        thr.inputs[1].default_value = random.uniform(0.76, 0.9)
        nt2.links.new(brick.outputs['Color'], thr.inputs[0])
        inv = nt2.nodes.new('ShaderNodeMath')
        inv.operation = 'SUBTRACT'
        inv.inputs[0].default_value = 1.0
        nt2.links.new(brick.outputs['Fac'], inv.inputs[1])
        # roofs (|nz|>0.5) never lit
        anz = math_node('ABSOLUTE', sepn.outputs['Z'])
        wallm = math_node('LESS_THAN', anz.outputs[0], vb=0.5)
        mul0 = math_node('MULTIPLY', thr.outputs[0], inv.outputs[0])
        mul = math_node('MULTIPLY', mul0.outputs[0], wallm.outputs[0])
        emit_col = (1.0, 0.72, 0.42, 1) if random.random() < 0.7 else (0.75, 0.85, 1.0, 1)
        pr.inputs['Emission Color'].default_value = emit_col
        # scale emission strength
        ms = nt2.nodes.new('ShaderNodeMath')
        ms.operation = 'MULTIPLY'
        ms.inputs[1].default_value = random.uniform(0.12, 0.45)
        nt2.links.new(mul.outputs[0], ms.inputs[0])
        nt2.links.new(ms.outputs[0], pr.inputs['Emission Strength'])
        cube('bldg', (wdt, dep, hgt), (x, y, hgt / 2), m, rot=(0, 0, a))
    # a few far tower beacons / glows
    for i in range(6):
        a = random.uniform(0, 2 * math.pi)
        r = random.uniform(150, 260)
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.6, location=(r * math.cos(a), r * math.sin(a), random.uniform(30, 60)))
        bpy.context.object.data.materials.append(mat_emit('beacon%d' % i, 40.0, color=(1.0, 0.1, 0.05)))


sky_strength_ref = {}
{'studio': build_studio, 'day': build_day, 'night': build_night}[SCENE]()
bpy.ops.render.render(write_still=True)
if SCENE == 'day':
    print('SUNDIR', sky_strength_ref['sun_dir'])
print('DONE', OUTP)
