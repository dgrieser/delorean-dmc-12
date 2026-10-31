"""Rig the supplied donor car without replacing the original car assets.

blender -b --python-exit-code 1 -P tools/model/build_donor.py -- /path/to/FINAL_MODEL_DMC12.fbx
python tools/pack.py tools/out/donor-car.glb web/assets/donor/car
python tools/pack.py tools/out/donor-wheels.glb web/assets/donor/wheels
"""
import sys, json, hashlib, shutil
from pathlib import Path
import bpy
import bmesh
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0, str(Path(__file__).parent))
from import_mirrors import components, Reporter, FBX_SHA256
from donor_doors import skin_geometry, contains_outline, door_shell, edge_details, body_jamb
from donor_hinges import attachments, BODY_BALL, DOOR_BALL, HINGE_Z, HINGE_SLOPE
from donor_cabin import seats, rear_cabin, glass_seals, door_pull, sill_details, rear_plate, seat_badge_uv, seat_belts, PULL_ANCHOR, PULL_CLOSED_SCALE, PULL_FREE_ANGLE
from donor_fittings import aerial, rear_heater, louvre_fixings, pedal, dash_ducts, floor_mats
from io_scene_fbx import import_fbx

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'tools/out'
WEB = ROOT/'web/assets/donor'
SOURCE = Path(sys.argv[sys.argv.index('--')+1]).resolve()
if hashlib.sha256(SOURCE.read_bytes()).hexdigest() != FBX_SHA256:
    raise ValueError('Unexpected donor FBX')
OUT.mkdir(exist_ok=True); WEB.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
import_fbx.load(Reporter(), bpy.context, filepath=str(SOURCE))
bpy.context.view_layer.update()


def connected(me, v):
    _, iv = np.unique(np.round(v, 5), axis=0, return_inverse=True)
    parent = list(range(iv.max()+1))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]; i = parent[i]
        return i
    for edge in me.edges:
        a,b = map(find, iv[list(edge.vertices)]); parent[a] = b
    groups = {}; ids = np.empty(len(v), int)
    for i in range(len(v)):
        root = find(iv[i])
        if root not in groups: groups[root] = len(groups)
        ids[i] = groups[root]
    return ids


sources = {}
for o in bpy.data.objects:
    if o.type != 'MESH' or not len(o.data.vertices): continue
    me = o.data; me.calc_loop_triangles()
    v = np.array([o.matrix_world @ p.co for p in me.vertices])*100
    v = v[:, [1,0,2]]*[-1,1,1]
    nm = o.matrix_world.to_3x3().inverted().transposed()
    n = np.array([nm @ a.vector for a in me.corner_normals])[:, [1,0,2]]*[-1,1,1]
    n /= np.maximum(np.linalg.norm(n,axis=1,keepdims=True),1e-12)
    uv = np.array([a.uv for a in me.uv_layers.active.data]) if me.uv_layers.active else np.zeros((len(me.loops),2))
    islands = np.empty(len(v), int)
    for ii, vertices in enumerate(components(me)): islands[vertices] = ii
    sources[o.name] = dict(islands=islands, v=v,n=n,uv=uv,loops=np.array([l.vertex_index for l in me.loops]),
        tris=np.array([t.loops[:] for t in me.loop_triangles]),
        mats=np.array([t.material_index for t in me.loop_triangles]),
        materials=[m.name for m in me.materials], comp=connected(me,v))

# Diffuse/normal maps remain in their original UV layout. Phong FBX values are
# translated to PBR by semantic material type in the viewer.
materials = {}
for m in bpy.data.materials:
    if not m.use_nodes: continue
    bs = next((n for n in m.node_tree.nodes if n.type=='BSDF_PRINCIPLED'), None)
    if bs is None: continue
    spec = {'color':list(bs.inputs['Base Color'].default_value)[:3], 'roughness':.55, 'metalness':0}
    texture_files = {}
    for node in m.node_tree.nodes:
        if node.type != 'TEX_IMAGE' or not node.image: continue
        links = list(node.outputs['Color'].links)
        kind = 'map' if any(l.to_socket.name=='Base Color' for l in links) else 'normalMap' if any(l.to_node.type=='NORMAL_MAP' for l in links) else None
        if not kind: continue
        file = Path(bpy.path.abspath(node.image.filepath))
        file = SOURCE.parent/file.name if not file.exists() else file
        texture_files[file.name] = file
        spec[kind] = file.name
    name = m.name
    if any(k in name for k in ['phong4SG','phong13SG','phong14SG','phong20SG']): spec.update(metalness=.9,roughness=.35)
    if 'phong6SG' in name: spec.update(metalness=.85,roughness=.24)
    if 'phong3SG' in name: spec.update(metalness=.35,roughness=.4)
    if 'phong4SG' in name: spec.pop('normalMap',None)  # FBX mislabels its material/opacity atlas as a normal map.
    if 'phong10SG' in name: spec.update(kind='glass',color=[.10,.12,.11])
    if 'phong9SG' in name: spec.update(kind='mirror',metalness=1,roughness=.035)
    if 'phong16SG' in name: spec.update(kind='lamp',color=[.65,.65,.60],emissive=[1,.92,.78],opacity=.35)
    if 'phong17SG' in name: spec.update(kind='lamp',color=[.45,.008,.003],emissive=[1,.015,.003])
    if 'phong18SG' in name: spec.update(kind='lamp',color=[.55,.16,.003],emissive=[1,.28,.005])
    if 'Wheel1A_3D' in name: spec.update(roughness=.85)
    if 'phong8SG' in name: spec['trim']=True
    # These atlases use alpha to cut out decal backgrounds and grille holes.
    # Their zero-alpha RGB pixels are white, so treating them as opaque creates
    # white rectangles around cabin controls, pedals, badges and engine details.
    # The body livery's alpha is a paint mask, not a geometry cutout.
    if spec.get('map') in ['Interior_D.png', 'Engine_D.png', 'Chassis_D.png', 'Badge_SetA_D.png']:
        spec['alphaTest']=.5
    for kind in ['map', 'normalMap']:
        if kind in spec:
            file = texture_files[spec[kind]]
            if not file.is_file():raise FileNotFoundError(f'Missing donor texture: {file}')
            shutil.copyfile(file, WEB/file.name)
    materials['Donor_'+name] = spec
