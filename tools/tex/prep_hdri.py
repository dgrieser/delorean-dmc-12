"""Prepare Poly Haven HDRIs (CC0) for the viewer.

For each environment: clamp the over-bright key light (sun / lamp / softbox core) out of the
map, measure the clamped energy and its direction (-> a DirectionalLight with matching
irradiance, so shadows come from the real light), write a 2k Radiance .hdr for lighting and
reflections and, for scenes with a projected ground, a 4k sRGB JPEG backdrop.

Direction convention matches three.js equirect lookup (u = atan2(z, x) / 2pi + 0.5, top row = +Y).
usage: python3 prep_hdri.py <src_dir> <dst_dir> [name=file:clamp:k ...]   (k = '-' for no backdrop)
"""
import json, os, sys
import cv2
import numpy as np

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)

SCENES = {
    # name: (source file, clamp level, backdrop scale k (jpeg = srgb(L * k)), want backdrop, yaw offset deg)
    'studio': ('cyclorama_hard_light_2k.hdr', 60.0, None, False, 0.0),
    'day': ('driving_school_4k.hdr', 40.0, 0.32, True, 0.0),
    'night': ('hansaplatz_4k.hdr', 25.0, 1.6, True, 0.0),
}


def dirs(h, w):
    v = 1.0 - (np.arange(h) + 0.5) / h
    u = (np.arange(w) + 0.5) / w
    lat = (v - 0.5) * np.pi
    phi = (u - 0.5) * 2 * np.pi
    L, P = np.meshgrid(lat, phi, indexing='ij')
    d = np.stack([np.cos(P) * np.cos(L), np.sin(L), np.sin(P) * np.cos(L)], -1)
    domega = (2 * np.pi / w) * (np.pi / h) * np.cos(L)
    return d, domega


def lum(img):
    return img[..., 0] * 0.2126 + img[..., 1] * 0.7152 + img[..., 2] * 0.0722


def srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


for spec in sys.argv[3:]:
    name, rest = spec.split('=')
    fn, clamp, k = rest.split(':')
    SCENES[name] = (fn, float(clamp), None if k == '-' else float(k), k != '-', 0.0)
if len(sys.argv) > 3:
    SCENES = {k: v for k, v in SCENES.items() if any(a.startswith(k + '=') for a in sys.argv[3:])}
meta = json.load(open(os.path.join(DST, 'env.json'))) if os.path.exists(os.path.join(DST, 'env.json')) else {}
for name, (fn, clamp, k, backdrop, yaw) in SCENES.items():
    img = cv2.imread(os.path.join(SRC, fn), cv2.IMREAD_ANYDEPTH | cv2.IMREAD_COLOR)[..., ::-1].astype(np.float32)
    h, w = img.shape[:2]
    d, dom = dirs(h, w)
    Y = lum(img)
    # energy above the clamp level -> key light
    excess = np.maximum(img - clamp * (img / np.maximum(Y[..., None], 1e-6)), 0)
    hot = Y > clamp
    exc = np.where(hot[..., None], img - img / np.maximum(Y[..., None], 1e-6) * clamp, 0)
    wgt = lum(exc) * dom
    E = (exc * dom[..., None]).reshape(-1, 3).sum(0)            # irradiance at normal incidence (RGB)
    if wgt.sum() > 0:
        kd = (d * wgt[..., None]).reshape(-1, 3).sum(0)
        kd /= np.linalg.norm(kd)
    else:
        kd = np.array([0, 1, 0.0])
    clamped = np.where(hot[..., None], img - exc, img)
    # 2k environment for PMREM
    env = cv2.resize(clamped, (2048, 1024), interpolation=cv2.INTER_AREA) if w > 2048 else clamped
    cv2.imwrite(os.path.join(DST, f'{name}.hdr'), np.ascontiguousarray(env[..., ::-1]))
    entry = {'keyDir': [float(x) for x in kd], 'keyIrradiance': [float(x) for x in E],
             'keyLuma': float(E @ [0.2126, 0.7152, 0.0722]),
             'meanRadiance': float(Y.mean()), 'source': fn.rsplit('_', 1)[0], 'license': 'CC0 (Poly Haven)'}
    if backdrop:
        bg = srgb(img * k)
        bg = cv2.resize(bg, (4096, 2048), interpolation=cv2.INTER_AREA) if w != 4096 else bg
        cv2.imwrite(os.path.join(DST, f'{name}_bg.jpg'), np.ascontiguousarray((bg[..., ::-1] * 255 + 0.5).astype(np.uint8)),
                    [cv2.IMWRITE_JPEG_QUALITY, 88, cv2.IMWRITE_JPEG_PROGRESSIVE, 1])
        entry['backdropScale'] = k
    meta[name] = entry
    print(name, json.dumps(entry))
json.dump(meta, open(os.path.join(DST, 'env.json'), 'w'), indent=1)
