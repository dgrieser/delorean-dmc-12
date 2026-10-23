"""Glass, rubber gaskets and the black side strips as projected patches on the shell."""
import os, sys, time
import numpy as np
import body as B
from patch import patch, region_outline, offset_poly, project, resample_poly
from extract import clip_level, sdf_normals

OUT = os.environ.get('OUT', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'out'))
os.makedirs(OUT, exist_ok=True)
shell = B.shell


def save(name, V, F, N):
    np.savez_compressed(f'{OUT}/{name}.npz', V=V.astype(np.float32), F=F.astype(np.int32), N=N.astype(np.float32))
    print(f'{name}: {len(V)} verts {len(F)} faces', flush=True)


def mirror(V, F, N):
    V2 = V * [1, -1, 1]
    N2 = N * [1, -1, 1]
    return V2, F[:, [0, 2, 1]], N2


def windshield():
    # Include the full raked pane up to the roof; the old X=0.20 bound cut its header off.
    lo, hi = (-0.15, -0.85), (0.95, 0.85)
    out = region_outline(shell, B.r_windshield, ('X', 'Y'), 'Z', 1, lo, hi, res=0.004)
    if np.any(out.min(0) < np.asarray(lo) + 0.008) or np.any(out.max(0) > np.asarray(hi) - 0.008):
        raise ValueError('Windscreen outline reaches its sampling bounds; enlarge them before building glass')
    glass = offset_poly(out, 0.006)
    V, F, N = patch(shell, glass, ('X', 'Y'), 'Z', 1, offset=-0.0035, step=0.02)
    save('glass_windshield', V, F, N)
    outer = offset_poly(out, 0.014)
    inner = offset_poly(out, -0.009)
    V, F, N = patch(shell, outer, ('X', 'Y'), 'Z', 1, offset=-0.0008, step=0.008, holes=[inner], thickness=0.004)
    save('gasket_windshield', V, F, N)
    # black ceramic frit band round the glass (~4.5 cm along the pillars and header, as the top
    # view shows), printed on the inside face
    frit_in = region_outline(shell, lambda X, Y, Z: B.r_windshield(X, Y, Z) + 0.045, ('X', 'Y'), 'Z', 1,
                             lo, hi, res=0.004)
    V, F, N = patch(shell, glass, ('X', 'Y'), 'Z', 1, offset=-0.0042, step=0.012, holes=[frit_in])
    save('frit_windshield', V, F, N)
    return out


TOLL = np.array([(-0.12, 0.856), (0.20, 0.856), (0.20, 0.930), (-0.12, 0.930)])


def door_glass():
    from patch import round_poly
    pts = B.DOOR_GLASS_POLY
    toll = round_poly(TOLL, 0.014)
    for side, tag in [(1, 'L'), (-1, 'R')]:
        V, F, N = patch(shell, offset_poly(pts, 0.006), ('X', 'Z'), 'Y', side, offset=-0.0035, step=0.016,
                        holes=[offset_poly(toll, 0.002)])
        save(f'glass_door_{tag}', V, F, N)
        # toll window pane (slides down into the door) + its black surround on the fixed glass
        V, F, N = patch(shell, offset_poly(toll, 0.006), ('X', 'Z'), 'Y', side, offset=-0.0055, step=0.012)
        save(f'glass_toll_{tag}', V, F, N)
        V, F, N = patch(shell, offset_poly(toll, 0.011), ('X', 'Z'), 'Y', side, offset=-0.002, step=0.006,
                        holes=[offset_poly(toll, 0.0015)], thickness=0.003)
        save(f'toll_frame_{tag}', V, F, N)
        # The rubber seal sits proud of the rolled steel edge, including the curved header.
        V, F, N = patch(shell, offset_poly(pts, B.DOOR_SEAL_OUTSET), ('X', 'Z'), 'Y', side,
                        offset=B.DOOR_SEAL_OFFSET, step=0.008,
                        holes=[offset_poly(pts, -B.DOOR_SEAL_INSET)], thickness=0.004)
        save(f'gasket_door_{tag}', V, F, N)


