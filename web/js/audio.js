// Procedural audio: odd-fire PRV V6 engine (90/150 deg firing intervals), starter motor,
// relays, door latches, gas struts and wiper motor. No samples are used.

class EngineDSP {
  constructor(sr) {
    this.sr = sr; this.phi = 0; this.rpm = 0; this.load = 0; this.crank = 0; this.on = 0; this.cut = 0;
    this.fire = [0, 150, 240, 390, 480, 630]; this.next = 0; this.cyl = [1.0, 0.93, 1.05, 0.97, 1.02, 0.95];
    this.p = []; // active pulses
    this.r = [this.res(95, 6), this.res(210, 9), this.res(640, 7), this.res(1500, 5)];
    this.lp = 0; this.lp2 = 0; this.hp = 0; this.seed = 1234567; this.st = 0; this.stLp = 0; this.noiseLp = 0;
    this.gain = 0;
  }
  rnd() { this.seed = (this.seed * 1664525 + 1013904223) >>> 0; return this.seed / 4294967296 * 2 - 1; }
  res(f, q) { const w = 2 * Math.PI * f / this.sr, a = Math.sin(w) / (2 * q); const b0 = a, a0 = 1 + a, a1 = -2 * Math.cos(w), a2 = 1 - a;
    return { b0: b0 / a0, b2: -b0 / a0, a1: a1 / a0, a2: a2 / a0, x1: 0, x2: 0, y1: 0, y2: 0 }; }
  biq(s, x) { const y = s.b0 * x + s.b2 * s.x2 - s.a1 * s.y1 - s.a2 * s.y2; s.x2 = s.x1; s.x1 = x; s.y2 = s.y1; s.y1 = y; return y; }
  render(out, n) {
    const sr = this.sr;
    for (let i = 0; i < n; i++) {
      const rpm = this.rpm;
      const prev = this.phi;
      this.phi = (this.phi + rpm / 60 * 360 / sr) % 720;
      // firing events
      if (this.on > 0.01 && rpm > 60) {
        const f = this.fire[this.next];
        const crossed = prev <= this.phi ? (prev < f && this.phi >= f) : (prev < f || this.phi >= f);
        if (crossed) {
          const amp = this.cut ? 0.05 : (0.22 + this.load * 0.95) * this.cyl[this.next] * (1 + this.rnd() * 0.08);
          this.p.push({ t: 0, a: amp });
          this.next = (this.next + 1) % 6;
        }
      }
      let x = 0;
      for (let k = this.p.length - 1; k >= 0; k--) {
        const q = this.p[k];
        const env = Math.exp(-q.t * (260 + rpm * 0.03)) * q.a;
        x += env * (this.rnd() * 0.55 + Math.sin(q.t * 2 * Math.PI * 70) * 0.8);
        q.t += 1 / sr;
        if (q.t > 0.03) this.p.splice(k, 1);
      }
      // exhaust resonances + body
      const e = this.biq(this.r[0], x) * 1.3 + this.biq(this.r[1], x) * 0.9 + this.biq(this.r[2], x) * (0.25 + this.load * 0.4) + this.biq(this.r[3], x) * 0.12 * this.load;
      const cutoff = 0.06 + Math.min(0.5, rpm / 9000) * (0.4 + this.load * 0.5);
      this.lp += (e - this.lp) * cutoff;
      // intake / mechanical noise
      const nz = this.rnd();
      this.noiseLp += (nz - this.noiseLp) * 0.25;
      const intake = (nz - this.noiseLp) * this.load * Math.min(1, rpm / 4000) * 0.05 + this.noiseLp * 0.012 * Math.min(1, rpm / 3000);
      // starter motor: whine + compression rhythm
      let st = 0;
      if (this.crank > 0.01) {
        this.st += 2 * Math.PI * (1650 + 200 * Math.sin(this.phi / 720 * 2 * Math.PI * 3)) / sr;
        const comp = 0.55 + 0.45 * Math.sin(this.phi / 720 * 2 * Math.PI * 3);
        st = (Math.sin(this.st) * 0.10 + Math.sin(this.st * 0.5) * 0.12 + nz * 0.05) * comp * this.crank;
      }
      const g = this.on;
      this.gain += (g - this.gain) * 0.0008;
      let y = (this.lp * 1.6 + intake) * this.gain + st;
      // gentle saturation
      y = Math.tanh(y * 1.3) * 0.8;
      out[i] = y;
    }
  }
}
const ENGINE_DSP = EngineDSP.toString();

export class CarAudio {
  constructor() {
    this.ctx = null;
    this.enabled = false;
    this.params = { rpm: 0, load: 0, crank: 0, on: 0, cut: 0 };
    this.inside = 0;
  }

