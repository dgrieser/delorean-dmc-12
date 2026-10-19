"""Procedural car-photography studio environment (lighting / reflections for the studio scene).

The look of the studio reference set (ref/studio): a white cyclorama, one large overhead
softbox, darker ceiling, and a floor that reads dark in the car's lower flanks (the car shades
the floor right around it). Uniform white rooms make brushed steel look flat; this gives the
tonal gradient the photos show: bright tops, light upper flanks, darker tucked lower flanks.

Writes web/assets/env/studio.hdr (2048 x 1024, three.js equirect orientation: u = atan2(z, x)
/ 2pi + 0.5, top row = +Y, car front = +X) and the studio entry of env.json (key light = the
overhead softbox).   usage: python3 tools/tex/studio_env.py
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
L, P = np.meshgrid(lat, phi, indexing='ij')
d = np.stack([np.cos(P) * np.cos(L), np.sin(L), np.sin(P) * np.cos(L)], -1)
deg = np.degrees(L)

# cyc wall band above the horizon, darker ceiling; floor bright far away, shaded near the car
up = 1.0 - 0.90 * smooth(18, 42, deg)
down = 0.30 + 0.55 * smooth(-14, -1, deg)
rad = np.where(deg >= 0, up, down)

# overhead softbox: 6.0 x 3.2 m panel 3.0 m above the car's centre, soft-edged
with np.errstate(divide='ignore', invalid='ignore'):
    t = np.where(d[..., 1] > 1e-3, 3.0 / d[..., 1], np.inf)
    px, pz = d[..., 0] * t, d[..., 2] * t
box = (1 - smooth(2.75, 3.25, np.abs(px))) * (1 - smooth(1.35, 1.85, np.abs(pz)))
rad = rad + 7.0 * np.nan_to_num(box)

# two tall strip boxes (front-right, rear-left) for vertical highlights on corners and flanks
for az, gain in ((40.0, 2.6), (220.0, 2.0)):
    da = np.degrees(np.angle(np.exp(1j * (P - np.radians(az)))))
    strip = (1 - smooth(5.0, 8.0, np.abs(da))) * smooth(-4, 2, deg) * (1 - smooth(30, 38, deg))
    rad = rad + gain * strip

img = np.repeat(rad[..., None], 3, -1).astype(np.float32)
img *= np.array([1.0, 0.995, 0.985], np.float32)          # faintly warm tungsten-balanced white
cv2.imwrite(os.path.join(DST, 'studio.hdr'), np.ascontiguousarray(img[..., ::-1]))

# key light for shadows: the softbox, from almost straight above (slightly to the front-right)
kd = np.array([0.12, 1.0, 0.16]); kd /= np.linalg.norm(kd)
meta_path = os.path.join(DST, 'env.json')
meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
meta['studio'] = {'keyDir': kd.tolist(), 'keyIrradiance': [2.2, 2.19, 2.17], 'keyLuma': 2.19,
                  'meanRadiance': float(rad.mean()), 'source': 'procedural (tools/tex/studio_env.py)',
                  'license': 'generated'}
json.dump(meta, open(meta_path, 'w'), indent=1)
print('studio.hdr', img.shape, 'mean', round(float(rad.mean()), 3), 'max', round(float(rad.max()), 2))
