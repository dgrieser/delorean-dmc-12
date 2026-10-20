"""Calibrate the studio reference photos (ref/studio) against each other.

A bundle adjustment over the eight photos: per photo a pinhole camera (rotation, centre, focal
length; square pixels, centred principal point) and, shared by all photos, ~25 landmarks of the
car (lamp corners, indicators, side markers, the antenna base, mirror and windscreen corners, the
B-pillar vents, the wheel centres). Landmarks are mirror-symmetric pairs; the wheel centres sit
on the published wheelbase, which fixes the scale. The pixel observations below were read off
zoomed crops of the photos.

Writes tools/ref/cameras.json: per photo the camera in the car frame (X forward, Y left, Z up,
ground z = 0) and the matching three.js camera (position, quaternion, vertical fov) for
tools/ref/shots.mjs, plus the solved landmarks.

usage: python3 tools/ref/calibrate.py        (numpy, scipy)
"""
import json, os, sys
import numpy as np
from scipy.optimize import least_squares
from scipy.spatial.transform import Rotation as Rot

W, H = 2048, 1366
XA = 1.2065

# symmetric landmarks: (x, |y|, z) initial; suffix _R -> y<0, _L -> y>0
SYM = {
    'hl_o_ot': (2.03, 0.70, 0.61), 'hl_o_ob': (2.03, 0.70, 0.49),
    'hl_i_it': (2.03, 0.36, 0.61), 'hl_i_ib': (2.03, 0.36, 0.49),
    'ts_o': (2.10, 0.65, 0.45), 'ts_i': (2.10, 0.50, 0.45),
    'smf_f': (1.75, 0.92, 0.52), 'smf_r': (1.58, 0.92, 0.52),
    'smr_f': (-1.70, 0.92, 0.55), 'smr_r': (-1.85, 0.92, 0.55),
    'tl_ot': (-1.98, 0.78, 0.75), 'tl_ob': (-1.98, 0.80, 0.60), 'tl_it': (-1.98, 0.31, 0.76),
    'mir_ot': (0.55, 0.99, 0.92), 'hood_fc': (1.95, 0.75, 0.73), 'ws_t': (0.02, 0.51, 1.045),
    'tail_tc': (-1.92, 0.75, 0.82), 'bv_t': (-0.80, 0.70, 1.05), 'bv_b': (-0.75, 0.80, 0.80),
}
FREE = {'badge': (2.05, 0.0, 0.55), 'ant': (0.9, -0.75, 0.80)}
CENTRE = {'badge'}

