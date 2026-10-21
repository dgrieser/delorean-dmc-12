"""Fit the studio's per-angle light rigs (tools/tex/studio_env.py) to the reference photos.

Two stages, both written to studio_rigs.json:

params  For each reference angle (a rig per group of calibrated photos taken from about the same
        azimuth round the car), a coordinate descent adjusts the rig's parameters so the stainless
        panels of the viewer, rendered from the photos' cameras (tools/ref/shots.mjs), match the
        photos' tones on the patches of tools/ref/patches.json. A weak pull towards the default rig
        keeps the less constrained parameters sensible. The rigs are fitted in parallel.
gain    The parametric rigs only get the broad tones right; the photos' steel also shows the
        darker flags and walls and the brighter spots of the photographer's set. A reflection pass
        (shots.mjs REFL=1) gives the direction each stainless pixel reflects in its rig's
        camera-relative frame; the ratio of photo to render radiance (both through the inverse of
        the viewer's tone curve) is binned by that direction, robustly averaged and smoothed into a
        gain map per rig, and the render / compare / update loop repeats a few times.

usage: python3 tools/tex/studio_fit.py [params] [gain]    (both by default; serve the repo root on
       :8123 first)
"""
import json, math, os, re, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
REF = os.path.join(ROOT, 'ref', 'studio')
CAMS = json.load(open(os.path.join(ROOT, 'tools', 'ref', 'cameras.json')))['cams']
PATCHES = {k: v for k, v in json.load(open(os.path.join(ROOT, 'tools', 'ref', 'patches.json'))).items() if not k.startswith('_')}
OUT = os.environ.get('OUT', '/tmp/studio_fit')
# photos grouped by the angle they were taken from (camera azimuth round the car, mirrored)
GROUPS = [['02'], ['03', '04'], ['01'], ['07'], ['05'], ['06']]
PARAMS = dict(wall=(0.15, 0.0), dark=(0.15, 0.02), floor=(0.2, 0.2), floor_cam=(0.25, 0.0), nadir=(0.15, 0.05),
              key=(0.8, 0.3), key_lo=(6.0, 5.0), back=(0.8, 0.0), box=(0.8, 0.0))       # name: (step, lower bound)


def azimuth(v):
    C = CAMS[v]['C']
    return abs(math.degrees(math.atan2(C[1], C[0])))


def photo_tones(v):
    a = np.asarray(Image.open(next(os.path.join(REF, f) for f in os.listdir(REF) if f.startswith(v + '_'))).convert('L')
                   .resize((2048, 1366))).astype(float)
    return {k: a[y0:y1, x0:x1].mean() for k, (x0, y0, x1, y1) in PATCHES[v].items()}


def fit(job):
    import studio_env as SE
    name, views, p0 = job
    target = {v: photo_tones(v) for v in views}
    out = os.path.join(OUT, name)
    cache = {}

    def cost(p):
        key = json.dumps(p, sort_keys=True)
        if key in cache:
            return cache[key]
        SE.write(name, {**SE.DEFAULT, **p}, half=True)
        subprocess.run(['node', 'ref/shots.mjs', out] + views, cwd=os.path.join(ROOT, 'tools'), check=True, capture_output=True)
        err = []
        for v in views:
            b = np.asarray(Image.open(f'{out}/{v}.png').convert('L').resize((2048, 1366))).astype(float)
            err += [b[y0:y1, x0:x1].mean() - target[v][k] for k, (x0, y0, x1, y1) in PATCHES[v].items()]
        reg = sum(((p[k] - SE.DEFAULT[k]) / s) ** 2 for k, (s, _) in PARAMS.items())
        c = float(np.sqrt(np.mean(np.square(err)))) + 0.6 * reg
        cache[key] = c
        return c

    best = {k: SE.DEFAULT[k] for k in PARAMS} if p0 is None else dict(p0)
    bc = cost(best)
    steps = {k: s for k, (s, _) in PARAMS.items()}
    for rnd in range(3):
        for k, (_, lo) in PARAMS.items():
            for sgn in (1, -1):
                q = dict(best); q[k] = max(lo, best[k] + sgn * steps[k])
                c = cost(q)
                if c < bc - 0.05:
                    best, bc = q, c
                    q2 = dict(best); q2[k] = max(lo, best[k] + sgn * steps[k])
                    c2 = cost(q2)
                    if c2 < bc - 0.05:
                        best, bc = q2, c2
                    break
        steps = {k: v * 0.5 for k, v in steps.items()}
        print(name, 'round', rnd, round(bc, 2), flush=True)
    return name, best, bc