materials['Donor_RearGlass'] = dict(kind='glass',color=[.10,.12,.11])
materials['Donor_InstrumentBacking'] = dict(color=[.008,.009,.009],roughness=.8,metalness=0)
materials['Donor_ConsoleTrim'] = dict(color=[.014,.016,.014],roughness=.78,metalness=0)
materials['Donor_DoorSteel'] = dict(color=[.43,.44,.42],roughness=.42,metalness=.85)
materials['Donor_DoorLatch'] = dict(color=[.15,.16,.15],roughness=.34,metalness=.8)
materials['Donor_DoorRecess'] = dict(color=[.006,.007,.006],roughness=.7,metalness=0)
materials['Donor_Weatherstrip'] = dict(color=[.009,.010,.011],roughness=.82,metalness=0,detail='rubber')
materials['Donor_SeatLeather'] = dict(color=[.022,.023,.025],roughness=.64,metalness=0,detail='leather',cabinTrim='leather')
materials['Donor_SeatPiping'] = dict(color=[.012,.013,.014],roughness=.65,metalness=0,cabinTrim='piping')
materials['Donor_SeatControl'] = dict(color=[.035,.037,.040],roughness=.55,metalness=0)
materials['Donor_SeatHardware'] = dict(color=[.025,.028,.030],roughness=.45,metalness=.65)
materials['Donor_SeatThread'] = dict(color=[.055,.056,.058],roughness=.92,metalness=0)
materials['Donor_SeatMark'] = dict(color=[.7,.7,.67],roughness=.95,metalness=0,detail='seat_mark')
materials['Donor_BuckleRed'] = dict(color=[.32,.012,.006],roughness=.57,metalness=0)
materials['Donor_Carpet'] = dict(color=[.045,.047,.050],roughness=1,metalness=0,detail='carpet',cabinTrim='carpet')
materials['Donor_CabinPlastic'] = dict(color=[.012,.013,.015],roughness=.72,metalness=0,detail='rubber')
materials['Donor_Headliner'] = dict(color=[.20,.205,.20],roughness=1,metalness=0,detail='cloth')
materials['Donor_Webbing'] = dict(color=[.025,.029,.031],roughness=.88,metalness=0,detail='webbing')
materials['Donor_AerialSteel'] = dict(color=[.55,.56,.58],roughness=.24,metalness=.95)
materials['Donor_HeaterTrace'] = dict(color=[.12,.065,.028],roughness=.75,metalness=.35)
materials['Donor_PedalRubber'] = dict(color=[.024,.025,.027],roughness=.60,metalness=0,detail='rubber')
materials['Donor_Jamb'] = dict(color=[.025,.028,.027],roughness=.64,metalness=.05)
materials['Donor_ExhaustSteel'] = dict(color=[.10,.105,.11],roughness=.48,metalness=.85)
materials['Donor_ChassisGrey'] = dict(color=[.12,.125,.13],roughness=.68,metalness=.12)
materials['Donor_ZincBrackets'] = dict(color=[.38,.32,.19],roughness=.44,metalness=.9)
materials['Donor_RearBacking'] = dict(color=[.025,.028,.03],roughness=.72,metalness=.12)
materials['Donor_Drivetrain'] = dict(color=[.38,.39,.40],roughness=.65,metalness=.65,
    map='Engine_D.png',normalMap='Car_DMC_DeLorean_1983_Engine_NO.png',alphaTest=.5)