OBS = {
 '07': {'hub_FR': (1538, 985), 'hub_RR': (479, 983), 'gnd_FR': (1538, 1105), 'gnd_RR': (479, 1108),
        'smf_f_R': (1798, 897), 'smf_r_R': (1707, 899), 'smr_r_R': (195, 880), 'smr_f_R': (278, 880),
        'ant': (1342, 780), 'hood_fc_R': (1860, 833), 'tail_tc_R': (205, 743), 'bv_t_R': (660, 664), 'bv_b_R': (637, 776)},
 '02': {'hl_o_ot_R': (499, 771), 'hl_o_ob_R': (499, 846), 'hl_i_it_R': (750, 772), 'hl_i_ib_R': (750, 845),
        'hl_i_it_L': (1285, 772), 'hl_i_ib_L': (1285, 845), 'hl_o_ot_L': (1538, 775), 'hl_o_ob_L': (1538, 848),
        'ts_o_R': (601, 915), 'ts_i_R': (709, 915), 'ts_i_L': (1328, 916), 'ts_o_L': (1437, 916),
        'badge': (1019, 815), 'ant': (519, 633), 'mir_ot_R': (432, 581), 'mir_ot_L': (1619, 578),
        'hood_fc_R': (488, 744), 'hood_fc_L': (1551, 746), },
 '01': {'hub_FR': (1026, 961), 'hub_RR': (349, 898), 'hl_o_ot_R': (1339, 796), 'hl_o_ob_R': (1340, 855),
        'hl_i_it_L': (1716, 776), 'hl_i_ib_L': (1716, 823), 'hl_o_ot_L': (1810, 774), 'hl_o_ob_L': (1810, 824),
        'badge': (1618, 813), 'smf_r_R': (1128, 857), 'smf_f_R': (1218, 868), 'ant': (882, 716), 'ws_t_R': (762, 577), 'ws_t_L': (1095, 586)},
 '03': {'hub_FL': (1307, 945), 'hl_o_ot_R': (301, 765), 'hl_o_ob_R': (301, 826), 'hl_i_it_R': (473, 763),
        'hl_i_ib_R': (473, 826), 'hl_i_it_L': (864, 747), 'hl_i_ib_L': (864, 811), 'hl_o_ot_L': (1059, 746),
        'hl_o_ob_L': (1059, 810), 'badge': (650, 790), 'ts_i_R': (425, 879), 'ts_i_L': (891, 871), 'ts_o_L': (979, 871),
        'smf_f_L': (1179, 830), 'smf_r_L': (1253, 822), 'ant': (613, 712), 'smr_f_L': (1840, 838)},
 '04': {'hub_FL': (1148, 980), 'hub_RL': (1568, 707), 'hl_o_ot_R': (273, 752), 'hl_o_ob_R': (275, 812),
        'hl_i_it_R': (408, 772), 'hl_i_ib_R': (408, 832), 'hl_i_it_L': (742, 862), 'hl_i_ib_L': (742, 917),
        'hl_o_ot_L': (915, 901), 'badge': (557, 859), 'ts_i_R': (365, 875), 'ts_i_L': (760, 984), 'ts_o_L': (837, 990),
        'smf_f_L': (1027, 962), 'smf_r_L': (1100, 922), 'ant': (611, 575), 'ws_t_R': (902, 416), 'ws_t_L': (1278, 470)},
 '05': {'hub_RL': (869, 943), 'hub_FL': (320, 834), 'tl_ot_L': (1264, 717), 'tl_it_L': (1431, 713), 'tl_ob_L': (1246, 799),
        'tl_it_R': (1658, 700), 'tl_ot_R': (1801, 698), 'tl_ob_R': (1826, 764), 'smr_f_L': (1027, 851), 'smr_r_L': (1118, 855)},
 '06': {'hub_RR': (1418, 930), 'hub_FR': (1737, 947), 'tl_ot_L': (361, 645), 'tl_ob_L': (324, 722), 'tl_it_L': (567, 641),
        'tl_it_R': (894, 632), 'tl_ot_R': (1115, 632), 'tl_ob_R': (1150, 711), 'smr_r_R': (1267, 777), 'smr_f_R': (1330, 778)},
 '08': {'hood_fc_R': (300, 414), 'hood_fc_L': (294, 960), 'ant': (693, 378), 'mir_ot_R': (889, 305), 'mir_ot_L': (870, 1094),
        'bv_t_R': (1350, 450), 'bv_b_R': (1352, 378), 'bv_t_L': (1341, 933), 'bv_b_L': (1341, 1025), 'ws_t_R': (995, 470), 'ws_t_L': (994, 899)},
}

# initial camera centres and look-at targets
CAM0 = {'07': ((0.03, -20, 0.96), (0.03, 0, 0.96)), '02': ((12, 0, 1.0), (0, 0, 0.6)),
        '01': ((8, -7, 1.5), (0.3, 0, 0.6)), '03': ((7, 5, 0.5), (0, 0, 0.8)), '04': ((7, 5, 4), (0, 0, 0.6)),
        '05': ((-8, 6, 2), (0, 0, 0.7)), '06': ((-7, -4, 0.4), (0, 0, 0.9)), '08': ((0, 0, 20), (0, 0, 0))}