def save_rigs(rigs, path):
    """studio_rigs.json, with each row of a gain map on one line."""
    def row(m):
        return '[' + ', '.join(v.strip() for v in m.group(1).split(',')) + ']'
    open(path, 'w').write(re.sub(r'\[\s+(-?[0-9][-0-9.,\s]*?)\s+\]', row, json.dumps(rigs, indent=1)))


def fit_params(rigs):
    import studio_env as SE
    jobs = []
    for views in GROUPS:
        az = round(float(np.mean([azimuth(v) for v in views])), 1)
        name = f'studio_a{int(round(az)):03d}'
        rigs.setdefault(name, {'azimuth': az, 'views': views, 'params': {}})
        rigs[name].pop('gain', None)                   # fitted on top of the old parameters
        jobs.append((name, views, rigs[name]['params'] or None))
    save_rigs(rigs, SE.RIGS_PATH)
    subprocess.run([sys.executable, os.path.join(HERE, 'studio_env.py')], check=True)     # rig list into env.json
    with Pool(len(jobs)) as pool:
        for name, best, c in pool.imap_unordered(fit, jobs):
            rigs[name]['params'] = {k: round(v, 4) for k, v in best.items()}
            rigs[name]['cost'] = round(c, 2)
            print('fitted', name, rigs[name], flush=True)


# --- gain maps -------------------------------------------------------------------------------
STEP = 4                    # gain map cell, degrees (elevation x angle from the camera axis)
GAIN_ITERS = 4
EXPO = 0.62                 # the studio preset's exposure (web/js/env.js); cancels in the ratios


def srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def aces(x):
    """three.js ACESFilmicToneMapping of a neutral grey (after the exposure)."""
    i = np.array([[0.59719, 0.07600, 0.02840], [0.35458, 0.90834, 0.13383], [0.04823, 0.01566, 0.83777]])
    o = np.array([[1.60475, -0.10208, -0.00327], [-0.53108, 1.10813, -0.07276], [-0.07367, -0.00605, 1.07602]])
    v = (np.asarray(x, float)[..., None] / 0.6) * np.ones(3) @ i
    v = (v * (v + 0.0245786) - 0.000090537) / (v * (0.983729 * v + 0.4329510) + 0.238081) @ o
    return np.clip(v[..., 1], 0, 1)


_T = np.geomspace(1e-4, 60, 4000)
_Y = aces(_T)


def radiance_of(srgb):
    """Displayed sRGB (0..1) -> scene radiance of a neutral surface."""
    return np.interp(srgb_to_lin(srgb), _Y, _T) / EXPO


def luma(path, size=(1024, 683)):
    return np.asarray(Image.open(path).convert('L').resize(size, Image.LANCZOS)).astype(float) / 255


