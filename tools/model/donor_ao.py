"""Bake contact shading for the imported car in closed and open door poses."""
import time
import bpy
import numpy as np
from mathutils import Matrix


def bake(materials, samples=48):
    scene=bpy.context.scene
    scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=samples
    scene.cycles.use_denoising=False
    if scene.world is None:scene.world=bpy.data.worlds.new('Donor bake world')
    scene.world.light_settings.distance=.42
    objects=[o for o in scene.objects if o.type=='MESH']
    def occluder(o):
        name=o.data.materials[0].name
        spec=materials.get(name,{})
        return spec.get('kind') not in ['glass','mirror','lamp'] and not name.startswith('Lamp_') and 'Grille' not in name and spec.get('detail')!='seat_mark'
    solid=[o for o in objects if occluder(o)]
    for tag,angle in [('_AO',0),('_AO2',69)]:
        vertices=[];faces=[];offsets=[];offset=0
        for o in solid:
            me=o.data;me.calc_loop_triangles();matrix=o.matrix_world.copy()
            parent=o.parent
            while parent:
                if parent.name.startswith('DoorPull_'):
                    sign=1 if '_L_' in parent.name else -1
                    pm=parent.matrix_world
                    matrix=pm@Matrix.Rotation(np.deg2rad(-angle*sign),4,'X')@pm.inverted()@matrix
                if parent.name in ['Door_L_Pivot','Door_R_Pivot']:
                    sign=1 if parent.name=='Door_L_Pivot' else -1
                    pm=parent.matrix_world
                    matrix=pm@Matrix.Rotation(np.deg2rad(angle*sign),4,'X')@pm.inverted()@matrix
                    break
                parent=parent.parent
            v=np.empty(len(me.vertices)*3,np.float32);me.vertices.foreach_get('co',v);v=v.reshape(-1,3)
            m=np.array(matrix);v=v@m[:3,:3].T+m[:3,3]
            f=np.array([t.vertices[:] for t in me.loop_triangles])
            remap=None
            if o.name in ['seat_leather','belts_webbing']:
                # Texture seams and thin ribbon edges split these vertices.
                # Weld only the bake proxy so those splits cannot become false
                # creases in its smooth normals or the AO smoothing pass.
                _,first,remap=np.unique(np.round(v,6),axis=0,return_index=True,return_inverse=True)
                v=v[first];f=remap[f]
            vertices.append(v);faces.append(f+offset)
            offsets.append((o,offset,len(v),remap));offset+=len(v)
        v=np.concatenate(vertices);f=np.concatenate(faces)
        mesh=bpy.data.meshes.new('Donor AO proxy');mesh.from_pydata(v.tolist(),[],f.tolist());mesh.update()
        for poly in mesh.polygons:poly.use_smooth=True
        mesh.materials.append(bpy.data.materials.new('Donor AO bake'))
        mesh.color_attributes.new('AO bake','FLOAT_COLOR','POINT')
        mesh.color_attributes.active_color=mesh.color_attributes['AO bake']
        proxy=bpy.data.objects.new('Donor AO proxy',mesh);scene.collection.objects.link(proxy)
        for o in objects:o.hide_render=True;o.hide_set(True)
        bpy.ops.object.select_all(action='DESELECT');proxy.select_set(True);bpy.context.view_layer.objects.active=proxy
        started=time.time();bpy.ops.object.bake(type='AO',target='VERTEX_COLORS',margin=0)
        buf=np.empty(len(v)*4,np.float32);mesh.color_attributes['AO bake'].data.foreach_get('color',buf)
        ao=buf[::4].astype(float)
        edges=np.concatenate([f[:,[0,1]],f[:,[1,2]],f[:,[2,0]]])
        deg=np.bincount(edges.ravel(),minlength=len(v))
        for _ in range(2):
            total=np.bincount(edges[:,0],ao[edges[:,1]],len(v))+np.bincount(edges[:,1],ao[edges[:,0]],len(v))
            ao=.5*ao+.5*np.where(deg>0,total/np.maximum(deg,1),ao)
        for o,start,count,remap in offsets:
            attr=o.data.attributes.new(tag,'FLOAT','POINT')
            values=ao[start:start+count]
            if remap is not None:values=values[remap]
            attr.data.foreach_set('value',values.astype(np.float32))
        for o in objects:o.hide_render=False;o.hide_set(False)
        bpy.data.objects.remove(proxy,do_unlink=True);bpy.data.meshes.remove(mesh)
        print('Donor occlusion',tag,len(v),'vertices',round(time.time()-started,1),'seconds',flush=True)