# The roof diffuser is a separate UV island in the interior atlas. Keep its
# lens pattern and dark border, but give it an independently driven emission.
interior_material = next(s for s in materials.values() if s.get('trim'))
materials['Donor_DomeLens'] = dict(interior_material, trim=False, kind='lamp',
    color=[.65,.65,.60], emissive=[1,.88,.65], emissiveMap=interior_material['map'])

# Match material-separated trim to the original door skin, not to an arbitrary
# rectangular selection that would take chunks of the roof or dashboard along.
paint = sources['DELOREAN:M_CarPaint_Max']
paint_faces = paint['loops'][paint['tris']]
door_vertices, _, _, door_outer = skin_geometry(paint, 2)
door_outline = door_vertices[door_outer]
def tree(ids):
    faces = paint_faces[np.isin(paint['comp'][paint_faces[:,0]],ids)]
    return BVHTree.FromPolygons(paint['v'].tolist(),faces.tolist(),all_triangles=True)
doors = tree([1,2]); fixed = tree([3,4,5,6,7])

def door_region(p):
    x,y,z=p; ay=abs(y)
    if not (-.737<x<.698 and .305<z<1.17 and ay>.13):return False
    # Inner cards sit further inward than the stainless skin.
    if z<.79 and ay<.635:return False
    if z>=.79 and ay<.45 and z<1.02:return False
    d=doors.find_nearest(Vector(p)); b=fixed.find_nearest(Vector(p))
    return d is not None and d[3]<.27 and (b is None or d[3]<b[3]+.008)


def classify(name, cid, center, lo, hi):
    x,y,z = center; side='L' if y>=0 else 'R'
    parent='Body'; semantic=None
    if 'LicensePlate' in name:return 'SKIP',None  # studio plate and rounded backing replace the blank donor plate
    if 'NickelRough' in name:return 'Body','exhaust_steel'
    if 'PlasticSmooth' in name and cid in [9,163]:return 'Body','jamb_closeout'
    if 'PlasticSmooth' in name and cid==128:return 'Body','rear_backing'
    # Original radiator and muffler supports are plated metal, not yellow
    # plastic. Keep a muted gold tint with metallic reflections.
    if 'PlasticSmooth' in name and cid in [11,12,13,14,18,19,20,21,147,148,149,150,151,154]:
        return 'Body','zinc_brackets'
    # The source puts the epoxy-coated frame on a white plastic swatch shared
    # with cabin trim. Separate whole frame components without tinting that trim.
    if 'PlasticSmooth' in name and cid in [5,6,10,105,108,109,110,115,116,117,118,119,
            122,123,124,126,127,129,132,133,134,135,136,138,139,142,143,152,153,159,160,168,169,170,171]:
        return 'Body','chassis_grey'
    if name.endswith('M_Engine_Max') and cid in [192,219,221]:return 'Body','drivetrain'
    if 'CarPaint' in name:
        return ('Hood' if cid==0 else 'Door_R' if cid==1 else 'Door_L' if cid==2 else 'Body'),None
    if 'WindowFront' in name:
        if cid in [2,4]:return 'Door_R','glass_toll_R'
        if cid in [7,8]:return 'Door_L','glass_toll_L'
        if cid in [3,5]:return 'Door_R','glass_door_R'
        if cid in [6,9]:return 'Door_L','glass_door_L'
        return 'Body',None
    if 'PlasticSmooth' in name and cid<=101 and lo[0]>.66 and lo[2]>.76 and hi[2]<.865 and hi[1]<.70 and lo[1]>-.71:return 'SKIP',None  # static donor wipers; animated replacements follow the windshield.
    if 'PlasticRough' in name and cid in [121,122,123,124,125,126]:return 'EngineLid',None
    if 'Chassis' in name and cid in [358,359,360,362]:return 'Hood',None
    if 'GrilleA' in name:return 'EngineLid',None
    if 'PlasticSmooth' in name and cid in [87,125]:return 'Door_'+side,None
    if 'GlassOpaque' in name:
        return ('Door_'+side if abs(y)>.7 else 'Body'),None
    if 'Interior' in name:
        # Original door pulls remained static beside the seats; replacements
        # already follow their doors. Belts and seat adjusters have detailed replacements.
        if cid in [31,32,33,69,70,71,72,79,128,129,130,131,139,148,149,155,157,158,159,167,169]:return 'SKIP',None
        if cid in [1,16,143,150,151,152,153,154,163,164,170,171]:return 'SKIP',None  # seats, release handles and buckles rebuilt from studio 12
        if cid in [94,95,96,97,98,99]:return 'SKIP',None  # physical duct throats and pedal pads replace flat cards
        if cid==29:return 'Body','carpet'
        # Sun visors and their clips are mounted to the fixed windshield header.
        if cid in [35,36,37,38,39,40,42,43,44,45]:return 'Body','sunvisors'
        # Seat-belt anchors, seat adjusters and dashboard end trim stay in the
        # cabin even where they sit close to the outer door skin.
        if cid in [34,126,182]:return 'Body',None
        if cid==41:return 'Body','cabin_lens'
        if cid==115:return 'Body','gauge_legend'  # instrument printing must not lift with the nearby door
        if cid==121:return 'Body','gauge_backplate'  # erase baked gauges behind the live instrument face
        if cid in [15,53,56]:return 'Body','console_trim'
        if cid==177:return 'SKIP',None  # rounded knob and engraved shift pattern in console.js
        if cid in [84,85,86,87,92,93]:return 'SKIP',None  # replaced by the high-resolution radio face and controls
        # Exact disconnected control assemblies, rebuilt with rounded geometry
        # and high-resolution printing in console.js. Keep the surrounding trim.
        if cid in [60,61,62,63,64,65,66,67,80,81,82,83,89,90,91,100,101,102,103,104,178,179,180,181]:return 'SKIP',None
        if cid==105:return 'Pedal_Clutch',None
        if cid==106:return 'Pedal_Brake',None
        if cid==107:return 'Pedal_Gas',None
        if cid==50:return 'SteeringWheel',None
        if cid==68:return 'Shifter','gear_boot'
        if cid in [124,125]:return 'Handbrake',None
        if lo[0]<-.738 or hi[0]>.700 or lo[2]<.305 or lo[0]>.52:return 'Body',None
        if hi[2]<.40 and max(abs(lo[1]),abs(hi[1]))<.70:return 'Body',None
    if 'LGlass' in name:
        if cid in [61,62]:return 'Body','rear_window'
        if x>1.9:semantic=('hl_bulb_Lo' if abs(y)>.55 else 'hl_bulb_Hi') if z>.51 else 'turn_front'
        elif x>1.5:semantic='marker_front'
        elif x<-1.9:semantic='plate_lenses' if abs(y)<.2 else 'tl_rev' if abs(y)<.335 else 'tl_turn' if abs(y)>.59 else 'tl_tail'
        elif x<-1.5:semantic='marker_rear'
        return 'Body',semantic
    if name.endswith('M_Engine_Max') or name.endswith('M_Chassis_Max'):return 'Body',None
    if 'PlasticSmooth' in name and cid in [22,44,48,62]:return 'Body',None
    if door_region(center): parent='Door_'+side
    return parent,semantic

