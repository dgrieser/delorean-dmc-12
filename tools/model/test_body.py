import os, time, sys, numpy as np, trimesh
from extract import extract, decimate, sdf_normals, orient_faces, project_to_surface
import body
h = float(sys.argv[1]) if len(sys.argv) > 1 else 0.008
parts = [('body', body.body, body.BODY_BMIN, body.BODY_BMAX, [210,212,215,255]),
         ('fbump', body.front_bumper, body.FBUMP_BMIN, body.FBUMP_BMAX, [60,62,64,255]),
         ('rbump', body.rear_bumper, body.RBUMP_BMIN, body.RBUMP_BMAX, [60,62,64,255])]
scene = trimesh.Scene()
for name, f, a, b, col in parts:
    t = time.time()
    V, F = extract(f, a, b, h, verbose=False)
    V, F = decimate(V, F, 0.7)
    V = project_to_surface(f, V, 1)
    N = sdf_normals(f, V)
    F = orient_faces(V, F, N)
    Vg = np.stack([V[:, 0], V[:, 2], -V[:, 1]], 1)
    Ng = np.stack([N[:, 0], N[:, 2], -N[:, 1]], 1)
    m = trimesh.Trimesh(Vg, F, vertex_normals=Ng, process=False)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.tile(col, (len(Vg), 1)))
    scene.add_geometry(m, node_name=name, geom_name=name)
    print(name, len(V), round(time.time() - t, 1))
scene.export(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wgltest', 'body.glb'))
