# delorean-dmc-12

An interactive, browser-based DeLorean DMC-12. The model is built from scratch in code, no
downloaded meshes. Signed distance fields sculpt it, Blender assembles it and bakes ambient
occlusion, and three.js renders it with brushed-stainless PBR materials. Doors, bonnet, engine
cover, lights, gauges, wipers and the engine are all simulated.

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
| **Body** | Gull-wing doors with a torsion-bar + gas-strut model, bonnet and louvred engine cover on gas struts, fuel flap. Panels swing, settle and latch, with sound. |
| **Ignition** | Off → Acc → On → Start (hold). The starter cranks, the V6 fires with a cold-start fast idle that settles as the coolant warms. Rev limiter at 6400 rpm. |
| **Instruments** | 85 mph speedometer with a km/h inner scale and odometer, 8000 rpm tach, volts, coolant, oil pressure and fuel. Each needle has its own dynamics (fast magnetic movements, slow bimetal ones). Bulb check at key-on, plus warning lamps (brake, oil, charge, door, fuel, beam, indicators), panel illumination, console clock and radio display. |
| **Lights** | Park, low and high beam (spot lights with a beam-pattern cookie and cut-off), flash-to-pass, indicators and hazards at 85 flashes/min with relay clicks, brake and reverse lamps, side markers, dome and door courtesy lamps. The bulbs have warm-up and cool-down time. |
| **Wipers** | Interval, low and high, plus washer. The tandem arms follow the curved windscreen. |
| **Driving** | Drive mode moves the car under its own power. The torque curve, 5-speed gear ratios, final drive, drag, rolling resistance, traction limit, Ackermann steering and body pitch/roll come from published DMC-12 figures. |
| **Scenes** | Studio (polished floor with planar reflection), day (sunlit parking bay), night (wet asphalt, sodium street lamps). The car's own lamps light the ground. |
| **Trim** | Grey or black hide interior. |

Press `?` in the app for the full keyboard map.

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
tools/model/wheels.py            Blender: turbine wheels, tyres with tread, brakes
tools/model/assemble.py          Blender: assembles all parts, pivots, bakes two AO sets
                                 (doors shut / open) into vertex attributes, exports glTF
tools/pack.py                    quantised, delta-coded, gzip container (web/assets/*.bin)
tools/tex/                       procedural textures and Blender-rendered HDR environments
web/js/                          viewer: materials, environment, car rig, lamps, cluster,
                                 vehicle simulation, procedural engine audio, cameras, UI
```

To rebuild the assets (needs Blender 4, Python with numpy/scipy/scikit-image/trimesh, and
`npm install` in `tools/`):

```bash
cd tools/model
python3 build_shell.py && python3 build_trim.py && python3 build_details.py
python3 build_interior.py && python3 build_engine.py
blender -b -P wheels.py
python3 manifest.py
blender -b -P assemble.py -- ../../web/assets/dmc12_raw.glb --ao
cd .. && python3 pack.py ../web/assets/dmc12_raw.glb ../web/assets/car
python3 pack.py out/wheels.glb ../web/assets/wheels
```

Dimensions follow published figures: length 4216 mm, wheelbase 2413 mm, height 1140 mm,
track 1590/1588 mm, 195/60 R14 front and 235/60 R15 rear tyres. The photos in `ref/` were
used for proportions and details.
