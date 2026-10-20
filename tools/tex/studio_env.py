"""Procedural car-photography studio environment (lighting / reflections for the studio scene).

The look of the studio reference set (ref/studio): a white cyclorama and floor, a big softbox
behind the camera, a dark ceiling to the sides, a lit backdrop and a modest overhead softbox.
Uniform white rooms make brushed steel look flat; this gives the tonal changes the photos show
from panel to panel.

Writes web/assets/env/studio.hdr (2048 x 1024, three.js equirect orientation: u = atan2(z, x)
/ 2pi + 0.5, top row = +Y, +X = towards the camera, see below) and the studio entry of env.json
(key light = the overhead softbox).   usage: python3 tools/tex/studio_env.py
Parameters can be overridden for tuning: STUDIO='{"key": 2.5}' python3 tools/tex/studio_env.py
"""
import json, os
import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DST = os.path.join(ROOT, 'web', 'assets', 'env')
W, H = 2048, 1024


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

# The rig is authored relative to the camera, as on a turntable shoot: +X (u = 0.5) points from
# the car towards the camera, and the viewer turns the map with the orbit camera
# (Environment.follow). Tuned against the calibrated reference photos, panel by panel:
# - a big softbox behind and above the photographer lights the flanks that face the camera
#   (the side view's upper flanks are near white);
# - flanks turned ~90-130 deg away reflect a dark ceiling 20-60 deg up (front 3/4 view: door 138,
#   wing 85 of 255);
# - the bonnet, seen from in front, reflects a bright backdrop behind the car, brighter 20-30 deg
#   up than at the horizon (205 vs 158);
# - the tucked-under lower flanks reflect the bright white floor all round (176-206);
# - a modest overhead softbox for the roof and the bonnet seen from high up.
P = dict(wall=0.40, wall_top=4.0, dark=0.40, dark_from=20.0, floor=1.10, nadir=0.45, floor_fall=-12.0,
         key=3.2, key_w=42.0, key_lo=26.0, key_hi=62.0,
         back=2.2, back_w=30.0, back_lo=14.0, back_hi=28.0,
         box=2.0, box_x=1.9, box_z=1.35)
P.update(json.loads(os.environ.get('STUDIO', '{}')))

up = P['wall'] - (P['wall'] - P['dark']) * smooth(P['wall_top'], P['dark_from'], deg)
# the floor is white, but the car shades it close round its sills
down = P['floor'] - (P['floor'] - P['nadir']) * smooth(P['floor_fall'], -60, deg)
rad = np.where(deg >= 0, up, down)
azd = np.degrees(np.abs(np.angle(np.exp(1j * PHI))))          # 0 = towards the camera, 180 = behind the car

# key softbox behind the camera
key = (1 - smooth(P['key_w'], P['key_w'] + 15, azd)) * smooth(P['key_lo'] - 6, P['key_lo'] + 4, deg) \
    * (1 - smooth(P['key_hi'] - 4, P['key_hi'] + 8, deg))
rad = rad + P['key'] * key

# lit backdrop behind the car, brightening upwards
back = smooth(180 - P['back_w'] - 20, 180 - P['back_w'], azd) * smooth(P['back_lo'], 24, deg) * (1 - smooth(P['back_hi'] - 4, P['back_hi'] + 8, deg))
rad = rad + P['back'] * back

# overhead softbox: soft-edged panel 3.0 m above the car's centre
with np.errstate(divide='ignore', invalid='ignore'):
    t = np.where(d[..., 1] > 1e-3, 3.0 / d[..., 1], np.inf)
    px, pz = d[..., 0] * t, d[..., 2] * t
box = (1 - smooth(P['box_x'], P['box_x'] + 0.5, np.abs(px))) * (1 - smooth(P['box_z'], P['box_z'] + 0.5, np.abs(pz)))
rad = rad + P['box'] * np.nan_to_num(box)

img = np.repeat(rad[..., None], 3, -1).astype(np.float32)
img *= np.array([1.0, 0.995, 0.985], np.float32)          # faintly warm tungsten-balanced white
cv2.imwrite(os.path.join(DST, 'studio.hdr'), np.ascontiguousarray(img[..., ::-1]))

# key light for shadows: the overhead softbox, from almost straight above
kd = np.array([0.05, 1.0, 0.0]); kd /= np.linalg.norm(kd)
meta_path = os.path.join(DST, 'env.json')
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
meta['studio'] = {'keyDir': kd.tolist(), 'keyIrradiance': [2.2, 2.19, 2.17], 'keyLuma': 2.19,
                  'meanRadiance': float(rad.mean()), 'source': 'procedural (tools/tex/studio_env.py)',
                  'license': 'generated'}
json.dump(meta, open(meta_path, 'w'), indent=1)
print('studio.hdr', img.shape, 'mean', round(float(rad.mean()), 3), 'max', round(float(rad.max()), 2))