def quarter_glass():
    pts = B.QUARTER_POLY
    for side, tag in [(1, 'L'), (-1, 'R')]:
        V, F, N = patch(shell, offset_poly(pts, 0.006), ('X', 'Z'), 'Y', side, offset=-0.003, step=0.02)
        # Glass ends under the curved divider; the rear tip is a recessed finned insert.
        V, F = clip_level(V, F, lambda x, y, z: x - B.quarter_vent_split(z) + 0.001)
        N = sdf_normals(shell, V)
        save(f'glass_quarter_{tag}', V, F, N)
        V, F, N = patch(shell, offset_poly(pts, 0.012), ('X', 'Z'), 'Y', side, offset=-0.0008, step=0.008,
                        holes=[offset_poly(pts, -0.007)], thickness=0.004)
        # Line the inner opening too: its rolled steel edge was visible through the glass.
        ring = project(shell, resample_poly(offset_poly(pts, -0.007), 0.008), ('X', 'Z'), 'Y', side)
        normals = sdf_normals(shell, ring)
        outer, inner = ring - normals * 0.0008, ring - normals * 0.020
        k = np.arange(len(ring))
        j = (k + 1) % len(ring)
        walls = np.concatenate([np.stack([k, j, j + len(ring)], 1),
                                np.stack([k, j + len(ring), k + len(ring)], 1)])
        wall_v = np.concatenate([outer, inner])
        wall_n = np.cross(np.roll(outer, -1, axis=0) - outer, inner - outer)
        wall_n /= np.maximum(np.linalg.norm(wall_n, axis=1, keepdims=True), 1e-12)
        # Face the lining into the opening on either side of the car.
        if np.mean(np.sum(wall_n * (outer.mean(axis=0) - outer), axis=1)) < 0:
            walls = walls[:, [0, 2, 1]]
            wall_n = -wall_n
        F = np.concatenate([F, walls + len(V)])
        V = np.concatenate([V, wall_v])
        N = np.concatenate([N, wall_n, wall_n])
        save(f'gasket_quarter_{tag}', V, F, N)


def strips():
    """Black rubbing strip on the side crease; split into fender / door / quarter pieces."""
    def band(x0, x1, X):
        zc = B.z_crease(np.array([x0, x1]))
        return np.array([(x0, zc[0] - 0.0125), (x1, zc[1] - 0.0125), (x1, zc[1] + 0.0125), (x0, zc[0] + 0.0125)])
    # door edges at crease height
    zc = float(B.z_crease(np.array(0.6)))
    from sdf import poly2d
    xs = np.linspace(-0.9, 0.9, 1801)
    inside = poly2d(xs, np.full_like(xs, zc), B.DOOR_POLY) < 0
    xd0, xd1 = xs[inside].min() + 0.004, xs[inside].max() - 0.004
    # arch openings at strip height
    def arch_span(cx, cz, r, z):
        h = np.sqrt(max(r * r - (z - cz) ** 2, 0.0))
        return cx - h, cx + h
    fa0, fa1 = arch_span(B.X_FA, B.ARCH_ZF, B.ARCH_F, float(B.z_crease(np.array(B.X_FA))))
    ra0, ra1 = arch_span(B.X_RA, B.ARCH_ZR, B.ARCH_R, float(B.z_crease(np.array(B.X_RA))))
    # the front marker's black end piece runs from its lens on to the nose panel's seam
    tip1 = float(B.x_nose_seam(B.z_crease(np.array(1.80)))) - 0.005
    # Continue the black carrier under the amber lens; exposed steel here washes it out
    # and makes the marker look detached from the strip in the side view.
    segs = {'fender': (xd1 + 0.008, fa0 - 0.012), 'nose': (fa1 + 0.012, 1.788), 'tip': (1.788, tip1), 'door': (xd0, xd1),
            'quarter': (ra1 + 0.012, xd0 - 0.008), 'rearcorner': (B.TAIL_SEAM + 0.004, ra0 - 0.012)}
    for side, tag in [(1, 'L'), (-1, 'R')]:
        for k, (a, b) in segs.items():
            pts = band(min(a, b), max(a, b), None)
            if k in ('fender', 'nose'):
                # The ends beside the front opening follow its arc instead of
                # stopping square, leaving a constant reveal around the pressed lip.
                near = b if k == 'fender' else a
                zc = float(B.z_crease(np.array(near)))
                zs = np.linspace(zc - 0.0125, zc + 0.0125, 9)
                radius = B.ARCH_F + 0.020
                dx = np.sqrt(np.maximum(radius**2 - (zs - B.ARCH_ZF)**2, 0.0))
                arc = np.column_stack([B.X_FA + (-dx if k == 'fender' else dx), zs])
                pts = np.vstack([pts[0], arc, pts[3]]) if k == 'fender' else np.vstack([arc[0], pts[1], pts[2], arc[:0:-1]])
            from patch import round_poly
            V, F, N = patch(shell, round_poly(pts, 0.003 if k in ('fender', 'nose') else 0.008), ('X', 'Z'), 'Y', side, offset=0.0035, step=0.01,
                            thickness=0.006)
            save(f'strip_{k}_{tag}', V, F, N)


if __name__ == '__main__':
    t = time.time()
    windshield()
    door_glass()
    quarter_glass()
    strips()
    print('trim done', time.time() - t)
