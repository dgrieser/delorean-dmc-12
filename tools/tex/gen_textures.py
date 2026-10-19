"""Procedural, seamlessly tiling material textures for the DMC-12 viewer.

All noise is generated in the frequency domain (FFT) or on a torus, so every map tiles.
Normal maps are tangent space, OpenGL convention (+Y / green = up, i.e. towards row 0).
"""
import os
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree

OUT = os.environ.get('OUT', '/home/user/delorean-dmc-12/web/assets/tex')
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(1981)


def freqs(h, w):
    fy = np.fft.fftfreq(h)[:, None]
    fx = np.fft.fftfreq(w)[None, :]
    return fx, fy


def spectral_noise(h, w, filt):
    """Periodic noise: white noise shaped by filter(fx, fy) in the frequency domain."""
    fx, fy = freqs(h, w)
    W = np.fft.fft2(rng.standard_normal((h, w)))
    out = np.real(np.fft.ifft2(W * filt(fx, fy)))
    out -= out.mean()
    out /= out.std() + 1e-12
    return out


def norm01(a):
    a = a - a.min()
    return a / (a.max() + 1e-12)


def height_to_normal(hgt, strength):
    """Height (rows=v downwards) -> OpenGL tangent-space normal map RGB uint8."""
    # periodic central differences
    dx = (np.roll(hgt, -1, 1) - np.roll(hgt, 1, 1)) * 0.5
    dy_rows = (np.roll(hgt, -1, 0) - np.roll(hgt, 1, 0)) * 0.5
    dv = -dy_rows                      # +v is up the image (towards row 0)
    nx = -dx * strength
    ny = -dv * strength
    nz = np.ones_like(hgt)
    L = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / L, ny / L, nz / L], -1)
    return np.clip((n * 0.5 + 0.5) * 255 + 0.5, 0, 255).astype(np.uint8)


def save_rgb(name, rgb):
    Image.fromarray(rgb, 'RGB').save(os.path.join(OUT, name), optimize=True)
    print(name, os.path.getsize(os.path.join(OUT, name)) // 1024, 'KB')


def save_grey(name, g):
    Image.fromarray(np.clip(g * 255 + 0.5, 0, 255).astype(np.uint8), 'L').save(os.path.join(OUT, name), optimize=True)
    print(name, os.path.getsize(os.path.join(OUT, name)) // 1024, 'KB')


def periodic_voronoi(n, count, k=2, seed=0):
    """F1/F2 distances (in pixels) to jittered points on an n x n torus."""
    r = np.random.default_rng(seed)
    pts = r.random((count, 2)) * n
    tree = cKDTree(pts, boxsize=n)
    yy, xx = np.mgrid[0:n, 0:n]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], 1) % n
    d, idx = tree.query(q, k=k)
    return d.reshape(n, n, k), idx.reshape(n, n, k)


# ---------------------------------------------------------------- brushed stainless
def brushed():
    n = 2048
    # fine streaks: very long along U (x), narrow across V (y)
    def streak_filter(fx, fy):
        return np.exp(-(fx / 0.0035) ** 2) * (np.abs(fy) > 0) * np.exp(-(fy / 0.45) ** 2)
    s1 = spectral_noise(n, n, streak_filter)
    def streak_filter2(fx, fy):
        return np.exp(-(fx / 0.0012) ** 2) * np.exp(-(fy / 0.06) ** 2)
    s2 = spectral_noise(n, n, streak_filter2)
    # sparse deeper scratches along U
    def scratch_filter(fx, fy):
        return np.exp(-(fx / 0.0008) ** 2) * np.exp(-(fy / 0.45) ** 2)
    sc = spectral_noise(n, n, scratch_filter)
    sc = np.maximum(sc - 2.2, 0)
    # very low-frequency panel waviness (isotropic)
    def wavy(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-(f / 0.0025) ** 2) * (f > 0)
    wv = spectral_noise(n, n, wavy)
    h = 0.55 * s1 + 0.35 * s2 + 0.9 * sc
    nrm = height_to_normal(h * 1.0 + wv * 4.0, 0.30)
    save_rgb('brushed_n.png', nrm)
    # roughness variation: streaky, centred ~0.5
    r = 0.5 + 0.07 * s2 + 0.09 * s1 - 0.05 * np.tanh(sc)
    def blotch(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-(f / 0.01) ** 2) * (f > 0)
    r += 0.04 * spectral_noise(n, n, blotch)
    save_grey('brushed_r.png', np.clip(r, 0, 1))


