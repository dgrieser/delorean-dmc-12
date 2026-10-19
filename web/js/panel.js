// Resizable control panel: drag the latch to set any height (down to only the latch showing),
// tap the latch to unfold to the default height or to fold away.
const KEY = 'dmc12.panelHeight';

export function initPanel(rack, grip) {
  const gripH = () => grip.offsetHeight + 6;
  const fab = document.querySelector('.fab');
  const maxH = () => {
    // keep the latch clear of the corner buttons when the panel spans under them (phones)
    let top = 12;
    const r = rack.getBoundingClientRect(), f = fab?.getBoundingClientRect();
    if (f && f.width && f.left < r.right && f.right > r.left) top = f.bottom + 8;
    return Math.max(gripH(), innerHeight - parseFloat(getComputedStyle(rack).bottom || '12') - top);
  };
  const narrow = () => matchMedia('(max-width: 720px)').matches;
  const defaultH = () => Math.min(maxH(), narrow() ? Math.round(innerHeight * 0.44) : 780);
  let h = 0;

  function set(v, { save = true } = {}) {
    h = Math.max(gripH(), Math.min(maxH(), v));
    rack.style.height = h + 'px';
    const folded = h <= gripH() + 2;
    rack.classList.toggle('folded', folded);
    grip.setAttribute('aria-valuenow', String(Math.round((h - gripH()) / Math.max(1, maxH() - gripH()) * 100)));
    if (save) { try { localStorage.setItem(KEY, String(Math.round(h))); } catch (e) { /* storage unavailable */ } }
  }
  const isFolded = () => h <= gripH() + 2;
  const fold = () => set(gripH());
  const open = () => set(defaultH());
  const toggle = () => (isFolded() ? open() : fold());

  let saved = NaN;
  try { saved = parseFloat(localStorage.getItem(KEY)); } catch (e) { /* storage unavailable */ }
  set(Number.isFinite(saved) ? saved : defaultH(), { save: false });

  let drag = null;
  grip.addEventListener('pointerdown', e => {
    if (e.button !== undefined && e.button !== 0) return;
    drag = { y: e.clientY, h, moved: false, id: e.pointerId };
    grip.setPointerCapture?.(e.pointerId);
    e.preventDefault();
  });
  grip.addEventListener('pointermove', e => {
    if (!drag || e.pointerId !== drag.id) return;
    const dy = e.clientY - drag.y;
    if (!drag.moved && Math.abs(dy) < 5) return;
    if (!drag.moved) { drag.moved = true; rack.classList.add('dragging'); }
    set(drag.h - dy, { save: false });
  });
  const end = e => {
    if (!drag || (e && e.pointerId !== drag.id)) return;
    rack.classList.remove('dragging');
    if (!drag.moved) toggle();
    else if (h < gripH() + 48) fold();          // released near the bottom: tuck away
    else set(h);
    drag = null;
  };
  grip.addEventListener('pointerup', end);
  grip.addEventListener('pointercancel', end);
  grip.addEventListener('lostpointercapture', end);
  grip.addEventListener('keydown', e => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); set(h + 60); }
    else if (e.key === 'ArrowDown') { e.preventDefault(); set(h - 60); }
  });
  addEventListener('resize', () => set(h, { save: false }));
  return { toggle, fold, open, get folded() { return isFolded(); } };
}
