// Control rack + keyboard bindings. Smooths pedal inputs, auto-clutch, hold-to-crank key.
import { initPanel } from './panel.js';

export function bindUI(ctx) {
  const { car, sim, lamps, audio, rig, env, state } = ctx;
  const $ = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];
  const held = { throttle: false, brake: false, start: false, flash: false, wash: false, left: false, right: false };
  const ui = { steer: 0 };
  let keyHold = 0, kDown = false, shiftT = 0;

  let noteT = 0;
  function flashNote(msg) {
    const n = $('#note'); if (!n) return;
    n.textContent = msg; n.hidden = false; clearTimeout(noteT); noteT = setTimeout(() => { n.hidden = true; }, 2200);
  }
  const press = (sel, on) => $$(sel).forEach(b => b.setAttribute('aria-pressed', on ? 'true' : 'false'));
  const group = (name, val, attr) => $$(`[data-group="${name}"] [data-${attr}]`).forEach(b => b.setAttribute('aria-pressed', String(b.dataset[attr] === String(val))));

  function refresh() {
    group('cam', rig.mode, 'cam');
    $('#cam-name').textContent = { orbit: 'Orbit', free: 'Free roam', driver: 'Driver seat', passenger: 'Passenger seat', cinematic: 'Cinematic' }[rig.mode];
    group('env', state.env, 'env');
    group('trim', state.trim, 'trim');
    group('ign', sim.ignition, 'ign');
    group('gear', sim.gear, 'gear');
    group('lights', lamps.state.headlights, 'lights');
    group('cabin', lamps.state.interior, 'cabin');
    group('wipe', car.wipers.mode, 'wipe');
    for (const [k, p] of Object.entries(car.panels)) press(`[data-panel="${k}"]`, !p.latched && p.intent >= 0);
    press('[data-toll="L"]', car.toll.L?.target > 0.5);
    press('[data-toll="R"]', car.toll.R?.target > 0.5);
    press('#hbrake', sim.handbrake > 0.5);
    press('#drive', state.drive);
    press('#snd', state.sound);
    press('#hazard', lamps.state.hazard);
    press('#turnL', lamps.state.turn < 0);
    press('#turnR', lamps.state.turn > 0);
  }

  // ---- actions
  const A = {
    cam: m => { rig.setMode(m); refresh(); },
    panel: k => { car.panels[k].toggle(); refresh(); },
    ign: v => {
      v = +v;
      if (v === 3) return;                    // start is hold-only
      if (v !== sim.ignition) audio.key();
      sim.setIgnition(v); refresh();
    },
    gear: g => {
      if (g === sim.gear) return;
      // auto clutch: dip for the shift
      sim.clutch = 1; shiftT = 0.35;
      sim.gear = g; lamps.state.reverse = g === 'R'; audio.switchClick(); refresh();
    },
    toll: k => {
      const t = car.toll[k]; if (!t) return;
      car.setToll(k, t.target < 0.5);
      if (sim.ignition < 2) flashNote('Toll windows need the ignition on');
      audio.switchClick(); refresh();
    },
    lights: v => { lamps.state.headlights = +v; audio.switchClick(); refresh(); },
    cabin: v => { lamps.state.interior = v; audio.switchClick(); refresh(); },
    wipe: v => { car.wipers.setMode(v); audio.switchClick(); refresh(); },
    env: async v => { await ctx.setEnv(v); refresh(); },
    trim: v => { ctx.setTrimColor(v); refresh(); },
    turn: d => { lamps.state.turn = lamps.state.turn === d ? 0 : d; audio.switchClick(); refresh(); },
    hazard: () => { lamps.state.hazard = !lamps.state.hazard; audio.switchClick(); refresh(); },
    handbrake: () => { sim.handbrake = sim.handbrake > 0.5 ? 0 : 1; audio.click(0.3, 900, 0.05); refresh(); },
    drive: () => { ctx.setDrive(!state.drive); refresh(); },
    sound: async () => { await ctx.toggleSound(!state.sound); refresh(); },
    shot: s => {
      const V = (x, y, z) => ({ x, y, z });
      const shots = {
        engine: [[-4.2, 2.6, 1.6], [-1.3, 0.75, 0], 34, () => { if (car.lid.latched) car.lid.toggle(); }],
        frunk: [[4.4, 2.3, 1.7], [1.45, 0.62, 0], 34, () => { if (car.hood.latched) car.hood.toggle(); }],
        wheel: [[1.9, 0.55, 2.0], [1.2, 0.32, 0.8], 30],
        cockpit: [[1.2, 1.55, -2.1], [0.2, 0.75, -0.2], 40, () => { if (car.doorL.latched) car.doorL.toggle(); }],
      };
      const [p, t, f, fn] = shots[s];
      fn?.();
      import('three').then(T => rig.goto(new T.Vector3(...p), new T.Vector3(...t), f));
      refresh();
    },
  };

  // ---- buttons
  document.addEventListener('click', e => {
    const b = e.target.closest('button');
    if (!b) return;
    const d = b.dataset;
    if (d.cam) A.cam(d.cam);
    else if (d.panel) A.panel(d.panel);
    else if (d.toll) A.toll(d.toll);
    else if (d.ign !== undefined) A.ign(d.ign);
    else if (d.gear) A.gear(d.gear);
    else if (d.lights !== undefined) A.lights(d.lights);
    else if (d.cabin) A.cabin(d.cabin);
    else if (d.wipe) A.wipe(d.wipe);
    else if (d.env) A.env(d.env);
    else if (d.trim) A.trim(d.trim);
    else if (d.shot) A.shot(d.shot);
    else if (b.id === 'turnL') A.turn(-1);
    else if (b.id === 'turnR') A.turn(1);
    else if (b.id === 'hazard') A.hazard();
    else if (b.id === 'hbrake') A.handbrake();
    else if (b.id === 'drive') A.drive();
    else if (b.id === 'snd') A.sound();
    else if (b.id === 'help-btn') $('#help').hidden = false;
    else if (b.id === 'help-close') $('#help').hidden = true;
  });
  const panel = initPanel($('#rack'), $('#grip'));
  function toggleRack() { panel.toggle(); }
  $('#help').addEventListener('click', e => { if (e.target.id === 'help') $('#help').hidden = true; });
  // hold buttons (pointer)
  const holdMap = { throttle: '#throttle', brake: '#brake', flash: '#flash', wash: '#wash', start: '[data-ign="3"]' };
  for (const [k, sel] of Object.entries(holdMap)) {
    const b = $(sel);
    if (!b) continue;
    const on = e => { e.preventDefault(); held[k] = true; b.classList.add('active'); if (k === 'start') startKey(true); if (k === 'wash') car.wipers.wash(true); };
    const off = () => { if (!held[k]) return; held[k] = false; b.classList.remove('active'); if (k === 'start') startKey(false); if (k === 'wash') car.wipers.wash(false); };
    b.addEventListener('pointerdown', on);
    b.addEventListener('pointerup', off); b.addEventListener('pointerleave', off); b.addEventListener('pointercancel', off);
  }
  function startKey(on) {
    if (on) { if (sim.ignition < 2) { sim.setIgnition(2); } audio.key(); sim.setIgnition(3); }
    else if (sim.ignition === 3) sim.setIgnition(2);
    refresh();
  }

  // ---- keyboard
  const keys = {};
  addEventListener('keydown', e => {
    if (e.target.closest?.('input,select,textarea')) return;
    if (e.repeat && !['ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(e.code)) { keys[e.code] = true; return; }
    keys[e.code] = true;
    const free = rig.mode === 'free';
    switch (e.code) {
      case 'Digit1': A.cam('orbit'); break;
      case 'Digit2': A.cam('free'); break;
      case 'Digit3': A.cam('driver'); break;
      case 'Digit4': A.cam('passenger'); break;
      case 'Digit5': A.cam('cinematic'); break;
      case 'KeyO': A.panel('doorL'); break;
      case 'KeyP': A.panel('doorR'); break;
      case 'KeyH': A.panel('hood'); break;
      case 'KeyT': A.panel('lid'); break;
      case 'KeyY': A.panel('fuel'); break;
      case 'BracketLeft': A.toll('L'); break;
      case 'BracketRight': A.toll('R'); break;
      case 'KeyK':
        if (e.shiftKey) { A.ign(0); break; }
        kDown = true; keyHold = 0;
        if (sim.ignition < 2) A.ign(sim.ignition + 1);
        break;
      case 'KeyX': stepGear(1); break;
      case 'KeyZ': stepGear(-1); break;
      case 'KeyN': A.gear('N'); break;
      case 'KeyR': A.gear('R'); break;
      case 'KeyV': A.handbrake(); break;
      case 'KeyG': A.drive(); break;
      case 'KeyL': A.lights((lamps.state.headlights + 1) % 4); break;
      case 'KeyJ': held.flash = true; break;
      case 'Comma': A.turn(-1); break;
      case 'Period': A.turn(1); break;
      case 'Slash': A.hazard(); break;
      case 'KeyI': A.wipe({ off: 'int', int: 'low', low: 'high', high: 'off' }[car.wipers.mode]); break;
      case 'KeyU': held.wash = true; car.wipers.wash(true); break;
      case 'KeyB': A.env({ studio: 'day', day: 'night', night: 'studio' }[state.env]); break;
      case 'KeyM': A.sound(); break;
      case 'Tab': e.preventDefault(); toggleRack(); break;
      case 'Escape': $('#help').hidden = true; break;
      case 'ArrowUp': case 'ArrowDown': case 'ArrowLeft': case 'ArrowRight': e.preventDefault(); break;
      default: if (e.key === '?') $('#help').hidden = !$('#help').hidden;
    }
    if (free && ['KeyW', 'KeyA', 'KeyS', 'KeyD'].includes(e.code)) e.preventDefault();
  });
  addEventListener('keyup', e => {
    keys[e.code] = false;
    if (e.code === 'KeyK') { kDown = false; if (sim.ignition === 3) { sim.setIgnition(2); refresh(); } }
    if (e.code === 'KeyJ') held.flash = false;
    if (e.code === 'KeyU') { held.wash = false; car.wipers.wash(false); }
  });
  addEventListener('blur', () => { for (const k in keys) keys[k] = false; });
  const ORDER = ['R', 'N', '1', '2', '3', '4', '5'];
  function stepGear(d) { const i = ORDER.indexOf(String(sim.gear)); A.gear(ORDER[Math.max(0, Math.min(ORDER.length - 1, i + d))]); }

  // ---- per-frame input integration
  ui.input = dt => {
    if (kDown) { keyHold += dt; if (keyHold > 0.35 && sim.ignition === 2) { audio.key(); sim.setIgnition(3); refresh(); } }
    const thr = held.throttle || keys.ArrowUp;
    const brk = held.brake || keys.ArrowDown || (keys.Space && rig.mode !== 'free');
    sim.throttle += ((thr ? 1 : 0) - sim.throttle) * Math.min(1, dt * (thr ? 5 : 9));
    sim.brake += ((brk ? 1 : 0) - sim.brake) * Math.min(1, dt * (brk ? 7 : 10));
    lamps.state.brake = sim.brake > 0.08;
    lamps.state.flash = held.flash;
    // steering: ~1.2 turns each way (2.4 turns lock to lock), self-centres with speed
    const sl = keys.ArrowLeft, sr = keys.ArrowRight;
    const maxA = 1.2 * 2 * Math.PI;
    const rate = 4.5;
    if (sl || sr) ui.steer += (sl ? 1 : -1) * rate * dt;
    else if (Math.abs(sim.speed) > 0.5) ui.steer -= ui.steer * Math.min(1, dt * Math.min(3, Math.abs(sim.speed) * 0.3));
    ui.steer = Math.max(-maxA, Math.min(maxA, ui.steer));
    // auto clutch: shift dip, then launch slip control
    if (shiftT > 0) { shiftT -= dt; sim.clutch = 1; }
    else if (state.drive && sim.gear !== 'N' && sim.running) {
      // a driver's left foot: slip the clutch to launch, disengage before the engine would stall
      const idle = sim.idleTarget();
      let want = 0;
      if (sim.lockedRpm < idle * 1.05) want = sim.throttle > 0.05 ? Math.max(0, Math.min(1, 1 - (sim.rpm - 1100) / 900)) : 1;
      if (sim.brake > 0.5 && sim.lockedRpm < idle * 1.3) want = 1;
      sim.clutch += (want - sim.clutch) * Math.min(1, dt * (want > sim.clutch ? 14 : 6));
    } else sim.clutch += (0 - sim.clutch) * Math.min(1, dt * 6);
  };
  ui.steer = 0;

  // ---- HUD
  let hudT = 0, lastEng = '';
  ui.hud = () => {
    const now = performance.now();
    if (now - hudT < 100) return;
    hudT = now;
    const on = sim.electrics;
    $('#h-speed').textContent = Math.round(sim.speedMph) + '';
    $('#h-rpm').textContent = Math.round(sim.rpm / 10) * 10 + '';
    $('#h-gear').textContent = sim.gear;
    const eng = { off: 'Off', cranking: 'Cranking', running: 'Running', stalling: 'Stopping' }[sim.engine];
    $('#h-eng').textContent = eng;
    $('#h-temp').textContent = on ? Math.round(sim.coolantF) + ' °F' : '–';
    $('#h-oil').textContent = on ? Math.round(sim.oilPsi) + ' psi' : '–';
    $('#h-volt').textContent = on ? sim.volts.toFixed(1) + ' V' : '–';
    $('#h-fuel').textContent = on ? Math.round(sim.fuel * 100) + ' %' : '–';
    $('#h-oil').classList.toggle('warn', on && sim.oil < 0.35);
    const es = sim.engine === 'running' ? `idle ${Math.round(sim.idleTarget())} rpm` : sim.engine === 'cranking' ? 'cranking…' : 'engine off';
    if (es !== lastEng) { $('#eng-state').textContent = es; lastEng = es; }
    if (sim.engine === 'off' && sim.ignition === 3) {}
    // flasher feedback on the turn buttons
    $('#turnL').classList.toggle('blink', lamps.flasher.on && (lamps.state.turn < 0 || lamps.state.hazard));
    $('#turnR').classList.toggle('blink', lamps.flasher.on && (lamps.state.turn > 0 || lamps.state.hazard));
    $('#hazard').classList.toggle('blink', lamps.flasher.on && lamps.state.hazard);
    group('ign', sim.ignition, 'ign');
  };
  ui.refresh = refresh;
  refresh();
  return ui;
}
