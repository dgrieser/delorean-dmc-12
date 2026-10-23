"""DeLorean bumper wordmark, preserving the vector's custom letter outlines.

Source and derived-mask provenance: assets/README.md. The physical placement is
matched to the rectified rear bumper in studio views 05 and 06. Geometry uses a
signed distance field, so the lettering has actual bevelled walls and a floor.
"""
from functools import lru_cache
from pathlib import Path
import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt, map_coordinates, gaussian_filter

WIDTH = 0.455
HEIGHT = WIDTH * 12.09443 / 148.467346
YC, ZC = 0.516, 0.522
DEPTH = 0.0035
PAD = 24


@lru_cache(maxsize=1)
def field():
    mask = np.asarray(Image.open(Path(__file__).parent / 'assets/delorean-wordmark.png')) > 127
    step = WIDTH / (mask.shape[1] - 2 * PAD)
    # Smooth subpixel contour stair-steps before taking normals on the bevels.
    return gaussian_filter((distance_transform_edt(~mask) - distance_transform_edt(mask)) * step, 1.2)


def letters(Y, Z):
    """Signed distance to the filled glyphs, facing the rear of the car."""
    shape = np.broadcast_shapes(np.shape(Y), np.shape(Z))
    Y, Z = np.broadcast_arrays(Y, Z)
    result = np.full(shape, 0.05)
    sel = (np.abs(Y-YC) < WIDTH/2+0.004) & (np.abs(Z-ZC) < HEIGHT/2+0.004)
    if np.any(sel):
        grid = field()
        u = (0.5-(Y[sel]-YC)/WIDTH)*(grid.shape[1]-2*PAD) + PAD - 0.5
        v = (0.5-(Z[sel]-ZC)/HEIGHT)*(grid.shape[0]-2*PAD) + PAD - 0.5
        result[sel] = map_coordinates(grid, [v,u], order=1, mode='constant', cval=0.05)
    return result


def border(Y, Z):
    # Rounded rectangular moulding 4 mm outside the glyphs, with a 1.2 mm groove.
    qy = np.abs(Y-YC) - (WIDTH/2+0.004) + 0.002
    qz = np.abs(Z-ZC) - (HEIGHT/2+0.004) + 0.002
    d = np.hypot(np.maximum(qy,0), np.maximum(qz,0)) + np.minimum(np.maximum(qy,qz),0) - 0.002
    return np.abs(d)-0.0006