# ---------------------------------------------------------------- leather
def leather():
    n = 1024
    d, _ = periodic_voronoi(n, 5200, 2, seed=7)
    f1, f2 = d[..., 0], d[..., 1]
    edge = f2 - f1                       # 0 on cell borders
    cell = np.clip(edge / 5.0, 0, 1)
    bump = np.sqrt(cell) * (1 - 0.35 * np.clip(f1 / 9.0, 0, 1))
    # larger irregular grain + fine wrinkles
    def mid(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-(f / 0.02) ** 2) * (f > 0)
    def fine(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-((f - 0.18) / 0.08) ** 2)
    g = spectral_noise(n, n, mid)
    w = spectral_noise(n, n, fine)
    h = bump * 1.0 + 0.25 * g + 0.06 * w
    save_rgb('leather_n.png', height_to_normal(h, 2.2))
    rough = 0.55 + 0.10 * (1 - cell) - 0.05 * bump + 0.05 * g
    save_grey('leather_r.png', np.clip(rough, 0, 1))


# ---------------------------------------------------------------- carpet
def carpet():
    n = 1024
    # loop pile: small cells, each loop a soft dome; plus tufting rows
    d, idx = periodic_voronoi(n, 42000, 2, seed=11)
    f1, f2 = d[..., 0], d[..., 1]
    loop = np.clip(1 - f1 / 3.4, 0, 1) ** 0.7
    yy, xx = np.mgrid[0:n, 0:n]
    rows = 0.5 + 0.5 * np.cos(2 * np.pi * yy / n * 128)
    def mottle(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-(f / 0.012) ** 2) * (f > 0)
    m = spectral_noise(n, n, mottle)
    def fib(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-((f - 0.3) / 0.12) ** 2)
    fibre = spectral_noise(n, n, fib)
    h = loop * 0.8 + rows * 0.15 + fibre * 0.12
    save_rgb('carpet_n.png', height_to_normal(h, 3.0))
    r = np.random.default_rng(5)
    per_loop = r.random(42000)[idx[..., 0]]
    lum = 0.62 + 0.18 * loop + 0.07 * (per_loop - 0.5) + 0.05 * m + 0.04 * fibre
    lum = np.clip(lum, 0, 1)
    rgb = np.stack([lum * 0.98, lum * 0.99, lum * 1.0], -1)
    save_rgb('carpet_c.png', np.clip(rgb * 255 + 0.5, 0, 255).astype(np.uint8))


# ---------------------------------------------------------------- plastic stipple
def plastic():
    n = 1024
    def stip(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-((f - 0.09) / 0.05) ** 2)
    s = spectral_noise(n, n, stip)
    s = np.tanh(s * 1.2)
    def lo(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-(f / 0.01) ** 2) * (f > 0)
    h = s + 0.3 * spectral_noise(n, n, lo)
    save_rgb('plastic_grain_n.png', height_to_normal(h, 0.9))


# ---------------------------------------------------------------- tyre tread micro detail
def tread():
    w, h = 1024, 256
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    # sipes: thin slanted grooves repeating around the circumference (U)
    u = xx / w
    v = yy / h
    sipe = np.abs(((u * 64 + v * 0.6) % 1.0) - 0.5)
    sipe_h = -np.exp(-(sipe / 0.035) ** 2)
    def rub(fx, fy):
        f = np.sqrt(fx * fx + (fy * 4) ** 2)
        return np.exp(-((f - 0.25) / 0.15) ** 2)
    fx, fy = freqs(h, w)
    W = np.fft.fft2(rng.standard_normal((h, w)))
    grain = np.real(np.fft.ifft2(W * rub(fx, fy)))
    grain = (grain - grain.mean()) / grain.std()
    hgt = sipe_h + 0.08 * grain
    save_rgb('tyre_tread_n.png', height_to_normal(hgt, 2.0))


# ---------------------------------------------------------------- glass dirt
def glass_dirt():
    n = 1024
    def smudge(fx, fy):
        f = np.sqrt(fx * fx + fy * fy)
        return np.exp(-(f / 0.006) ** 2) * (f > 0)
    def streak(fx, fy):
        return np.exp(-(fx / 0.004) ** 2) * np.exp(-(fy / 0.03) ** 2)
    a = spectral_noise(n, n, smudge)
    b = spectral_noise(n, n, streak)
    m = np.clip(0.5 * a + 0.35 * b - 0.6, 0, None)
    m = m / (m.max() + 1e-9) * 0.55
    # dust specks
    r = np.random.default_rng(3)
    dust = np.zeros((n, n))
    pts = r.integers(0, n, (900, 2))
    dust[pts[:, 0], pts[:, 1]] = r.random(900) * 0.6 + 0.1
    from scipy.ndimage import gaussian_filter
    dust = gaussian_filter(dust, 0.6, mode='wrap') * 3
    save_grey('glass_dirt.png', np.clip(m + dust, 0, 1))


if __name__ == '__main__':
    import sys
    todo = sys.argv[1:] or ['brushed', 'leather', 'carpet', 'plastic', 'tread', 'glass_dirt']
    for t in todo:
        globals()[t]()