# Save the source data before removing the FBX hierarchy.
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
nodes={}
def node(name,loc=(0,0,0),parent=None,rot=None):
    o=bpy.data.objects.new(name,None);scene.collection.objects.link(o)
    o.location=loc
    if rot is not None:o.rotation_euler=rot
    if parent:o.parent=nodes[parent]
    nodes[name]=o;return o
node('Car');node('Body',parent='Car')
# Source roof lens centre, with the light just below the diffuser (Z up here).
node('LP_Cabin',(.038745,-.000233,1.06223),'Body')
for side,sign in [('L',1),('R',-1)]:
    node('Door_'+side+'_Pivot',(0,sign*.135,HINGE_Z),'Body',(0,np.arctan(HINGE_SLOPE),0))
bpy.context.view_layer.update()
for side,sign in [('L',1),('R',-1)]:
    node('StrutBody_'+side,BODY_BALL*[1,sign,1],'Body')
    parent='Door_'+side+'_Pivot'
    local=nodes[parent].matrix_world.inverted()@Vector(DOOR_BALL*[1,sign,1])
    node('StrutDoor_'+side,local,parent)
    local=nodes[parent].matrix_world.inverted()@Vector(PULL_ANCHOR * [1,sign,1])
    node('DoorPull_'+side+'_Pivot',local,parent)
node('Hood_Pivot',(.745,0,.810),'Body');node('EngineLid_Pivot',(-.902,0,1.146),'Body')
node('SteeringWheel_Pivot',(.192,.367,.715),'Body')
angle=np.deg2rad(18)
nodes['SteeringWheel_Pivot'].rotation_euler=Matrix(((np.sin(angle),0,np.cos(angle)),(0,1,0),(-np.cos(angle),0,np.sin(angle)))).transposed().to_euler()
node('Shifter_Pivot',(.14,.02,.53),'Body');node('Handbrake_Pivot',(.23,.685,.435),'Body')
for name,y in [('Clutch',.44),('Brake',.315),('Gas',.21)]:node('Pedal_'+name+'_Pivot',(.685,y,.60),'Body')
# Dynamic dashboard/display anchors use the same local axes as the original rig.
node('GaugeFace_Pivot',(.318,.369,.773),'Body')
angle=np.deg2rad(14)
nodes['GaugeFace_Pivot'].rotation_euler=Matrix(((0,-1,0),(np.sin(angle),0,np.cos(angle)),(-np.cos(angle),0,np.sin(angle)))).transposed().to_euler()
node('ClockFace_Pivot',(.273,-.036,.521),'Body')
node('RadioFace_Pivot',(.364,.0107,.6406),'Body')
nodes['RadioFace_Pivot'].rotation_euler=Matrix(((0,-1,0),(.224,0,.97459),(-.97459,0,.224))).transposed().to_euler()
for k,loc in {'FL':(1.243,.78,.295),'FR':(1.243,-.78,.295),'RL':(-1.191,.79,.332),'RR':(-1.191,-.79,.332)}.items():node('WheelPos_'+k,loc,'Car')
for side,sign in [('L',1),('R',-1)]:
    for name,loc in {'HeadLo':(2.003,.638,.594),'HeadHi':(2.014,.454,.596),'TurnF':(2.045,.504,.461),'TurnR':(-2.015,.67,.78),'Tail':(-2.02,.47,.78),'Rev':(-2.025,.308,.78)}.items():node('LP_'+name+'_'+side,(loc[0],sign*loc[1],loc[2]),'Body')
