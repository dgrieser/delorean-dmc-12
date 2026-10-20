"""Compare renders from tools/ref/shots.mjs with the reference photos.

usage: python3 tools/ref/compare.py <renderdir> <outdir> [views...]
Writes <view>_stack.jpg (photo above render) and <view>_overlay.jpg (photo and render blended,
the render's edges in red) for each view."""
import glob, os, sys
import numpy as np
from PIL import Image, ImageFilter

REF = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ref', 'studio')
src, dst = sys.argv[1], sys.argv[2]
views = sys.argv[3:] or sorted(os.path.basename(p)[:2] for p in glob.glob(f'{src}/*.png'))
os.makedirs(dst, exist_ok=True)
for v in views:
    photo = Image.open(glob.glob(f'{REF}/{v}_*.jpg')[0]).convert('RGB').resize((2048, 1366))
    ren = Image.open(f'{src}/{v}.png').convert('RGB').resize((2048, 1366))
    stack = Image.new('RGB', (2048, 2732))
    stack.paste(photo, (0, 0)); stack.paste(ren, (0, 1366))
    stack.resize((1024, 1366)).save(f'{dst}/{v}_stack.jpg', quality=88)
    a, b = np.asarray(photo, float), np.asarray(ren, float)
    out = a * 0.55 + b * 0.45
    out[np.asarray(ren.convert('L').filter(ImageFilter.FIND_EDGES)) > 40] = [255, 0, 0]
    Image.fromarray(out.astype(np.uint8)).save(f'{dst}/{v}_overlay.jpg', quality=88)
    print(v)