def lookat(C, T, up=(0, 0, 1)):
    C, T = np.array(C, float), np.array(T, float)
    z = T - C; z /= np.linalg.norm(z)
    upv = np.array(up, float)
    if abs(z @ upv) > 0.99: upv = np.array([0, 1, 0.0])      # top view: image up = car right (-Y)
    x = np.cross(z, -upv); x /= np.linalg.norm(x)
    y = np.cross(z, x)
    return np.stack([x, y, z])                                # rows: camera axes in world


VIEWS = list(OBS)
SYMN = list(SYM); FREEN = list(FREE)


def unpack(p):
    cams = {}
    k = 0
    for v in VIEWS:
        cams[v] = (p[k:k + 3], p[k + 3:k + 6], p[k + 6]); k += 7
    pts = {}
    for n in SYMN:
        x, w, z = p[k:k + 3]; k += 3
        pts[n + '_R'] = np.array([x, -w, z]); pts[n + '_L'] = np.array([x, w, z])
    for n in FREEN:
        x, y, z = p[k:k + 3]; k += 3
        if n in CENTRE: y = 0.0
        pts[n] = np.array([x, y, z])
    hyF, hyR, rF, rR = p[k:k + 4]; k += 4
    pts['hub_FR'] = np.array([XA, -hyF, rF]); pts['hub_FL'] = np.array([XA, hyF, rF])
    pts['hub_RR'] = np.array([-XA, -hyR, rR]); pts['hub_RL'] = np.array([-XA, hyR, rR])
    pts['gnd_FR'] = np.array([XA, -hyF, 0.0]); pts['gnd_RR'] = np.array([-XA, -hyR, 0.0])
    return cams, pts


def project(cam, X):
    rv, C, f = cam
    R = Rot.from_rotvec(rv).as_matrix()
    q = (R @ (np.asarray(X) - C).T).T
    return np.stack([f * q[:, 0] / q[:, 2] + W / 2, f * q[:, 1] / q[:, 2] + H / 2], 1)


# camera centre priors (None = free): the side shot is a long lens (no far-side wheels show
# under the car), the photographer stands, the drone is above
CAM_PRIOR = {'07': ((0.0, -20.0, 0.95), (0.3, 0.5, 0.15)), '08': ((0.0, 0.0, 12.0), (0.5, 0.5, 2.0)), '06': ((None, None, 0.35), (1, 1, 0.2)),
             '03': ((None, None, 0.35), (1, 1, 0.2))}
PRIOR_SIG = 0.10            # metres, weak prior on the landmarks' starting guesses
WHEEL_PRIOR = (np.array([0.83, 0.84, 0.28, 0.29]), np.array([0.03, 0.03, 0.015, 0.015]))


def resid(p):
    cams, pts = unpack(p)
    r = []
    k = 7 * len(VIEWS)
    lm = p[k:k + 3 * (len(SYMN) + len(FREEN))]
    r.append(3.0 * (lm - P0_LM) / PRIOR_SIG)
    wv = p[-4:]
    r.append(3.0 * (wv - WHEEL_PRIOR[0]) / WHEEL_PRIOR[1])
    for v in VIEWS:
        C = cams[v][1]
        if v in CAM_PRIOR:
            c0, sig = CAM_PRIOR[v]
            for i in range(3):
                if c0[i] is not None: r.append(np.array([3.0 * (C[i] - c0[i]) / sig[i]]))
        if v == '08': r.append(np.array([300.0 * min(0.0, C[2] - 4.0)]))   # drone above the car
    return np.concatenate(r + [obs_resid(cams, pts)])


def obs_resid(cams, pts):
    r = []
    for v in VIEWS:
        names = list(OBS[v])
        uv = project(cams[v], np.array([pts[n] for n in names]))
        r.append((uv - np.array([OBS[v][n] for n in names])).ravel())
    return np.concatenate(r)


