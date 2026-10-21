"""Procedural car-photography studio environment (lighting / reflections for the studio scene).

The look of the studio reference set (ref/studio): a white cyclorama and floor, a softbox behind
the camera, a big overhead softbox, a mid-grey ceiling and darker walls.
Uniform white rooms make brushed steel look flat; this gives the tonal changes the photos show
from panel to panel.

The rig is authored relative to the camera, as on a turntable shoot: +X (u = 0.5) points from the
car towards the camera, and the viewer turns the map with the orbit camera (Environment.follow).
Like the photographer, who re-set the lights for each shot, the rig also changes with the angle
the car is seen from: one parameter set per reference angle (front, front three-quarter, side,
rear three-quarter), which the viewer blends by the camera's azimuth round the car. Each set was
fitted (coordinate descent, tools/tex/studio_fit.py) to the stainless panel tones of the
calibrated photos taken from that angle, ~25 patches whose reflection directions were traced on
the model. On top of that, each rig carries a smooth gain map over the directions its photos'
stainless panels reflect (flags, darker walls, the brighter spots of the photographer's lights),
fitted from every stainless pixel of those photos (studio_fit.py gain); it is symmetric about
the camera axis, so it serves views from either side of the car.

Writes web/assets/env/studio.hdr (the default rig) and studio_aNNN.hdr (one per angle, 2048 x
1024, three.js equirect orientation: u = atan2(z, x) / 2pi + 0.5, top row = +Y), and the studio
entry of env.json (key light = the overhead softbox, and the list of angle rigs).
usage: python3 tools/tex/studio_env.py
Parameters can be overridden for tuning: STUDIO='{"key": 2.5}' python3 tools/tex/studio_env.py
(applied to every rig; STUDIO_ONLY=studio_a090 writes just that one).
"""
import json, os
import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DST = os.path.join(ROOT, 'web', 'assets', 'env')
W, H = 2048, 1024

# - a dark band at the horizon (the studio's walls) under a mid-grey ceiling;
# - a softbox behind and above the photographer for the flanks facing the camera;
# - a lit backdrop behind the car;
# - a big overhead softbox for the bonnet, roof and the side view's upper flanks;
# - a white floor, brightest on the camera side, shaded by the car close round its sills.
DEFAULT = dict(wall=0.05, wall_top=4.0, dark=0.55, dark_from=20.0, floor=0.90, floor_cam=0.70, cam_w=100.0, nadir=0.35,
               floor_fall=-26.0, key=1.6, key_w=42.0, key_lo=35.0, key_hi=62.0,
               back=0.0, back_w=30.0, back_lo=19.5, back_hi=30.0,
               box=2.8, box_x=1.9, box_z=1.35)
# per-angle rigs (azimuth of the camera round the car, degrees from straight ahead); fitted values
# live in studio_rigs.json next to this file
RIGS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'studio_rigs.json')


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


v = 1.0 - (np.arange(H) + 0.5) / H
u = (np.arange(W) + 0.5) / W
lat = (v - 0.5) * np.pi
phi = (u - 0.5) * 2 * np.pi
L, PHI = np.meshgrid(lat, phi, indexing='ij')
d = np.stack([np.cos(PHI) * np.cos(L), np.sin(L), np.sin(PHI) * np.cos(L)], -1)
deg = np.degrees(L)
azd = np.degrees(np.abs(np.angle(np.exp(1j * PHI))))          # 0 = towards the camera, 180 = behind the car