bpy.context.view_layer.update()
mesh_materials={}
def material(name):
    if name not in mesh_materials:
        m=bpy.data.materials.new(name);m.use_nodes=True;mesh_materials[name]=m
    return mesh_materials[name]

def make_mesh(name,v,n,uv,parent,mat):
    if mat=='Decal_Plate':
        # The shared canvas uses flipY=true, unlike the imported donor images.
        uv=np.column_stack([.5-v[:,1]/.3048,.5-(v-[-2.014,0,.776])@np.array([.28,0,.96])/.1524])
    if mat=='Donor_SeatMark':
        uv=seat_badge_uv(v)
    if mat in ['Donor_SeatLeather','Donor_Carpet','Donor_Weatherstrip','Donor_CabinPlastic','Donor_Headliner','Donor_Webbing','Donor_PedalRubber']:
        # Metre UVs: one consistent physical grain size on every generated part.
        axes=np.argmax(np.abs(n.reshape(-1,3,3).mean(axis=1)),axis=1)
        uv=np.empty((len(v),2))
        for axis,pair in [(0,[1,2]),(1,[0,2]),(2,[0,1])]:
            mask=np.repeat(axes==axis,3);uv[mask]=v[mask][:,pair]
    # Preserve split normals and UV seams while joining identical corners.
    key=np.column_stack([v,np.round(n,6),uv]);_,first,inv=np.unique(key,axis=0,return_index=True,return_inverse=True)
    v=v[first];n=n[first];uv=uv[first];f=inv.reshape(-1,3)
    me=bpy.data.meshes.new(name);me.from_pydata(v.tolist(),[],f.tolist());me.update()
    for poly in me.polygons:poly.use_smooth=True
    me.normals_split_custom_set_from_vertices(n)
    layer=me.uv_layers.new();layer.data.foreach_set('uv',uv[f].astype(np.float32).ravel())
    me.materials.append(material(mat));o=bpy.data.objects.new(name,me);scene.collection.objects.link(o)
    o.parent=nodes[parent];o.matrix_parent_inverse=o.parent.matrix_world.inverted()
    return o

def header_corner(jamb, side):
    """Close the small gap between the fixed header, A-pillar and jamb return.

    Use only existing fixed trim and jamb vertices. Their local convex envelope
    forms a closed backing behind the corner, without borrowing moving door
    geometry or bridging across the windshield opening.
    """
    fixed = [v for (parent, name, _), pieces in buckets.items()
             if parent == 'Body' and name.startswith(('donor_M_Interior_Max_', 'donor_M_Opaque_Plastic'))
             for v, _, _ in pieces]
    points = np.concatenate(fixed+[jamb])
    y = points[:, 1]*(1 if side=='L' else -1)
    mask = ((points[:, 0]>-.04)&(points[:, 0]<.12)&(y>.45)&(y<.56)
            &(points[:, 2]>1.03)&(points[:, 2]<1.135))
    points = np.unique(np.round(points[mask], 6), axis=0)
    if len(points)<8:
        raise ValueError('Missing fixed windshield-header corner geometry')
    bm = bmesh.new()
    try:
        for point in points:
            bm.verts.new(point)
        bmesh.ops.convex_hull(bm, input=list(bm.verts), use_existing_faces=False)
        bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bmesh.ops.triangulate(bm, faces=list(bm.faces))
        bm.normal_update()
        if any(not edge.is_manifold for edge in bm.edges):
            raise ValueError('Windshield-header corner is not closed')
        v = np.array([vert.co[:] for face in bm.faces for vert in face.verts])
        n = np.array([vert.normal[:] for face in bm.faces for vert in face.verts])
    finally:
        bm.free()
    return v, n

def round_steering_wheel(o):
    """Refine the donor's faceted wheel without splitting its UV seams open."""
    me = o.data
    bm = bmesh.new()
    bm.from_mesh(me)
    # Export corners are split by normals and UVs. Subdivision needs connected
    # geometry; UVs remain per loop, so welding positions preserves the atlas.
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=0.00001)
    bmesh.ops.join_triangles(bm, faces=list(bm.faces),
        angle_face_threshold=np.deg2rad(40), angle_shape_threshold=np.deg2rad(60),
        cmp_uvs=True)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()
    # Discard the source's hard facet normals; let the refined surface shade
    # continuously across the rim and padded spoke junctions.
    me.normals_split_custom_set([(0, 0, 0)] * len(me.loops))
    for poly in me.polygons:
        poly.use_smooth = True
    bpy.context.view_layer.objects.active = o
    modifier = o.modifiers.new('Rounded steering wheel', 'SUBSURF')
    modifier.levels = 2
    modifier.render_levels = 2
    bpy.ops.object.modifier_apply(modifier=modifier.name)

