// Vehicle systems simulation for the DMC-12: ignition & electrics, PRV ZMJ-159 2.85 L V6,
// cooling, lubrication, fuel, 5-speed Renault transaxle, longitudinal + bicycle-model dynamics.
// Published figures: 130 hp @ 5500 rpm, 153 lb-ft (208 Nm) @ 2750 rpm, gears 3.364 / 2.059 /
// 1.381 / 1.057 / 0.8205, R 3.1818, final drive 3.44, kerb 1290 kg (38/62), 51.6 L tank.

const GEARS = { R: -3.1818, N: 0, 1: 3.364, 2: 2.059, 3: 1.381, 4: 1.057, 5: 0.8205 };
const FINAL = 3.44;
const R_TYRE = 0.299;           // rear rolling radius (low-profile tyres on the stock 15 in. rims, as on the reference car)
const MASS = 1290 + 80;         // kerb + driver
const CDA = 0.338 * 1.80;       // drag area (m^2): Cd 0.338
const CRR = 0.013;
const IDLE_HOT = 850, IDLE_COLD = 1150, REDLINE = 6000, LIMIT = 6400;

// torque curve (Nm) vs rpm, wide-open throttle
const TQ = [[600, 120], [1000, 160], [1500, 182], [2000, 198], [2750, 208], [3500, 203], [4500, 186], [5500, 171], [6000, 152], [6500, 120]];
function wot(rpm) {
  if (rpm <= TQ[0][0]) return TQ[0][1];
  for (let i = 1; i < TQ.length; i++) if (rpm <= TQ[i][0]) {
    const [a, ta] = TQ[i - 1], [b, tb] = TQ[i];
    return ta + (tb - ta) * (rpm - a) / (b - a);
  }
  return TQ[TQ.length - 1][1];
}

export class VehicleSim {
  constructor() {
    this.ignition = 0;          // 0 OFF, 1 ACC, 2 ON, 3 START (momentary)
    this.engine = 'off';        // off | cranking | running | stalling
    this.rpm = 0;
    this.crankT = 0;
    this.catchAt = 1.2;
    this.throttle = 0;          // pedal 0..1 (user)
    this.brake = 0;
    this.clutch = 0;            // pedal 0..1 (1 = disengaged)
    this.handbrake = 1;
    this.gear = 'N';
    this.speed = 0;             // m/s (forward +)
    this.accel = 0; this.latAccel = 0;
    this.yaw = 0; this.x = 0; this.z = 0; this.yawRate = 0;
    this.steer = 0;             // road wheel angle (rad)
    this.odometer = 23571.4;    // km... shown in miles on the US cluster
    this.trip = 128.6;
    this.coolant = 18;          // deg C (ambient start)
    this.ambient = 18;
    this.oil = 0;               // bar
    this.volts = 12.55;
    this.battery = 12.62;
    this.fuel = 0.64;           // tank fraction
    this.loadAmps = 0;
    this.shake = 0;
    this.firingHz = 0;
    this.bulbCheck = 0;
    this.drive = false;         // dynamics enabled (drive mode)
    this.events = [];
    this.limiterCut = false;
  }

  emit(e) { this.events.push(e); }

  setIgnition(pos) {
    pos = Math.max(0, Math.min(3, pos));
    const prev = this.ignition;
    this.ignition = pos;
    if (pos >= 2 && prev < 2) { this.bulbCheck = 2.2; this.emit('ignOn'); }
    if (pos === 3 && this.engine === 'off') {
      this.engine = 'cranking'; this.crankT = 0;
      // colder engines take longer to fire (K-Jetronic cold start valve)
      this.catchAt = 0.75 + Math.max(0, (60 - this.coolant) / 60) * 0.9 + Math.random() * 0.35;
      this.emit('crank');
    }
    if (pos < 3 && this.engine === 'cranking') { this.engine = 'off'; this.emit('crankStop'); }
    if (pos < 2 && this.engine === 'running') { this.engine = 'stalling'; this.emit('stop'); }
  }

