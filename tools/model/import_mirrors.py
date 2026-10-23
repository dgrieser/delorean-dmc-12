"""Extract only the exterior mirrors from the supplied donor FBX, using Blender.

blender -b -P tools/model/import_mirrors.py -- /path/to/FINAL_MODEL_DMC12.fbx
The FBX is inside source/FINAL_MODEL_DMC12.zip in 1981-dmc-delorean.zip.
The checked-in NPZ files make normal builds independent of the full donor car.
"""
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np
from io_scene_fbx import import_fbx

FBX_SHA256 = '9ff4e8a6c1e2d9884f6670d7c20e38ea036275ec17f5ae1e9259297cc536f1b9'
SELECTION = {
    'housing': ('DELOREAN:M_Opaque_PlasticRoughBlack_Max',
                list(range(1067, 1087))+list(range(1122, 1157)), 2797),
    'glass': ('DELOREAN:M_GlassOpaque_Mirror_Max', [4, 5, 6], 112),
}


class Reporter:
    def report(self, kinds, message):
        print(kinds, message)


def components(mesh):
    parent = list(range(len(mesh.vertices)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for edge in mesh.edges:
        a, b = map(find, edge.vertices)
        parent[a] = b
    groups = {}
    for i in range(len(parent)):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def extract(path, output):
    # Component indices refer to this exact source, not arbitrary donor files.
    if hashlib.sha256(path.read_bytes()).hexdigest() != FBX_SHA256:
        raise ValueError('Unexpected FBX: this extractor is for FINAL_MODEL_DMC12.fbx from the supplied archive')
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # Direct loader avoids Blender 5's broken ImportFBX.files operator property.
    import_fbx.load(Reporter(), bpy.context, filepath=str(path))
    output.mkdir(parents=True, exist_ok=True)
    for part, (name, ids, expected_faces) in SELECTION.items():
        obj = bpy.data.objects[name]
        mesh = obj.data
        groups = components(mesh)
        vertices = {i for component in ids for i in groups[component]}
        base = {i for component in range(1122, 1157) for i in groups[component]} if part == 'housing' else set()
        mesh.calc_loop_triangles()
        loops = [i for tri in mesh.loop_triangles if all(v in vertices for v in tri.vertices) for i in tri.loops]
        if len(loops) != expected_faces*3:
            raise ValueError(f'{part}: incomplete mirror extraction')
        matrix = obj.matrix_world
        normal_matrix = matrix.to_3x3().inverted().transposed()
        # Donor body imported at 1/100 scale, with its nose along -Y.
        # This proper rotation has determinant +1, so winding stays unchanged.
        v = np.array([matrix @ mesh.vertices[mesh.loops[i].vertex_index].co for i in loops])*100
        v = v[:, [1, 0, 2]]*[-1, 1, 1]
        n = np.array([normal_matrix @ mesh.corner_normals[i].vector for i in loops])
        n = n[:, [1, 0, 2]]*[-1, 1, 1]
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-15)
        uv = np.array([mesh.uv_layers.active.data[i].uv for i in loops])
        fit = np.array([mesh.loops[i].vertex_index in base for i in loops])
        # Keep split normals/UV seams. No decimation, subdivision or remeshing.
        np.savez_compressed(output / f'mirror_{part}_source.npz', V=v,
                            F=np.arange(len(v)).reshape(-1, 3), N=n, UV=uv, FIT=fit)
        print(f'{part}: {len(v)} corner vertices, {len(v)//3} triangles')
    (output / 'mirrors.json').write_text(json.dumps({
        'source_archive': '1981-dmc-delorean.zip (supplied by user)',
        'archive_sha256': '7b4d01a7a130bc47cc4cd4340300e12eb7207b6a35ac2869f2b2b68fe8cdcec2',
        'source_fbx': 'source/FINAL_MODEL_DMC12.zip / FINAL_MODEL_DMC12.fbx',
        'fbx_sha256': FBX_SHA256,
        'selection': {part: {'object': name, 'components': ids, 'triangles': count}
                      for part, (name, ids, count) in SELECTION.items()},
        'coordinates': 'Body metres: X forward, Y left, Z up; source world vertices rotated (-Y,X,Z) and multiplied by 100.',
        'texture': {'file': 'Swatches_D.png', 'mirror_srgb': [18, 18, 18],
                    'note': 'All housing UV samples use one constant swatch. Material colour replaces the atlas; source UVs retained. Glass has no image texture.'},
        'fitting': 'Assembly aligned rigidly to the window, with only the base contact surface deformed. Housing and glass retain source geometry. Right side reflected from left.',
        'glass_shading': 'Source normals retained in NPZ. The build uses planar normals on the broad optical face to avoid reflections rippling across the smoothed rim.',
        'provenance': 'No author or license document was included in the supplied archive.'
    }, indent=2)+'\n')


if __name__ == '__main__':
    args = sys.argv[sys.argv.index('--')+1:]
    extract(Path(args[0]).resolve(), Path(__file__).with_name('assets'))