def roof_trim_face(v, n, uv, moving):
    """Trim the inner roof edge at its binding, preserving interpolated UVs."""
    if not (np.min(v[:,2])>1.04 and np.max(v[:,0])<0 and np.max(abs(v[:,1]))<.60):
        return v,n,uv
    if not moving:
        return v,n,uv
    side=np.sign(v[:,1].mean())
    polygon=np.column_stack([v,n,uv]);out=[]
    for a,b in zip(polygon,np.roll(polygon,-1,axis=0)):
        da=side*a[1]-.202;db=side*b[1]-.202
        if da>=0:out.append(a)
        if (da>=0)!=(db>=0):out.append(a+(b-a)*da/(da-db))
    if len(out)<3:return None
    out=np.array(out)
    tri=np.array([[out[0],out[j],out[j+1]] for j in range(1,len(out)-1)]).reshape(-1,8)
    normals=tri[:,3:6];normals/=np.maximum(np.linalg.norm(normals,axis=1,keepdims=True),1e-12)
    return tri[:,:3],normals,tri[:,6:]


buckets={};audit=[];outline_membership={}
wheel_names={
 'DELOREAN:M_Rim_Main_Max1':('F','rim'), 'DELOREAN:M_RimBadge_Max1':('F','badge'), 'polySurface1':('F','tyre'), 'polySurface500':('F','caliper'),
 'DELOREAN:M_Rim_Main_Max':('R','rim'), 'DELOREAN:M_RimBadge_Max':('R','badge'), 'polySurface333':('R','tyre'), 'polySurface668':('R','caliper')}
wheel_data=[]
for name,s in sources.items():
    if name in wheel_names:
        wheel_data.append((wheel_names[name],s));continue
    if not name.startswith('DELOREAN:M_') or 'Rim' in name:continue
    for cid in np.unique(s['comp']):
        ids=np.where(s['comp']==cid)[0];pts=s['v'][ids];center=pts.mean(0);lo=pts.min(0);hi=pts.max(0)
        parent,semantic=classify(name,int(cid),center,lo,hi)
        ti=np.where(s['comp'][s['loops'][s['tris'][:,0]]]==cid)[0]
        if parent=='SKIP':continue
        for i in ti:
            loops=s['tris'][i];v=s['v'][s['loops'][loops]]
            pp=parent
            surface=None
            detail_label=None
            # FBX UV islands preserve the actual trim seams. Keep each whole
            # surface rigid; per-triangle spatial cuts leave sawteeth when open.
            if 'Interior' in name and cid==0:
                island=int(s['islands'][s['loops'][loops[0]]])
                # Thin atlas strips at the old open skin perimeter are replaced
                # by the continuous steel box; retaining both creates overlaps.
                if (1366<=island<=1380 or 1387<=island<=1421 or
                    1477<=island<=1509 or 1525<=island<=1541 or island in
                    [1544,1581,1547,1863,1905,1909,1910,1913,1914,2194,2195,2199,2200,2203,2204]):continue
                ip=s['v'][s['islands']==island]
                a,b=ip.min(0),ip.max(0); c=ip.mean(0)
                ay=np.abs(ip[:,1]); z=ip[:,2]
                inner=np.where(z<.79,.635,np.where(z<1.02,.45,.13))
                if island not in outline_membership:
                    outline_membership[island] = bool(np.all(contains_outline(ip, door_outline)))
                moving=(a[0]>-.738 and b[0]<.700 and a[2]>.305 and b[2]<1.17
                        and np.all(ay>inner) and not (b[0]>.52 and a[2]<.73)
                        and outline_membership[island])
                pp='Door_'+('L' if c[1]>=0 else 'R') if moving else 'Body'
                if a[0]>-1.91 and b[0]<-.89 and a[2]>.885 and np.max(ay)<.61:pp='EngineLid'
                if island in [1957,1960,1961,1980,1983,1985,1988,1989,1992,1995]:surface='Donor_Carpet'
                if a[2]>1.035 and b[0]<.14 and a[0]>-.73 and np.max(ay)<.57:surface='Donor_Headliner'
                # These narrow returns share the fixed windshield-header edge
                # (island 556 and its mirror), not the upholstered door panel.
                if island in [573,814]:pp='Body'
                # The dashboard's end cheeks surround the fixed air ducts.
                # Their proximity to the door must not make them lift with it.
                if island in [423,426,553,1621,1978]:
                    pp='Body'; surface='Donor_SeatLeather'
                    detail_label='dash_end_cheeks'
            mat='Donor_'+s['materials'][s['mats'][i]]
            if surface:mat=surface
            if semantic=='rear_window':mat='Donor_RearGlass'
            if semantic=='cabin_lens':mat='Donor_DomeLens'
            if semantic=='gauge_backplate':mat='Donor_InstrumentBacking'
            if semantic=='console_trim':mat='Donor_ConsoleTrim'
            if semantic=='exhaust_steel':mat='Donor_ExhaustSteel'
            if semantic=='chassis_grey':mat='Donor_ChassisGrey'
            if semantic=='drivetrain':mat='Donor_Drivetrain'
            if semantic=='jamb_closeout':mat='Donor_Jamb'
            if semantic=='rear_backing':mat='Donor_RearBacking'
            if semantic=='zinc_brackets':mat='Donor_ZincBrackets'
            if semantic=='carpet':mat='Donor_Carpet'
            if semantic=='webbing':mat='Donor_Webbing'
            label=detail_label or ('turn_front_bulb' if semantic=='turn_front' and 'phong16' in mat else semantic) or ('donor_'+name.split(':')[-1]+'_'+pp)
            key=(pp,label,mat)
            face=(v,s['n'][loops],s['uv'][loops])
            if 'Interior' in name and cid==0:
                # The old fixed roof lip straddled the hinge line and poked
                # through the moving flange. Keep it inside the roof channel.
                if pp=='Body' and island in [1351,1355,1422,1441]:
                    v=v.copy();mask=(abs(v[:,1])<.18)&(v[:,2]>1.12)
                    v[mask,1]=np.sign(v[mask,1])*np.minimum(abs(v[mask,1]),.128)
                    face=(v,s['n'][loops],s['uv'][loops])
                face=roof_trim_face(*face,pp.startswith('Door_'))
            if face is not None:buckets.setdefault(key,[]).append(face)
            if semantic=='marker_front':
                mv=v[::-1]*[1,-1,1]; mn=s['n'][loops][::-1]*[1,-1,1]
                buckets[key].append((mv,mn,s['uv'][loops][::-1]))
        audit.append(dict(source=name,component=int(cid),parent=parent,semantic=semantic,triangles=len(ti)))

