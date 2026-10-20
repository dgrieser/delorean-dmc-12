"""Turn CC0 texture scans from ambientCG (https://ambientcg.com) into the viewer's maps.

    Metal009   brushed stainless: web/assets/tex/stainless_{c,n,r}.jpg  (body panels)
    Leather026 black leather:     web/assets/tex/leather_{n,r}.jpg       (seats, door cards, dash)
    Carpet012  loop-pile carpet:  web/assets/tex/carpet_{c,n}.jpg        (floor, sills)

usage: python3 tools/tex/import_cc0.py <dir with the unzipped Metal009_2K-JPG, Leather026_1K-JPG,
       Carpet012_1K-JPG folders>     (download: https://ambientcg.com/get?file=<name>.zip)

Colour maps are re-centred so the material colours in web/js/materials.js keep meaning the mean
albedo (the map only carries the variation); roughness maps are re-centred on 0.5 for the same
reason (materials.js scales them by the material roughness).
"""
import os, sys
import numpy as np
from PIL import Image

SRC = sys.argv[1]
DST = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'web', 'assets', 'tex')


def load(name, kind):
    folder = next(f for f in os.listdir(SRC) if f.startswith(name) and os.path.isdir(os.path.join(SRC, f)))
    return Image.open(os.path.join(SRC, folder, f'{folder}_{kind}.jpg'))


def save(im, name, size):
    im = im.resize((size, size), Image.LANCZOS)
    im.save(os.path.join(DST, name), quality=90, optimize=True)
    print(name, im.size, os.path.getsize(os.path.join(DST, name)) // 1024, 'kB')


def centre(im, mean, grey=False):
    a = np.asarray(im.convert('L' if grey else 'RGB')).astype(np.float64)
    a = a * (mean / a.mean(axis=(0, 1)))
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def lin(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055) * 255


# brushed stainless: albedo variation centred on linear 0.5 (materials.js doubles the colour)
c = lin(np.asarray(load('Metal009', 'Color').convert('L')).astype(np.float64))
c = srgb(c * (0.5 / c.mean()))
save(Image.fromarray(c.astype(np.uint8)).convert('RGB'), 'stainless_c.jpg', 1024)
save(load('Metal009', 'NormalGL'), 'stainless_n.jpg', 1024)
save(centre(load('Metal009', 'Roughness'), 128, grey=True), 'stainless_r.jpg', 1024)

save(load('Leather026', 'NormalGL'), 'leather_n.jpg', 1024)
save(centre(load('Leather026', 'Roughness'), 128, grey=True), 'leather_r.jpg', 1024)

# carpet: neutral grey variation centred on linear 0.625 (the triplanar shader scales colour by 1.6)
c = lin(np.asarray(load('Carpet012', 'Color').convert('L')).astype(np.float64))
c = srgb(c * (0.625 / c.mean()))
save(Image.fromarray(c.astype(np.uint8)).convert('RGB'), 'carpet_c.jpg', 1024)
save(load('Carpet012', 'NormalGL'), 'carpet_n.jpg', 1024)
