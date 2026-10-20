import glob, os, sys, numpy as np, trimesh
OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
def col(n):
    if n.startswith(('turn_front', 'marker_front', 'tl_turn')): return [255, 120, 10, 255]
    if n.startswith(('tl_tail', 'marker_rear')): return [200, 10, 10, 255]
    if n.startswith(('tl_rev', 'hl_bulb')): return [240, 240, 240, 255]
    if n.startswith(('hl_lens',)): return [150, 160, 170, 255]
    if n.startswith(('hl_refl', 'badge_dmc', 'mirror_glass', 'exhaust')): return [235, 235, 235, 255]
    if n.startswith(('hl_bezel', 'grille', 'badge_plate', 'tl_housing', 'bpillar', 'mirror', 'liner', 'underbody')): return [15, 15, 15, 255]
    if n.startswith('glass'): return [20, 24, 30, 255]
    if n.startswith(('gasket', 'strip', 'rocker', 'lid')): return [18, 18, 18, 255]
    if n.startswith('bumper'): return [55, 57, 60, 255]
    return [200, 203, 207, 255]
scene = trimesh.Scene()
for f in sorted(glob.glob(f'{OUT}/*.npz')):
    n = os.path.basename(f)[:-4]
    d = np.load(f)
    V, F, N = d['V'], d['F'], d['N']
    Vg = np.stack([V[:, 0], V[:, 2], -V[:, 1]], 1)
    Ng = np.stack([N[:, 0], N[:, 2], -N[:, 1]], 1)
    m = trimesh.Trimesh(Vg, F, vertex_normals=Ng, process=False)
    m.visual = trimesh.visual.ColorVisuals(m, vertex_colors=np.tile(col(n), (len(Vg), 1)))
    scene.add_geometry(m, node_name=n, geom_name=n)
scene.export(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'wgltest', 'body.glb'))
print('exported')
