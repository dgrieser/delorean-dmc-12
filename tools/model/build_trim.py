"""Glass, rubber gaskets and the black side strips as projected patches on the shell."""
import os, sys, time
import numpy as np
import body as B
from patch import patch, region_outline, offset_poly

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
    out = region_outline(shell, B.r_windshield, ('X', 'Y'), 'Z', 1, (0.20, -0.85), (0.90, 0.85), res=0.004)
    glass = offset_poly(out, 0.006)
    V, F, N = patch(shell, glass, ('X', 'Y'), 'Z', 1, offset=-0.0035, step=0.02)
    save('glass_windshield', V, F, N)
    outer = offset_poly(out, 0.014)
    inner = offset_poly(out, -0.009)
    V, F, N = patch(shell, outer, ('X', 'Y'), 'Z', 1, offset=-0.0008, step=0.008, holes=[inner], thickness=0.004)
    save('gasket_windshield', V, F, N)
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
        V, F, N = patch(shell, offset_poly(pts, 0.013), ('X', 'Z'), 'Y', side, offset=-0.0008, step=0.008,
                        holes=[offset_poly(pts, -0.008)], thickness=0.004)
        save(f'gasket_door_{tag}', V, F, N)


def quarter_glass():
    pts = B.QUARTER_POLY
    for side, tag in [(1, 'L'), (-1, 'R')]:
        V, F, N = patch(shell, offset_poly(pts, 0.006), ('X', 'Z'), 'Y', side, offset=-0.003, step=0.02)
        save(f'glass_quarter_{tag}', V, F, N)
        V, F, N = patch(shell, offset_poly(pts, 0.012), ('X', 'Z'), 'Y', side, offset=-0.0008, step=0.008,
                        holes=[offset_poly(pts, -0.007)], thickness=0.004)
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
    segs = {'fender': (xd1 + 0.008, fa0 - 0.012), 'nose': (fa1 + 0.012, 1.575), 'door': (xd0, xd1),
            'quarter': (ra1 + 0.012, xd0 - 0.008), 'rearcorner': (-1.650, ra0 - 0.012)}
    for side, tag in [(1, 'L'), (-1, 'R')]:
        for k, (a, b) in segs.items():
            pts = band(min(a, b), max(a, b), None)
            from patch import round_poly
            V, F, N = patch(shell, round_poly(pts, 0.008), ('X', 'Z'), 'Y', side, offset=0.0035, step=0.01,
                            thickness=0.006)
            save(f'strip_{k}_{tag}', V, F, N)


if __name__ == '__main__':
    t = time.time()
    windshield()
    door_glass()
    quarter_glass()
    strips()
    print('trim done', time.time() - t)