def refl_dirs(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(float) / 255
    D = srgb_to_lin(a) * 2 - 1
    ok = np.abs(np.linalg.norm(D, axis=-1) - 1) < 0.06
    el = np.degrees(np.arcsin(np.clip(D[..., 1], -1, 1)))
    az = np.degrees(np.abs(np.arctan2(D[..., 2], D[..., 0])))
    return ndimage.binary_erosion(ok, iterations=3), el, az


def blur(a, m, s=1.5):
    return ndimage.gaussian_filter(a * m, s) / np.maximum(ndimage.gaussian_filter(m.astype(float), s), 1e-6)


def log_ratios(v, refl, render):
    """Per stainless pixel of view v: (elevation, angle from the camera axis, ln(photo / render))."""
    ok, el, az = refl
    p = blur(luma(next(os.path.join(REF, f) for f in os.listdir(REF) if f.startswith(v + '_'))), ok)
    r = blur(luma(render), ok)
    m = ok & (p > 25 / 255) & (p < 250 / 255) & (r > 10 / 255) & (r < 250 / 255)
    return el[m], az[m], np.log(radiance_of(p[m]) / radiance_of(r[m])), p[m], r[m]


def gain_step(samples):
    """Robust mean log ratio per cell, smoothed, shrunk to 0 where few pixels say anything."""
    ni, nj = 180 // STEP, 180 // STEP
    el, az, l = (np.concatenate(x) for x in zip(*[s[:3] for s in samples]))
    cell = np.clip(((el + 90) // STEP).astype(int), 0, ni - 1) * nj + np.clip((az // STEP).astype(int), 0, nj - 1)
    med, cnt = np.zeros(ni * nj), np.zeros(ni * nj)
    order = np.argsort(cell)
    cs, ls = cell[order], l[order]
    bounds = np.flatnonzero(np.diff(cs)) + 1
    for c, chunk in zip(cs[np.r_[0, bounds]], np.split(ls, bounds)):
        med[c], cnt[c] = np.median(chunk), len(chunk)
    w = np.minimum(cnt, 400).reshape(ni, nj)
    num = ndimage.gaussian_filter(w * med.reshape(ni, nj), 1.5, mode='reflect')
    den = ndimage.gaussian_filter(w, 1.5, mode='reflect')
    return num / (den + 8.0) / math.log(2)


def fit_gain(rigs):
    import studio_env as SE
    out = os.path.join(OUT, 'gain')
    views = [v for r in rigs.values() for v in r['views']]
    subprocess.run(['node', 'ref/shots.mjs', out + '/refl'] + views, cwd=os.path.join(ROOT, 'tools'), check=True,
                   capture_output=True, env={**os.environ, 'REFL': '1'})
    refl = {v: refl_dirs(f'{out}/refl/{v}.png') for v in views}
    ni, nj = 180 // STEP, 180 // STEP
    G = {n: np.zeros((ni, nj)) for n in rigs}
    for it in range(GAIN_ITERS + 1):
        for n, r in rigs.items():
            SE.write(n, {**SE.DEFAULT, **r['params']}, half=True, G={'step': STEP, 'log2': G[n]})
        subprocess.run(['node', 'ref/shots.mjs', f'{out}/{it}'] + views, cwd=os.path.join(ROOT, 'tools'), check=True,
                       capture_output=True)
        for n, r in rigs.items():
            S = [log_ratios(v, refl[v], f'{out}/{it}/{v}.png') for v in r['views']]
            for v, s in zip(r['views'], S):
                pp, pr = np.percentile(s[3] * 255, [10, 50, 90]), np.percentile(s[4] * 255, [10, 50, 90])
                print(f'iter {it} {n} view {v}: rms ln {np.sqrt(np.mean(s[2] ** 2)):.3f}  photo p10/50/90 {pp.round()}'
                      f'  render {pr.round()}', flush=True)
            if it < GAIN_ITERS:
                G[n] = np.clip(G[n] + 0.8 * gain_step(S), -3.0, 1.5)
    for n in rigs:
        rigs[n]['gain'] = {'step': STEP, 'log2': np.round(G[n], 3).tolist()}


if __name__ == '__main__':
    import studio_env as SE
    stages = sys.argv[1:] or ['params', 'gain']
    os.makedirs(OUT, exist_ok=True)
    rigs = json.load(open(SE.RIGS_PATH)) if os.path.exists(SE.RIGS_PATH) else {}
    if 'params' in stages:
        fit_params(rigs)
    if 'gain' in stages:
        fit_gain(rigs)
    save_rigs(rigs, SE.RIGS_PATH)
    subprocess.run([sys.executable, os.path.join(HERE, 'studio_env.py')], check=True)
