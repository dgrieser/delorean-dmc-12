# delorean-dmc-12

An interactive, browser-based DeLorean DMC-12. The body, cabin and engine bay are built from
scratch in code: signed distance fields sculpt them, Blender assembles them and bakes ambient
occlusion, and three.js renders them with brushed-stainless PBR materials. The wheels and tyres
are Peter_D's CC BY model (see Credits). Doors, bonnet, engine cover, lights, gauges, wipers and
the engine are all simulated.

## Run it

```bash
cd web
python3 -m http.server 8000
# open http://localhost:8000
```

three.js 0.170 loads from jsDelivr, so the page needs internet access. Add `?env=day` or
`?env=night` to start in a scene, or `?lite` to force the low-quality mode used on phones.

## What you can do

| Area | Controls |
|---|---|
| **Cameras** | Orbit, free roam (WASD/QE, Shift = fast, drag to look), driver seat, passenger seat (drag to look around, scroll to zoom), cinematic. Preset shots: engine bay, front trunk, wheel, cockpit. |
| **Body** | Gull-wing doors with a torsion-bar + gas-strut model, bonnet and louvred engine cover on gas struts. Panels swing, settle and latch, with sound. |
| **Ignition** | Off → Acc → On → Start (hold). The starter cranks, the V6 fires with a cold-start fast idle that settles as the coolant warms. Rev limiter at 6400 rpm. |
| **Instruments** | 85 mph speedometer with a km/h inner scale and odometer, 8000 rpm tach, volts, coolant, oil pressure and fuel. Each needle has its own dynamics (fast magnetic movements, slow bimetal ones). Bulb check at key-on, plus warning lamps (brake, oil, charge, door, fuel, beam, indicators), panel illumination, console clock and radio display. |
| **Lights** | Park, low and high beam (spot lights with a beam-pattern cookie and cut-off), flash-to-pass, indicators and hazards at 85 flashes/min with relay clicks, brake and reverse lamps, side markers, dome and door courtesy lamps. The bulbs have warm-up and cool-down time. |
| **Wipers** | Interval, low and high, plus washer. The tandem arms follow the curved windscreen. |
| **Driving** | Drive mode moves the car under its own power. The torque curve, 5-speed gear ratios, final drive, drag, rolling resistance, traction limit, Ackermann steering and body pitch/roll come from published DMC-12 figures. |
| **Scenes** | Studio: a white cyclorama under a car-photography light set tuned panel by panel against the reference photos (a big softbox behind the camera, dark ceiling, lit backdrop, white floor); the set turns with the orbit camera, as on a turntable shoot. Day (sunlit open lot) and night (city square under street lamps) are photographic HDRIs with a shadow-casting key light measured from the photo. The car's own lamps light the ground. |
| **Trim** | Grey or black hide interior. |

Press `?` in the app for the full keyboard map. The control panel has a latch on top: drag it
to any height, all the way down so only the latch shows, and tap it to fold or unfold.

## How it is built

```
tools/model/sdf.py, extract.py   SDF primitives, sparse marching cubes, crease refinement,
                                 attribute-aware decimation (meshoptimizer via gltfpack)
tools/model/body.py              body shell: crease line, leaned flanks, wedge nose, fastback,
                                 wheel arches, panel regions (doors, bonnet, cover, glass)
tools/model/details.py           quad sealed-beam headlamps, grille + DMC badge, tail-lamp grid,
                                 louvres, mirrors, markers, liners, exhaust, lettering
tools/model/interior.py          seats, dash + binnacle, console, door cards, steering wheel,
                                 pedals, shifter, handbrake, carpets, seals
tools/model/engine.py            PRV V6 engine bay, front luggage compartment
tools/model/build_edges.py       door edge walls and aperture jambs
tools/model/wheels.py            Blender: procedural wheel assemblies, discs, calipers
tools/model/wheels_pd.py         Blender: fits Peter_D's wheels and tyres into those assemblies
tools/model/assemble.py          Blender: assembles all parts, pivots, bakes two AO sets
                                 (doors shut / open) into vertex attributes, exports glTF
tools/pack.py                    quantised, delta-coded, gzip container (web/assets/*.bin)
tools/tex/                       procedural textures, CC0 scan import; prep_hdri.py (day/night HDRIs), studio_env.py
tools/ref/                       reference-photo calibration, renders from the photo cameras, overlays
web/js/                          viewer: materials, environment, car rig, lamps, cluster,
                                 vehicle simulation, procedural engine audio, cameras, UI
```

To rebuild the assets (needs Blender 4 or 5, Python with numpy/scipy/scikit-image/trimesh, and
`npm install` in `tools/`):

```bash
cd tools/model
python3 build_shell.py && python3 build_trim.py && python3 build_details.py
python3 build_interior.py && python3 build_engine.py && python3 build_edges.py
blender -b -P wheels_pd.py -- <downloaded "DeLorean wheels" glb>   # or wheels.py for the procedural set
python3 manifest.py
blender -b -P assemble.py -- ../../web/assets/dmc12_raw.glb --ao
cd .. && python3 pack.py ../web/assets/dmc12_raw.glb ../web/assets/car
python3 pack.py out/wheels.glb ../web/assets/wheels
```

`python3 tools/b64split.py <dir>` writes a text-only copy of `web/` (binary payloads as base64
chunks, which `web/js/fetchbin.js` falls back to) for hosts that only serve text and images.

Dimensions follow published figures: wheelbase 2413 mm, track 1590/1588 mm, height 1140 mm.
Everything else is measured from the studio set in `ref/studio/` (see its README):
`tools/ref/calibrate.py` calibrates the eight photos against each other (a bundle adjustment on
the wheel centres and ~25 body landmarks such as lamp corners, markers, the antenna base and the
windscreen corners, with the wheelbase setting the scale), and the body's profiles, plan taper,
windscreen rake, beltline, lamp layout and bumper bands were read off the calibrated views and
back-projected into the car frame. To check the model against the photos:

```bash
python3 -m http.server 8123 &                        # from the repo root
node tools/ref/shots.mjs /tmp/shots                  # the viewer from each photo's camera
python3 tools/ref/compare.py /tmp/shots /tmp/cmp     # photo/render stacks and overlays
```

The reference car sits lower than a stock US car on low-profile tyres (wheel centres 271 / 298 mm
above the floor); the model follows it (`STANCE` and `R_F` / `R_R` in `tools/model/body.py`, the
tyre squash in `web/js/car.js`). It has the later bonnet without a fuel flap.

## Credits

- Wheels and tyres: ["DeLorean wheels"](https://sketchfab.com/3d-models/delorean-wheels-813336c9381a4772a8a1ed1e7c6fae42)
  by [Peter_D](https://sketchfab.com/better_peter), licensed
  [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/). Decimated for the web and fitted to
  the car's hubs and brakes (`tools/model/wheels_pd.py`); textures re-encoded as JPEG.
- Day and night HDRI environments: CC0 from [Poly Haven](https://polyhaven.com) (Driving School,
  Hansaplatz); see `web/assets/env/NOTES.md`. The studio environment is generated.
- Brushed stainless, leather and carpet maps: CC0 scans from [ambientCG](https://ambientcg.com)
  (Metal009, Leather026, Carpet012), converted by `tools/tex/import_cc0.py`.