for (parent,name,mat),triangles in buckets.items():
    v,n,uv=(np.concatenate([t[i]for t in triangles])for i in range(3))
    pn=parent+'_Pivot' if parent not in ['Body'] else parent
    o = make_mesh(name,v,n,uv,pn,mat)
    if parent == 'SteeringWheel':
        round_steering_wheel(o)
    if parent == 'Shifter':
        round_steering_wheel(o)

cabin_materials={'leather':'Donor_SeatLeather','piping':'Donor_SeatPiping',
    'webbing':'Donor_Webbing','control':'Donor_SeatControl','hardware':'Donor_SeatHardware','recess':'Donor_DoorRecess',
    'thread':'Donor_SeatThread','plastic':'Donor_CabinPlastic','metal':'Donor_DoorLatch','carpet':'Donor_Carpet','badge':'Donor_SeatMark','red':'Donor_BuckleRed','plate':'Decal_Plate'}
cabin_materials.update(rubber='Donor_Weatherstrip',bright='Donor_AerialSteel',conductor='Donor_HeaterTrace',grip='Donor_PedalRubber')
for assembly,parts in [('seat',seats()),('belts',seat_belts()),('rear_cabin',rear_cabin()),('sill',sill_details()),('rear_plate',rear_plate())]:
    for finish,(v,n) in parts.items():
        make_mesh(assembly+'_'+finish,v,n,np.zeros((len(v),2)),'Body',cabin_materials[finish])

interior = sources['DELOREAN:M_Interior_Max']
fittings = [('aerial', aerial(paint), 'Body'),
    ('heater', rear_heater(sources['DELOREAN:M_LGlass_InnerClear_Max']), 'Body'),
    ('louvre_fixings', louvre_fixings(sources['DELOREAN:M_Opaque_PlasticRoughBlack_Max']), 'EngineLid_Pivot'),
    ('dash_ducts', dash_ducts(interior), 'Body'), ('floor_mats', floor_mats(interior), 'Body')]
for component, parent in [(96,'Pedal_Brake_Pivot'), (97,'Pedal_Gas_Pivot'),
                           (98,'Body'), (99,'Pedal_Clutch_Pivot')]:
    fittings.append(('pedal_'+str(component), pedal(interior, component), parent))
for assembly, parts, parent in fittings:
    for finish, (v, n) in parts.items():
        make_mesh(assembly+'_'+finish,v,n,np.zeros((len(v),2)),parent,cabin_materials[finish])

