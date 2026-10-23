"""Mirrors extracted from the user-supplied 1981 DMC DeLorean model.

Keep the donor housing, glass, pivot and support. Fit only the mounting surface
against this car's door, then reflect the complete assembly for the other side.
The source meshes retain authored split normals and UVs; see assets/mirrors.json.
"""
from pathlib import Path
import numpy as np
import body as B

ASSETS = Path(__file__).with_name('assets')
ROOT_POINT = np.array([.42593198, .80886560, .81998308])
ROOT_NORMAL = np.array([.02928058, .82455177, .56502835])
# Y clearance matches the raised seal; keeps the visible base out of the skin.
CONTACT_Y_OFFSET = .003


def source(part):
    with np.load(ASSETS / f'mirror_{part}_source.npz') as data:
        return tuple(data[k].copy() for k in ('V', 'F', 'N'))


def skin_y(x, z):
    y = np.full_like(x, .80)
    for _ in range(12):
        d = B.flanks(x, y, z)
        g = (B.flanks(x, y+.0001, z)-B.flanks(x, y-.0001, z))/.0002
        y -= d/np.maximum(g, .2)
    return y


def mount_outline():
    from patch import offset_poly, resample_poly
    window = offset_poly(B.DOOR_GLASS_POLY, -B.DOOR_SEAL_INSET)
    z0 = window[:, 1].min()
    clipped = []
    def aft(p):
        return p[0]-.335-1.25*(p[1]-z0)
    for a, b in zip(window, np.roll(window, -1, axis=0)):
        da, db = aft(a), aft(b)
        if (da >= 0) != (db >= 0):
            clipped.append(a+da/(da-db)*(b-a))
        if db >= 0:
            clipped.append(b)
    return resample_poly(np.asarray(clipped), .004)


def root_transform():
    p = mount_outline()
    a = p[p[:, 0].argmax()]
    b = p[p[:, 1].argmax()]
    target = np.array([a[0], skin_y(a[0:1], a[1:2])[0]+CONTACT_Y_OFFSET, a[1]])
    top = np.array([b[0], skin_y(b[0:1], b[1:2])[0]+CONTACT_Y_OFFSET, b[1]])
    source_anchor = np.array([.541, .827, .790])
    source_top = np.array([.400, .762, .891])
    from extract import sdf_normals
    normal = sdf_normals(B.flanks, target[None])[0]
    def basis(edge, n):
        n = n/np.linalg.norm(n)
        e = edge-n*np.dot(edge, n)
        e /= np.linalg.norm(e)
        return np.column_stack([e, np.cross(n, e), n])
    rotation = basis(top-target, normal) @ basis(source_top-source_anchor, ROOT_NORMAL).T
    return source_anchor, target, rotation


def fitted_positions(v, fit, transform):
    anchor, target, rotation = transform
    out = (v-anchor) @ rotation.T+target
    # The donor base plane is matched rigidly to the window. Follow the door's
    # curvature only at the contact face.
    distance = (v-ROOT_POINT) @ ROOT_NORMAL
    t = np.clip((.025-distance)/.017, 0, 1)
    weight = t*t*(3-2*t)*fit
    on_plane = v-distance[:, None]*ROOT_NORMAL
    surface = (on_plane-anchor) @ rotation.T+target
    out[:, 1] += weight*(skin_y(surface[:, 0], surface[:, 2])+CONTACT_Y_OFFSET-surface[:, 1])
    return out


def fitted(part):
    v, f, n = source(part)
    if part == 'glass':
        # FBX normals were smoothed over the thin glass rim. Use the fitted
        # optical plane on the broad face so a flat mirror does not look dented.
        plane = np.linalg.svd(v-v.mean(0), full_matrices=False)[2][-1]
        if np.dot(plane, n.mean(0)) < 0:
            plane = -plane
        face = np.cross(v[f[:, 1]]-v[f[:, 0]], v[f[:, 2]]-v[f[:, 0]])
        face /= np.linalg.norm(face, axis=1, keepdims=True)
        n[np.unique(f[face @ plane > .94])] = plane
    with np.load(ASSETS / f'mirror_{part}_source.npz') as data:
        fit = data['FIT']
    transform = root_transform()
    # Preserve the head and glass geometry. Only the base receives
    # a smooth fitting deformation; transform its authored corner normals too.
    h = .00001
    jac = np.stack([(fitted_positions(v+np.eye(3)[i]*h, fit, transform)
                     - fitted_positions(v-np.eye(3)[i]*h, fit, transform))/(2*h) for i in range(3)], axis=-1)
    normal = np.linalg.solve(jac.transpose(0, 2, 1), n[..., None])[..., 0]
    normal /= np.linalg.norm(normal, axis=1, keepdims=True)
    positions = fitted_positions(v, fit, transform)
    # FBX corner attributes are stored unrolled in the source. Rejoin matching
    # corners so the AO bake sees a continuous surface, not isolated triangles.
    # Keep discontinuous normals split at the donor's hard edges.
    key = np.column_stack([positions, np.round(normal, 6)])
    _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
    return positions[first], inverse[f], normal[first]


def build():
    left = {'mirror_L': fitted('housing'), 'mirror_glass_L': fitted('glass')}
    result = dict(left)
    for name, (v, f, n) in left.items():
        result[name[:-1]+'R'] = (v*[1, -1, 1], f[:, [0, 2, 1]], n*[1, -1, 1])
    return result