def init():
    p = []
    for v in VIEWS:
        C, T = CAM0[v]
        R = lookat(C, T)
        p += list(Rot.from_matrix(R).as_rotvec()) + list(C) + [5000.0 if v in ('07', '08') else 3000.0]
    for n in SYMN: p += list(SYM[n])
    for n in FREEN: p += list(FREE[n])
    p += [0.84, 0.84, 0.27, 0.28]
    return np.array(p)


P0_LM = None
if __name__ == '__main__':
    p0 = init()
    P0_LM = p0[7 * len(VIEWS):7 * len(VIEWS) + 3 * (len(SYMN) + len(FREEN))].copy()
    # stage 1: cameras only (landmarks fixed), stage 2: all
    ncam = 7 * len(VIEWS)
    _, pts0 = unpack(p0)
    pc = p0[:ncam].copy()
    for vi, v in enumerate(VIEWS):
        names = list(OBS[v])
        X = np.array([pts0[n] for n in names]); uv = np.array([OBS[v][n] for n in names], float)
        best = None
        if v == '08':
            pc[vi * 7 + 6] = 9000.0; pc[vi * 7 + 3:vi * 7 + 6] = (0, 0, 22.0)
            print('init 08 fixed'); continue
        for f in np.geomspace(1500, 40000, 40):
            k = vi * 7
            def rv(q, f=f):
                return (project((q[:3], q[3:6], f), X) - uv).ravel()
            q0 = pc[k:k + 6]
            sol = least_squares(rv, q0, loss='soft_l1', f_scale=20, max_nfev=2000)
            e = np.sqrt(np.mean(sol.fun ** 2))
            if best is None or e < best[0]: best = (e, sol.x, f)
        pc[vi * 7:vi * 7 + 6] = best[1]; pc[vi * 7 + 6] = best[2]
        print('init', v, round(best[0], 1), 'f', round(best[2]), 'C', np.round(best[1][3:6], 2))
    p1 = np.concatenate([pc, p0[ncam:]])
    s2 = least_squares(resid, p1, loss='linear', max_nfev=20000)
    p = s2.x
    cams, pts = unpack(p)
    r = obs_resid(cams, pts).reshape(-1, 2)
    i = 0
    print('per-observation residuals (px):')
    for v in VIEWS:
        rv, C, f = cams[v]
        errs = []
        for n in OBS[v]:
            e = np.hypot(*r[i]); i += 1
            errs.append(e)
            if e > 4: print(f'  {v} {n}: {e:.1f}  ({r[i-1][0]:+.1f},{r[i-1][1]:+.1f})')
        print(f'view {v}: C={np.round(C, 3)} f={f:.0f} rms={np.sqrt(np.mean(np.square(errs))):.2f}')
    print('landmarks:')
    for n in sorted(pts):
        print(f'  {n:12s} {np.round(pts[n], 3)}')
    def three(c):
        """Car-frame camera -> three.js (x fwd, y up, z = car right) position, quaternion, fov."""
        T = lambda v: [v[0], v[2], -v[1]]
        R = Rot.from_rotvec(c[0]).as_matrix()
        zc, yc = -np.array(T(R[2])), -np.array(T(R[1]))
        q = Rot.from_matrix(np.stack([np.cross(yc, zc), yc, zc], 1)).as_quat()
        return {'p': T(list(c[1])), 'q': list(map(float, q)), 'fov': float(2 * np.degrees(np.arctan(H / 2 / c[2])))}
    DOORS = {'03': ['doorL', 'doorR'], '04': ['doorL', 'doorR'], '05': ['doorL', 'doorR'], '06': ['doorL', 'doorR'], '07': ['doorR']}
    out = {'cams': {v: {'rotvec': list(map(float, cams[v][0])), 'C': list(map(float, cams[v][1])), 'f': float(cams[v][2]),
                        'three': {**three(cams[v]), 'doors': DOORS.get(v, [])}} for v in VIEWS},
           'pts': {n: list(map(float, pts[n])) for n in pts}}
    dst = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cameras.json')
    json.dump(out, open(dst, 'w'), indent=1)
    print('wrote', dst)