def radiance(P):
    up = P['wall'] - (P['wall'] - P['dark']) * smooth(P['wall_top'], P['dark_from'], deg)
    floor = P['floor'] + P['floor_cam'] * (1 - smooth(P['cam_w'], P['cam_w'] + 50, azd))
    down = floor - (floor - P['nadir']) * smooth(P['floor_fall'], P['floor_fall'] - 25, deg)
    rad = np.where(deg >= 0, up, down)
    key = (1 - smooth(P['key_w'], P['key_w'] + 15, azd)) * smooth(P['key_lo'] - 6, P['key_lo'] + 4, deg) \
        * (1 - smooth(P['key_hi'] - 4, P['key_hi'] + 8, deg))
    rad = rad + P['key'] * key
    back = smooth(180 - P['back_w'] - 20, 180 - P['back_w'], azd) * smooth(P['back_lo'], 24, deg) \
        * (1 - smooth(P['back_hi'] - 4, P['back_hi'] + 8, deg))
    rad = rad + P['back'] * back
    # overhead softbox: soft-edged panel 3.0 m above the car's centre
    with np.errstate(divide='ignore', invalid='ignore'):
        t = np.where(d[..., 1] > 1e-3, 3.0 / d[..., 1], np.inf)
        px, pz = d[..., 0] * t, d[..., 2] * t
    box = (1 - smooth(P['box_x'], P['box_x'] + 0.5, np.abs(px))) * (1 - smooth(P['box_z'], P['box_z'] + 0.5, np.abs(pz)))
    return rad + P['box'] * np.nan_to_num(box)


def gain(G):
    """The rig's gain map (log2, rows = elevation -90..90, columns = angle from the camera axis
    0..180, cells of G['step'] degrees) sampled bilinearly over the equirect map."""
    g = np.asarray(G['log2'], np.float64)
    st = G['step']
    fi = np.clip((deg + 90) / st - 0.5, 0, g.shape[0] - 1)
    fj = np.clip(azd / st - 0.5, 0, g.shape[1] - 1)
    i0, j0 = np.minimum(fi.astype(int), g.shape[0] - 2), np.minimum(fj.astype(int), g.shape[1] - 2)
    ti, tj = fi - i0, fj - j0
    v = (g[i0, j0] * (1 - tj) + g[i0, j0 + 1] * tj) * (1 - ti) + (g[i0 + 1, j0] * (1 - tj) + g[i0 + 1, j0 + 1] * tj) * ti
    return np.exp2(v)


def write(name, P, half=False, G=None):
    rad = radiance(P)
    if G is not None:
        rad = rad * gain(G)
    img = np.repeat(rad[..., None], 3, -1).astype(np.float32)
    img *= np.array([1.0, 0.995, 0.985], np.float32)          # faintly warm tungsten-balanced white
    img[deg < 0] *= np.array([1.0, 0.965, 0.92], np.float32)   # the lower flanks pick up a warm cast off the floor
    if half:            # the angle rigs only feed the prefiltered reflections: 1024 x 512 is plenty
        img = cv2.resize(img, (W // 2, H // 2), interpolation=cv2.INTER_AREA)
    cv2.imwrite(os.path.join(DST, name + '.hdr'), np.ascontiguousarray(img[..., ::-1]))
    print(name + '.hdr', 'mean', round(float(rad.mean()), 3), 'max', round(float(rad.max()), 2))
    return rad


if __name__ == '__main__':
    over = json.loads(os.environ.get('STUDIO', '{}'))
    only = os.environ.get('STUDIO_ONLY')
    rigs = json.load(open(RIGS_PATH)) if os.path.exists(RIGS_PATH) else {}
    if not only or only == 'studio':
        rad = write('studio', {**DEFAULT, **over})
    angles = []
    for name, r in sorted(rigs.items(), key=lambda kv: kv[1]['azimuth']):
        angles.append([r['azimuth'], name + '.hdr'])
        if not only or only == name:
            write(name, {**DEFAULT, **r['params'], **over}, half=True, G=r.get('gain'))
    if not only:
        # key light for shadows: the overhead softbox, from almost straight above
        kd = np.array([0.05, 1.0, 0.0]); kd /= np.linalg.norm(kd)
        meta_path = os.path.join(DST, 'env.json')
        meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
        meta['studio'] = {'keyDir': kd.tolist(), 'keyIrradiance': [2.2, 2.19, 2.17], 'keyLuma': 2.19,
                          'meanRadiance': float(rad.mean()), 'rigs': angles,
                          'source': 'procedural (tools/tex/studio_env.py)', 'license': 'generated'}
        json.dump(meta, open(meta_path, 'w'), indent=1)