  async start() {
    if (this.ctx) { await this.ctx.resume(); this.enabled = true; return; }
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    this.ctx = ctx;
    this.master = ctx.createGain(); this.master.gain.value = 0.7;
    this.cabinLP = ctx.createBiquadFilter(); this.cabinLP.type = 'lowpass'; this.cabinLP.frequency.value = 18000;
    this.cabinLP.connect(this.master); this.master.connect(ctx.destination);
    this.engineOut = ctx.createGain(); this.engineOut.gain.value = 0.9; this.engineOut.connect(this.cabinLP);
    try {
      const src = ENGINE_DSP + `
class P extends AudioWorkletProcessor {
  constructor() { super(); this.d = new EngineDSP(sampleRate); this.port.onmessage = e => Object.assign(this.d, e.data); }
  process(_, outputs) { const o = outputs[0][0]; this.d.render(o, o.length); for (let c = 1; c < outputs[0].length; c++) outputs[0][c].set(o); return true; }
}
registerProcessor('engine-dsp', P);`;
      const url = URL.createObjectURL(new Blob([src], { type: 'application/javascript' }));
      await ctx.audioWorklet.addModule(url);
      this.node = new AudioWorkletNode(ctx, 'engine-dsp', { outputChannelCount: [2] });
      this.post = p => this.node.port.postMessage(p);
    } catch (e) {
      // fallback: ScriptProcessor running the same DSP on the main thread
      const dsp = new EngineDSP(ctx.sampleRate);
      this.node = ctx.createScriptProcessor(1024, 0, 2);
      this.node.onaudioprocess = ev => { const o = ev.outputBuffer.getChannelData(0); dsp.render(o, o.length); ev.outputBuffer.getChannelData(1).set(o); };
      this.post = p => Object.assign(dsp, p);
    }
    this.node.connect(this.engineOut);
    // continuous wiper motor + strut hiss
    this.noise = ctx.createBuffer(1, ctx.sampleRate * 2, ctx.sampleRate);
    const d = this.noise.getChannelData(0);
    for (let i = 0; i < d.length; i++) d[i] = Math.random() * 2 - 1;
    this.wiperGain = ctx.createGain(); this.wiperGain.gain.value = 0;
    const wn = ctx.createBufferSource(); wn.buffer = this.noise; wn.loop = true;
    const wf = ctx.createBiquadFilter(); wf.type = 'bandpass'; wf.frequency.value = 900; wf.Q.value = 0.8;
    const wm = ctx.createOscillator(); wm.type = 'sawtooth'; wm.frequency.value = 95;
    const wmg = ctx.createGain(); wmg.gain.value = 0.03;
    wn.connect(wf).connect(this.wiperGain); wm.connect(wmg).connect(this.wiperGain);
    this.wiperGain.connect(this.cabinLP); wn.start(); wm.start();
    this.hissGain = ctx.createGain(); this.hissGain.gain.value = 0;
    const hn = ctx.createBufferSource(); hn.buffer = this.noise; hn.loop = true; hn.playbackRate.value = 0.7;
    const hf = ctx.createBiquadFilter(); hf.type = 'highpass'; hf.frequency.value = 2500;
    hn.connect(hf).connect(this.hissGain).connect(this.cabinLP); hn.start();
    this.enabled = true;
  }

  stop() { this.enabled = false; this.ctx?.suspend(); }

  update(sim, opts) {
    if (!this.ctx || !this.enabled) return;
    const on = sim.engine === 'running' || (sim.engine === 'stalling' && sim.rpm > 80) ? 1 : 0;
    this.post?.({ rpm: sim.rpm, load: Math.max(sim.throttle, 0.05), crank: sim.engine === 'cranking' ? 1 : 0, on, cut: sim.limiterCut ? 1 : 0 });
    const t = this.ctx.currentTime;
    // inside with doors shut: strong low-pass + level drop; louder exhaust when outside behind
    const closed = 1 - Math.min(1, opts.doorOpen * 3);
    const muffle = opts.inside ? closed : 0;
    this.cabinLP.frequency.setTargetAtTime(18000 - muffle * 16200, t, 0.05);
    this.engineOut.gain.setTargetAtTime((opts.inside ? 0.65 + 0.35 * (1 - muffle) : 0.95) * opts.engineDistance, t, 0.05);
    this.wiperGain.gain.setTargetAtTime(opts.wiper * (opts.inside ? 0.05 : 0.02), t, 0.04);
    this.hissGain.gain.setTargetAtTime(opts.strut * 0.03, t, 0.03);
  }

  // one-shots ---------------------------------------------------------------------------------
  click(level = 0.3, freq = 3200, dur = 0.012) {
    if (!this.ctx || !this.enabled) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const src = ctx.createBufferSource(); src.buffer = this.noise;
    const f = ctx.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = freq; f.Q.value = 3;
    const g = ctx.createGain(); g.gain.setValueAtTime(level, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    src.connect(f).connect(g).connect(this.cabinLP);
    src.start(t, Math.random()); src.stop(t + dur + 0.02);
  }
  relay(on) { this.click(on ? 0.35 : 0.22, on ? 2400 : 1900, 0.018); }
  thunk(level = 0.8, freq = 120, dur = 0.25) {
    if (!this.ctx || !this.enabled) return;
    const ctx = this.ctx, t = ctx.currentTime;
    const o = ctx.createOscillator(); o.type = 'sine';
    o.frequency.setValueAtTime(freq * 1.8, t); o.frequency.exponentialRampToValueAtTime(freq * 0.7, t + dur);
    const g = ctx.createGain(); g.gain.setValueAtTime(level, t); g.gain.exponentialRampToValueAtTime(0.0001, t + dur);
    o.connect(g).connect(this.cabinLP); o.start(t); o.stop(t + dur + 0.05);
    this.click(level * 0.6, 1400, 0.03);
  }
  latch(strength) { this.thunk(Math.min(1, 0.3 + strength * 0.4), 95, 0.32); }
  unlatch() { this.click(0.5, 1800, 0.03); setTimeout(() => this.click(0.3, 900, 0.05), 40); }
  key() { this.click(0.4, 4200, 0.01); setTimeout(() => this.click(0.25, 3000, 0.012), 60); }
  switchClick() { this.click(0.25, 3800, 0.008); }
}
