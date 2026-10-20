"""Build a text-only copy of web/ for hosts that refuse binary files: every .bin/.hdr becomes
<name>.b64.<n>.txt chunks (decoded by web/js/fetchbin.js)."""
import base64, os, shutil, sys

SRC = os.path.join(os.path.dirname(__file__), '..', 'web')
DST = sys.argv[1]
CHUNK = 9_000_000          # characters per chunk (well under the 16 MB text limit)
SKIP = {'dmc12_raw.glb', 'dmc12.glb', 'glass_dirt.png', 'tyre_tread_n.png', 'NOTES.md'}
if os.path.exists(DST):
    shutil.rmtree(DST)
out = []
for root, _, files in os.walk(SRC):
    for f in files:
        if f in SKIP:
            continue
        src = os.path.join(root, f)
        rel = os.path.relpath(src, SRC)
        dst = os.path.join(DST, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if f.endswith(('.bin', '.hdr')):
            s = base64.b64encode(open(src, 'rb').read()).decode()
            for i in range(0, len(s), CHUNK):
                p = f'{rel}.b64.{i // CHUNK}.txt'
                open(os.path.join(DST, p), 'w').write(s[i:i + CHUNK])
                out.append(p)
        else:
            shutil.copy(src, dst)
            out.append(rel)
for p in sorted(out):
    print(p, os.path.getsize(os.path.join(DST, p)))