  get running() { return this.engine === 'running'; }
  get electrics() { return this.ignition >= 2; }

  idleTarget() {
    const w = Math.min(1, Math.max(0, (this.coolant - 20) / 60));
    return IDLE_COLD + (IDLE_HOT - IDLE_COLD) * w;
  }

  step(dt) {
    dt = Math.min(Math.max(dt, 1e-4), 0.05);
    const ig = this.ignition;
    // ---------------- engine speed
    const ratio = GEARS[this.gear] * FINAL;
    const wheelRpm = (this.speed / R_TYRE) * 60 / (2 * Math.PI);
    const engaged = this.drive && ratio !== 0 && this.clutch < 0.5;
    if (this.engine === 'cranking') {
      this.crankT += dt;
      const target = 190 + 25 * Math.sin(this.crankT * 30);
      this.rpm += (target - this.rpm) * Math.min(1, dt * 8);
      if (this.crankT > this.catchAt && this.fuel > 0.005) { this.engine = 'running'; this.emit('fire'); this.rpm = 650; this.flare = 1; }
    } else if (this.engine === 'running') {
      const idle = this.idleTarget();
      const thr = this.throttle;
      if (engaged) {
        // engine locked to the wheels through the clutch (slip handled below)
        const tgt = Math.abs(wheelRpm * ratio);
        const slip = this.clutch;
        this.rpm += ((tgt * (1 - slip) + (idle + thr * 5200) * slip) - this.rpm) * Math.min(1, dt * 12);
        if (this.rpm < 450) { this.engine = 'stalling'; this.emit('stall'); }
      } else {
        // free revving: rise ~3000 rpm/s at WOT, fall ~1500 rpm/s
        const tgt = idle + thr * (LIMIT + 200 - idle) + (this.flare || 0) * 600;
        const rate = tgt > this.rpm ? 2.2 + thr * 3 : 1.4;
        this.rpm += (tgt - this.rpm) * Math.min(1, dt * rate);
      }
      this.flare = Math.max(0, (this.flare || 0) - dt * 0.9);
      // rev limiter: fuel cut bounce
      if (this.rpm > LIMIT) { this.limiterCut = true; this.rpm -= 350; this.emit('limiter'); } else this.limiterCut = false;
      if (ig < 2) { this.engine = 'stalling'; this.emit('stop'); }
    } else if (this.engine === 'stalling' || this.engine === 'off') {
      this.rpm += (0 - this.rpm) * Math.min(1, dt * 3.5);
      if (this.rpm < 20) { this.rpm = 0; this.engine = 'off'; }
    }
    this.firingHz = this.rpm / 60 * 3;
    this.shake = this.engine === 'running' ? (this.rpm < 1300 ? 1.0 : 0.5) : this.engine === 'cranking' ? 1.6 : this.rpm > 50 ? 0.8 : 0;

    // ---------------- electrics
    const lampLoad = this.loadAmps;
    let v;
    if (ig < 2) v = 0;
    else if (this.engine === 'cranking') v = this.battery - 2.3 - 0.4 * Math.sin(this.crankT * 30) ** 2;
    else if (this.engine === 'running' && this.rpm > 700) v = 14.15 - lampLoad * 0.012 + Math.max(0, 1100 - this.rpm) * -0.0006;
    else v = this.battery - lampLoad * 0.018;
    this.volts += (v - this.volts) * Math.min(1, dt * 6);
    if (this.engine === 'running') this.battery += (12.75 - this.battery) * dt * 0.01;
    else if (ig >= 1) this.battery -= lampLoad * dt * 2e-6;

    // ---------------- cooling (lumped heat capacity, thermostat at 88 C, fans above 98 C)
    const heat = this.engine === 'running' ? (6.0 + this.rpm / 1000 * 2.4 + this.throttle * 9) : 0;
    const thermostat = Math.min(1, Math.max(0, (this.coolant - 82) / 10));
    const fan = this.coolant > 98 ? 1 : 0;
    const airflow = Math.abs(this.speed) * 0.08;
    const cool = (this.coolant - this.ambient) * (0.012 + thermostat * (0.10 + airflow + fan * 0.12));
    this.coolant += (heat - cool) * dt * 0.03;     // ~5 min to operating temperature at idle

    // ---------------- lubrication (relief valve ~5 bar; thinner oil when hot)
    const visc = 1.0 + Math.max(0, (70 - this.coolant) / 70) * 0.9;
    const oilT = this.rpm > 100 ? Math.min(5.0, (0.6 + this.rpm / 1000 * 1.25) * visc) : 0;
    this.oil += (oilT - this.oil) * Math.min(1, dt * 4);

    // ---------------- fuel (BSFC-ish)
    if (this.engine === 'running') {
      const lph = 1.1 + this.rpm / 1000 * 0.6 + this.throttle * this.rpm / 1000 * 2.4;
      this.fuel = Math.max(0, this.fuel - lph / 3600 * dt / 51.6);
      if (this.fuel <= 0) { this.engine = 'stalling'; this.emit('stall'); }
    }

    // ---------------- vehicle dynamics (only in drive mode)
    const prevV = this.speed;
    if (this.drive) {
      let Fx = 0;
      if (this.engine === 'running' && ratio !== 0 && this.clutch < 0.98) {
        // brake torque at the flywheel: friction + pumping + accessories rise with rpm
        const fric = 9 + this.rpm / 1000 * 3.2 + (1 - this.throttle) * this.rpm / 6000 * 22;
        let T = wot(this.rpm) * this.throttle - fric;
        if (this.limiterCut) T = 0;
        Fx = T * ratio * 0.86 / R_TYRE * (1 - this.clutch);
        // launch: clutch slip lets the engine hold revs; limit by rear-axle traction (62% rear, mu 0.95)
        Fx = Math.max(-0.95 * 9.81 * MASS * 0.62, Math.min(0.95 * 9.81 * MASS * 0.62, Fx));
      }
      const v0 = this.speed;
      const drag = 0.5 * 1.2 * CDA * v0 * Math.abs(v0) + CRR * MASS * 9.81 * Math.sign(v0) * Math.min(1, Math.abs(v0) * 4);
      const brakeF = (this.brake * 0.92 + this.handbrake * 0.25) * 9.81 * MASS;
      let a = (Fx - drag) / MASS;
      const bdec = brakeF / MASS;
      if (Math.abs(v0) < 0.05 && Math.abs(a) < bdec) { this.speed = 0; a = 0; }
      else { a -= Math.sign(v0 || a) * bdec; this.speed += a * dt; if (v0 !== 0 && Math.sign(this.speed) !== Math.sign(v0) && bdec > 0) this.speed = 0; }
      // kinematic bicycle model with a speed-dependent understeer gradient
      const L = 2.413;
      const k = 1 / (1 + this.speed * this.speed / 420);
      this.yawRate = this.speed / L * Math.tan(this.steer) * k;
      this.yaw += this.yawRate * dt;
      this.x += Math.cos(this.yaw) * this.speed * dt;
      this.z -= Math.sin(this.yaw) * this.speed * dt;
      this.latAccel = this.speed * this.yawRate;
      this.odometer += Math.abs(this.speed) * dt / 1000;
      this.trip += Math.abs(this.speed) * dt / 1000;
    } else {
      this.speed = 0; this.latAccel = 0;
    }
    this.accel += ((this.speed - prevV) / dt - this.accel) * Math.min(1, dt * 10);
    this.bulbCheck = Math.max(0, this.bulbCheck - dt);
  }

  // engine speed the wheels would force through the current gear with the clutch engaged
  get lockedRpm() { return Math.abs((this.speed / R_TYRE) * 60 / (2 * Math.PI) * GEARS[this.gear] * FINAL); }

  get speedMph() { return Math.abs(this.speed) * 2.23694; }
  get coolantF() { return this.coolant * 9 / 5 + 32; }
  get oilPsi() { return this.oil * 14.5038; }
}

export const SIM_CONST = { GEARS, FINAL, REDLINE, LIMIT };
