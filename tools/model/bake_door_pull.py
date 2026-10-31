"""Bake the pinned leather loop used by donor_cabin.door_pull.

Run: blender -b -t 4 -P tools/model/bake_door_pull.py
Gravity/self-collision relaxation is baked once; the viewer only animates its anchor.
"""
import bpy, numpy as np, json
from pathlib import Path
bpy.ops.wm.read_factory_settings(use_empty=True)
rows,cols=81,5
t=np.linspace(0,2*np.pi,rows)
center=np.column_stack([np.zeros_like(t),.018*np.sin(t)+np.linspace(.003,-.003,rows),-.10*(1-np.cos(t))])
v=(center[:,None,:]+np.linspace(-.014,.014,cols)[None,:,None]*np.array([1,0,0])).reshape(-1,3)
f=[(i*cols+j,i*cols+j+1,(i+1)*cols+j+1,(i+1)*cols+j) for i in range(rows-1) for j in range(cols-1)]
me=bpy.data.meshes.new('Leather ribbon');me.from_pydata(v.tolist(),[],f);me.update();ob=bpy.data.objects.new('Pull strap',me);bpy.context.collection.objects.link(ob)
pins=ob.vertex_groups.new(name='Pinned ends');pins.add(list(range(cols*2))+list(range((rows-2)*cols,rows*cols)),1,'REPLACE')
cloth=ob.modifiers.new('Gravity relaxation','CLOTH');s=cloth.settings;s.quality=12;s.mass=.3;s.tension_stiffness=80;s.compression_stiffness=80;s.shear_stiffness=30;s.bending_stiffness=3;s.air_damping=5;s.vertex_group_mass=pins.name;s.pin_stiffness=1
cloth.collision_settings.use_self_collision=True;cloth.collision_settings.self_distance_min=.0012;cloth.collision_settings.self_friction=5
scene=bpy.context.scene;scene.render.fps=30;cloth.point_cache.frame_start=1;cloth.point_cache.frame_end=100
for frame in range(1,101):
 scene.frame_set(frame)
 if frame%20==0:print('cloth',frame,flush=True)
evaluated=ob.evaluated_get(bpy.context.evaluated_depsgraph_get());out=np.array([p.co[:] for p in evaluated.data.vertices]);print('bounds',out.min(0),out.max(0),flush=True)
# Remove residual sideways swing from this static bake. Paired loop halves
# share the clamp plane; retain the cloth-solved drop and rounded lower fold.
grid=out.reshape(rows,cols,3)
grid=(grid+grid[::-1]*[1,-1,1])/2
grid[:,:,0]=np.linspace(-.014,.014,cols)
out=grid.reshape(-1,3)
Path(__file__).with_name('door_pull_cloth.json').write_text(json.dumps({'rows':rows,'cols':cols,'vertices':np.round(out,7).tolist()},separators=(',',':'))+'\n')
