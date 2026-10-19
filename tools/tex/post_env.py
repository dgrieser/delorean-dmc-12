"""Post-process raw Cycles panoramas: normalise, denoise dim regions, add a clamped sun disc
(day), write RLE Radiance .hdr and tonemapped sRGB JPG backdrops.

usage: python3 post_env.py <scene> <raw.hdr> <outdir>
"""
import os, sys, math
import numpy as np
import cv2

SUN_EL, SUN_AZ = 35.0, 40.0   # keep in sync with render_env.py (az from +X toward three.js +Z)


def read_hdr(p):
    im = cv2.imread(p, cv2.IMREAD_UNCHANGED)
    return im[..., ::-1].astype(np.float32).copy()


def write_hdr(p, rgb):
    cv2.imwrite(p, np.ascontiguousarray(rgb[..., ::-1]).astype(np.float32))


def lum(rgb):
    return rgb @ np.array([0.2126, 0.7152, 0.0722], np.float32)


def denoise(rgb, thresh, sigma_c=0.25, d=9, sigma_s=4.0, passes=2):
    """Edge-preserving smoothing in log space for pixels dimmer than `thresh` (emitters stay sharp)."""
    H, W = rgb.shape[:2]
    pad = 16
    out = rgb.copy()
    for _ in range(passes):
        lg = np.log(out + 1e-4)
        lgp = np.concatenate([lg[:, -pad:], lg, lg[:, :pad]], 1)   # wrap the u seam
        f = cv2.bilateralFilter(lgp.astype(np.float32), d, sigma_c, sigma_s)[:, pad:-pad]
        sm = np.exp(f) - 1e-4
        L = lum(out)
        w = np.clip((thresh * 2 - L) / thresh, 0, 1)[..., None]
        out = out * (1 - w) + np.maximum(sm, 0) * w
    return out


def dir_to_px(az_deg, el_deg, W, H):
    u = 0.5 + az_deg / 360.0
    v = 0.5 + el_deg / 180.0
    return u * W, (1 - v) * H


def add_sun(rgb):
    H, W = rgb.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    lon = (xx + 0.5) / W * 2 * np.pi - np.pi            # three.js: atan2(z, x)
    lat = np.pi / 2 - (yy + 0.5) / H * np.pi
    d = np.stack([np.cos(lat) * np.cos(lon), np.sin(lat), np.cos(lat) * np.sin(lon)], -1)
    el, az = math.radians(SUN_EL), math.radians(SUN_AZ)
    s = np.array([math.cos(el) * math.cos(az), math.sin(el), math.cos(el) * math.sin(az)], np.float32)
    ang = np.degrees(np.arccos(np.clip(d @ s, -1, 1)))
    col = np.array([1.0, 0.94, 0.86], np.float32)
    core = np.clip((0.42 - ang) / 0.12, 0, 1) * 1500.0
    glow = 22.0 * np.exp(-(ang / 2.2) ** 2) + 2.0 * np.exp(-(ang / 9.0) ** 2)
    return rgb + (core + glow)[..., None] * col, s


def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


def srgb(x):
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(np.maximum(x, 0), 1 / 2.4) - 0.055)


def to_ldr(rgb, exposure):
    return (np.clip(srgb(aces(rgb * exposure)), 0, 1) * 255 + 0.5).astype(np.uint8)


def main():
    scene, raw, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    rgb = read_hdr(raw)
    H, W = rgb.shape[:2]
    info = {}
    if scene == 'day':
        up = lum(rgb[:H // 2]).mean()
        k = 1.6 / up
        rgb *= k
        lower = rgb[H // 2:]
        rgb[H // 2:] = denoise(lower, thresh=2.0)
        rgb, s = add_sun(rgb)
        info['scale'] = k
        info['sun_dir_three'] = s.tolist()
        exposure = 0.65
    elif scene == 'studio':
        # single illuminant colour + neutral surfaces -> exact white balance to a near-neutral 5500K look
        L0 = lum(rgb)
        c = rgb[L0 > 5].mean(0)
        c = c / c[1]
        rgb *= (np.array([1.05, 1.0, 0.965], np.float32) / c)
        rgb = denoise(rgb, thresh=0.6)
        exposure = 1.0
    else:
        rgb = denoise(rgb, thresh=0.25, sigma_c=0.35)
        exposure = 2.2
    rgb = np.maximum(rgb, 0)
    hdr_p = os.path.join(outdir, f'{scene}.hdr')
    write_hdr(hdr_p, rgb)
    ldr = to_ldr(rgb, exposure)
    jp = os.path.join(outdir, f'{scene}_bg.jpg')
    cv2.imwrite(jp, ldr[..., ::-1], [cv2.IMWRITE_JPEG_QUALITY, 86])
    L = lum(rgb)
    print(scene, 'size %.2f MB' % (os.path.getsize(hdr_p) / 1e6), 'jpg %.2f MB' % (os.path.getsize(jp) / 1e6),
          'max %.1f' % L.max(), 'upper mean %.3f' % L[:H // 2].mean(), 'lower mean %.3f' % L[H // 2:].mean(),
          'p99 %.2f' % np.percentile(L, 99), info)
    cv2.imwrite(f'/tmp/env/{scene}_preview.png', cv2.resize(ldr, (1024, 512), interpolation=cv2.INTER_AREA)[..., ::-1])


if __name__ == '__main__':
    main()
