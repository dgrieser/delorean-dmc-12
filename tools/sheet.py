import sys
from PIL import Image
out, cols, files = sys.argv[1], int(sys.argv[2]), sys.argv[3:]
ims = [Image.open(f) for f in files]
W, H = ims[0].size
rows = (len(ims) + cols - 1) // cols
sh = Image.new('RGB', (W * cols, H * rows))
for i, im in enumerate(ims):
    sh.paste(im, ((i % cols) * W, (i // cols) * H))
sh.save(out)
