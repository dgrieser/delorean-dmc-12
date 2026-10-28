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
# The roof diffuser is a separate UV island in the interior atlas. Keep its
# lens pattern and dark border, but give it an independently driven emission.
interior_material = next(s for s in materials.values() if s.get('trim'))
materials['Donor_DomeLens'] = dict(interior_material, trim=False, kind='lamp',
    color=[.65,.65,.60], emissive=[1,.88,.65], emissiveMap=interior_material['map'])

# Match material-separated trim to the original door skin, not to an arbitrary
# rectangular selection that would take chunks of the roof or dashboard along.
paint = sources['DELOREAN:M_CarPaint_Max']
paint_faces = paint['loops'][paint['tris']]
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
        if cid==41:return 'Body','cabin_lens'
        if cid==121:return 'Body','gauge_backplate'  # erase baked gauges behind the live instrument face
        if cid in [15,53,56]:return 'Body','console_trim'
        if cid==177:return 'SKIP',None  # rounded knob and engraved shift pattern in console.js
        if cid in [84,85,86,87,92,93]:return 'SKIP',None  # replaced by the high-resolution radio face and controls
        # Exact disconnected control assemblies, rebuilt with rounded geometry
        # and high-resolution printing in console.js. Keep the surrounding trim.
        if cid in [60,61,62,63,64,65,66,67,80,81,82,83,89,90,91,100,101,102,103,104,178,179,180,181]:return 'SKIP',None
        if cid in [99,105]:return 'Pedal_Clutch',None
        if cid in [96,106]:return 'Pedal_Brake',None
        if cid in [97,107]:return 'Pedal_Gas',None
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
for side,sign in [('L',1),('R',-1)]:node('Door_'+side+'_Pivot',(0,sign*.135,1.147),'Body')
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

buckets={};audit=[]
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
            # FBX UV islands preserve the actual trim seams. Keep each whole
            # surface rigid; per-triangle spatial cuts leave sawteeth when open.
            if 'Interior' in name and cid==0:
                island=int(s['islands'][s['loops'][loops[0]]])
                ip=s['v'][s['islands']==island]
                a,b=ip.min(0),ip.max(0); c=ip.mean(0)
                ay=np.abs(ip[:,1]); z=ip[:,2]
                inner=np.where(z<.79,.635,np.where(z<1.02,.45,.13))
                moving=(a[0]>-.738 and b[0]<.700 and a[2]>.305 and b[2]<1.17
                        and np.all(ay>inner) and not (b[0]>.52 and a[2]<.73))
                pp='Door_'+('L' if c[1]>=0 else 'R') if moving else 'Body'
                if a[0]>-1.91 and b[0]<-.89 and a[2]>.885 and np.max(ay)<.61:pp='EngineLid'
            mat='Donor_'+s['materials'][s['mats'][i]]
            if semantic=='rear_window':mat='Donor_RearGlass'
            if semantic=='cabin_lens':mat='Donor_DomeLens'
            if semantic=='gauge_backplate':mat='Donor_InstrumentBacking'
            if semantic=='console_trim':mat='Donor_ConsoleTrim'
            label=('turn_front_bulb' if semantic=='turn_front' and 'phong16' in mat else semantic) or ('donor_'+name.split(':')[-1]+'_'+pp)
            key=(pp,label,mat)
            buckets.setdefault(key,[]).append((v,s['n'][loops],s['uv'][loops]))
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
# Door warning lamps are a frozen extract of our procedural car. All other
# moving geometry, including the pedals, comes from the donor.
lamps=np.load(ROOT/'tools/model/assets/donor_lamps.npz')
for name,parent in [('courtesy_L','Door_L_Pivot'),('courtesy_R','Door_R_Pivot'),('courtesy_rear_L','Door_L_Pivot'),('courtesy_rear_R','Door_R_Pivot')]:
    v,f,n=(lamps[name+'_'+key] for key in ['V','F','N'])
    v=v.copy();v[:,1]-=.06*(1 if name.endswith('_L') else -1)
    make_mesh(name,v[f].reshape(-1,3),n[f].reshape(-1,3),np.zeros((f.size,2)),parent,
              'Lamp_MarkerRear' if 'rear' in name else 'Lamp_Courtesy')


config=dict(windshield=dict(bx=.82,bz=.79,nx=.383,nz=.924,wrap=.20),lowProfile=False,tollWindow=dict(lean=34,travel=.19),tyreRadius=dict(F=.295,R=.332),wheelbase=2.434,track=1.56,
    dashboard=dict(center=[.35,.773,-.369],scale=.80,heightScale=.90),radio=dict(detailed=True),materials=materials,sourceSha256=FBX_SHA256)
(WEB/'config.json').write_text(json.dumps(config,indent=2)+'\n')
(OUT/'donor-rig-audit.json').write_text(json.dumps(audit,indent=2))

def export(path):
    bpy.context.view_layer.update()
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',export_yup=True,export_normals=True,export_tangents=True,export_materials='EXPORT')
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