glass=sources['DELOREAN:M_Glass_WindowFront_Max']
for component,parent,label,radius in [(0,'Body','windshield',.007),
        (5,'Door_R_Pivot','door_R',.004),(6,'Door_L_Pivot','door_L',.004),
        (4,'Door_R_Pivot','toll_R',.003),(8,'Door_L_Pivot','toll_L',.003),
        (11,'Body','quarter_L',.005),(13,'Body','quarter_R',.005)]:
    v,n=glass_seals(glass,component,radius)
    make_mesh('seal_'+label,v,n,np.zeros((len(v),2)),parent,'Donor_Weatherstrip')
v,n=glass_seals(sources['DELOREAN:M_LGlass_InnerClear_Max'],61,.006)
make_mesh('seal_rear_window',v,n,np.zeros((len(v),2)),'Body','Donor_Weatherstrip')
for side, component in [('L', 2), ('R', 1)]:
    v, n, skin = door_shell(paint, component)
    if side=='L':hinge_skin=skin
    for finish,(pv,pn) in door_pull(skin).items():
        make_mesh('pull_'+finish+'_'+side,pv,pn,np.zeros((len(pv),2)),
                  ('Door_' if finish in ['plastic','hardware'] else 'DoorPull_')+side+'_Pivot',cabin_materials[finish])
    for (parent,finish),(hv,hn) in attachments(hinge_skin,1 if side=='L' else -1).items():
        mat='Donor_DoorSteel' if finish=='steel' else 'Donor_DoorRecess'
        make_mesh('hinge_'+parent+'_'+finish+'_'+side,hv,hn,np.zeros((len(hv),2)),
                  'Body' if parent=='Body' else 'Door_'+side+'_Pivot',mat)
    for part,(jv,jn) in body_jamb(skin).items():
        mat={'shell':'Donor_Jamb','seal':'Donor_Weatherstrip','striker':'Donor_DoorLatch',
             'housing':'Donor_DoorRecess','flange':'Donor_DoorSteel'}[part]
        make_mesh('jamb_'+part+'_'+side,jv,jn,np.zeros((len(jv),2)),'Body',mat)
        if part=='shell':
            cv,cn=header_corner(jv,side)
            make_mesh('header_corner_'+side,cv,cn,np.zeros((len(cv),2)),'Body','Donor_CabinPlastic')
    make_mesh('door_box_'+side, v, n, np.zeros((len(v),2)),
              'Door_'+side+'_Pivot', 'Donor_DoorSteel')
    for part,(v,n) in edge_details(skin).items():
        name = ('courtesy_' if part=='amber' else 'courtesy_rear_' if part=='red' else 'door_'+part+'_')+side
        mat = {'amber':'Lamp_Courtesy','red':'Lamp_MarkerRear','steel':'Donor_DoorSteel',
               'latch':'Donor_DoorLatch','housing':'Donor_DoorRecess','recess':'Donor_DoorRecess','seal':'Donor_Weatherstrip'}[part]
        make_mesh(name,v,n,np.zeros((len(v),2)),'Door_'+side+'_Pivot',mat)


config=dict(windshield=dict(bx=.82,bz=.79,nx=.383,nz=.924,wrap=.20),lowProfile=False,tollWindow=dict(lean=34,travel=.19),tyreRadius=dict(F=.295,R=.332),wheelbase=2.434,track=1.56,
    doorPull=dict(closedScale=PULL_CLOSED_SCALE,freeAngle=float(PULL_FREE_ANGLE)),
    cameraEyes=dict(driver=[-.27,1.005,-.40],passenger=[-.37,.995,.40]),
    dashboard=dict(center=[.35,.773,-.369],scale=.80,heightScale=.90),radio=dict(detailed=True),materials=materials,sourceSha256=FBX_SHA256)
(WEB/'config.json').write_text(json.dumps(config,indent=2)+'\n')
(OUT/'donor-rig-audit.json').write_text(json.dumps(audit,indent=2))

def export(path):
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True,export_normals=True,export_tangents=True,export_attributes=True,export_materials='EXPORT')
if '--no-ao' not in sys.argv:
    from donor_ao import bake
    bake(materials)
export(OUT/'donor-car.glb')
# Export wheel assemblies separately, following Car's existing axle/spin contract.
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False);nodes.clear()
for ax in ['F','R']:
    node('WheelAsm_'+ax);node('Wheel_'+ax,parent='WheelAsm_'+ax)
for (ax,kind),s in wheel_data:
    center=np.array([1.243,.78,.295] if ax=='F' else [-1.191,.79,.332])
    for mi in np.unique(s['mats']):
        loops=s['tris'][s['mats']==mi].ravel();v=s['v'][s['loops'][loops]]-center
        name=('Caliper_' if kind=='caliper' else 'Tyre_' if kind=='tyre' else 'Rim_' if kind=='rim' else 'RimBadge_')+ax
        parent='WheelAsm_'+ax if kind=='caliper' else 'Wheel_'+ax
        make_mesh(name,v,s['n'][loops],s['uv'][loops],parent,'Donor_'+s['materials'][mi])
export(OUT/'donor-wheels.glb')
print('Donor rig complete:',len(buckets),'mesh groups')
