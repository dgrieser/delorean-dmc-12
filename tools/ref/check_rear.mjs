// Validate the assembled rear parts and their live lighting controls.
// Serve the repository root on :8123, then: node tools/ref/check_rear.mjs
import { chromium } from 'playwright-core';

const browser = await chromium.launch({
  executablePath: process.env.CHROME || '/usr/bin/google-chrome',
  args: ['--headless=new', '--enable-gpu', '--use-angle=vulkan', '--enable-features=Vulkan', '--ignore-gpu-blocklist'],
});
const errors = [];
try {
  const page = await browser.newPage({ viewport: { width: 1024, height: 683 } });
  page.on('pageerror', e => errors.push(e.message));
  const url = new URL(process.env.URL || 'http://localhost:8123/web/index.html');
  url.searchParams.set('still', '1'); url.searchParams.set('model', 'original');
  await page.goto(url.href);
  await page.waitForFunction(() => document.title === 'READY', null, { timeout: 300000 });
  const result = await page.evaluate(() => {
    const a = window.app, root = a.car.root;
    const parts = [
      'bumper_letters', 'rear_logo_border', 'rear_band', 'tl_bezel', 'tl_gasket', 'tl_reflectors', 'plate_border',
      'rear_bumper_seal', 'rear_apron_seal', 'rear_timing_cover', 'rear_sump',
      'rear_pulleys', 'rear_belt', 'rear_mechanical_bolts', 'rear_lower_fasteners',
      'rear_suspension', 'rear_dampers', 'rear_damper_rods', 'rear_springs',
      'rear_hoses', 'rear_hose_fittings', 'exhaust_liners', 'rear_logo_border',
      'lid_fasteners', 'lid_seal', 'quarter_vent_frame', 'quarter_vent_fins', 'quarter_vent_back',
    ];
    const meshes = new Map();
    root.traverse(o => {
      if (!o.isMesh) return;
      if (o.material.name === 'fallback') throw Error('Missing material: ' + o.name);
      meshes.set(o.name, o);
    });
    for (const name of parts) {
      const mesh = meshes.get(name);
      if (!mesh || (mesh.geometry.index?.count ?? mesh.geometry.attributes.position?.count ?? 0) < 3) throw Error('Missing geometry: ' + name);
      const positions = mesh.geometry.attributes.position.array;
      if (!positions.every(Number.isFinite)) throw Error('Invalid vertices: ' + name);
    }
    for (const name of ['lid_seal', 'lid_fasteners']) {
      let parent = meshes.get(name).parent;
      while (parent && !parent.name.startsWith('EngineLid')) parent = parent.parent;
      if (!parent) throw Error('Cover fitting does not move with the lid: ' + name);
    }
    const lamps = a.lamps, sim = { ignition: 2, electrics: true, volts: 13.5 };
    const settle = () => { for (let i = 0; i < 60; i++) lamps.update(1 / 60, sim); };
    const intensity = name => lamps.mats[name].emissiveIntensity;
    Object.assign(lamps.state, { headlights: 0, brake: false, reverse: false, turn: 0, hazard: false });
    settle();
    if (intensity('plate_lenses_L') > .001) throw Error('Plate lamp on with parking lamps off');
    lamps.state.headlights = 1;
    settle();
    if (intensity('plate_lenses_L') < 2.9 || intensity('tl_tail_L') < .6) throw Error('Parking lamps failed');
    lamps.state.brake = true; lamps.state.reverse = true;
    settle();
    if (intensity('tl_tail_R') < 3.8 || intensity('tl_rev_R') < 3.9) throw Error('Brake/reverse lamps failed');
    lamps.state.turn = -1; lamps.flasher.t = 0; lamps.update(.1, sim);
    if (intensity('tl_turn_L') < 3.9 || intensity('tl_turn_R') > .001) throw Error('Turn signals are not independent');
    Object.assign(lamps.state, { headlights: 0, brake: false, reverse: false, turn: 0 });
    settle();
    if (intensity('plate_lenses_R') > .001 || intensity('tl_tail_R') > .001) throw Error('Lamps did not switch off');
    return { rearParts: parts.length, materials: 'resolved', vertices: 'finite', coverFittings: 'attached', lighting: 'passed' };
  });
  console.log(JSON.stringify(result, null, 2));
  if (errors.length) throw Error(errors.join('\n'));
} finally {
  await browser.close();
}
