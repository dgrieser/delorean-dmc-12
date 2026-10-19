// Binary fetch with a fallback for hosts that only serve text: `<url>.b64.<n>.txt` chunks
// (written by tools/b64split.py) are fetched in order and decoded.

function looksMissing(res) {
  return !res.ok || (res.headers.get('content-type') || '').includes('text/html');
}

async function readWithProgress(res, onBytes) {
  if (!res.body) { const b = new Uint8Array(await res.arrayBuffer()); onBytes(b.length); return b; }
  const reader = res.body.getReader();
  const chunks = [];
  let n = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value); n += value.length; onBytes(value.length);
  }
  const out = new Uint8Array(n);
  let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.length; }
  return out;
}

function b64decode(text) {
  const bin = atob(text.replace(/\s+/g, ''));
  const out = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
  return out;
}

export async function fetchBinary(url, onProgress, sizeHint = 0) {
  let got = 0;
  const tick = n => { got += n; if (sizeHint) onProgress?.(Math.min(1, got / sizeHint)); };
  const res = await fetch(url).catch(() => null);
  if (res && !looksMissing(res)) {
    const total = +res.headers.get('content-length') || sizeHint;
    sizeHint = total;
    const bytes = await readWithProgress(res, tick);
    onProgress?.(1);
    return bytes.buffer;
  }
  const parts = [];
  for (let i = 0; ; i++) {
    const r = await fetch(`${url}.b64.${i}.txt`).catch(() => null);
    if (!r || looksMissing(r)) break;
    const textBytes = await readWithProgress(r, n => tick(n * 0.75));
    parts.push(b64decode(new TextDecoder().decode(textBytes)));
  }
  if (!parts.length) throw new Error(`Could not load ${url}`);
  const total = parts.reduce((a, p) => a + p.length, 0);
  const out = new Uint8Array(total);
  let o = 0;
  for (const p of parts) { out.set(p, o); o += p.length; }
  onProgress?.(1);
  return out.buffer;
}
