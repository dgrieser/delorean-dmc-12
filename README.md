# delorean-dmc-12

An interactive, browser-based DeLorean DMC-12 showing the supplied FBX car, rigged to the
existing controls. The earlier procedural body, cabin and engine remain available through
`?model=original`, including fitted donor mirrors and Peter_D's wheels.

## Run it

Live: <https://dgrieser.github.io/delorean-dmc-12/> (GitHub Pages, deployed from `web/` on every
push to `main` that touches it, see `.github/workflows/pages.yml`).

Locally:

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
| **Cameras** | Orbit, free roam (WASD/QE, Shift = fast, drag to look), driver seat, passenger seat, cinematic. Touch free roam: one finger looks, two fingers pan sideways/up/down, pinch moves closer/farther. Seat views: drag to look, pinch or scroll to zoom. Preset shots: engine bay, front trunk, wheel, cockpit. |
| **Body** | Gull-wing doors with a torsion-bar + gas-strut model, bonnet and louvred engine cover on gas struts. Panels swing, settle and latch, with sound. |
| **Ignition** | Off → Acc → On → Start (hold). The starter cranks, the V6 fires with a cold-start fast idle that settles as the coolant warms. Rev limiter at 6400 rpm. |
| **Instruments** | 85 mph speedometer with a km/h inner scale and odometer, 8000 rpm tach, volts, coolant, oil pressure and fuel. Each needle has its own dynamics (fast magnetic movements, slow bimetal ones). Bulb check at key-on, plus warning lamps (brake, oil, charge, door, fuel, beam, indicators), panel illumination, console clock and radio display. |
| **Lights** | Park, low and high beam (spot lights with a beam-pattern cookie and cut-off), flash-to-pass, indicators and hazards at 85 flashes/min with relay clicks, brake and reverse lamps, side markers, dome and door courtesy lamps. The bulbs have warm-up and cool-down time. |
| **Wipers** | Interval, low and high, plus washer. The tandem arms follow the curved windscreen. |
| **Driving** | Drive mode moves the car under its own power. The torque curve, 5-speed gear ratios, final drive, drag, rolling resistance, traction limit, Ackermann steering and body pitch/roll come from published DMC-12 figures. |
| **Scenes** | Studio: a white cyclorama under a car-photography light set (a big softbox overhead and one behind the camera, dark walls, white floor). Like the photographer's, it turns with the camera and is re-set for each angle: one set per reference photo angle, blended as you orbit, each fitted to the stainless tones of the photos taken from there. Day (sunlit open lot) and night (city square under street lamps) are photographic HDRIs with a shadow-casting key light measured from the photo. The car's own lamps light the ground. |
| **Trim** | Grey or black hide interior. |

Press `?` in the app for the full keyboard map. The control panel has a latch on top: drag it
to any height, all the way down so only the latch shows, and tap it to fold or unfold.

## Imported model

The imported car uses its own body, interior, engine, wheels and UV textures. Doors (including
mirrors, glass and inner cards), bonnet and its liner, engine covers, steering wheel, pedals,
shifter and handbrake have been separated and parented to the interactive rig. The upper and
lower engine covers open together. Animated wipers, instruments, displays and door warning
lamps use the viewer's existing systems. Wheelbase, tyre radii and window travel follow this
car's geometry.

The default URL opens the imported car. `?model=original` opens our procedural model;
`?model=donor` selects the imported one explicitly. Switching models reloads the viewer.
Original assets and the original build pipeline are preserved. The photographic calibration
and lighting-fit tools still select the original model by default; use `QS='&model=donor'`
with `tools/ref/shots.mjs` to render the imported car from those cameras.

To rebuild the imported assets, extract `source/FINAL_MODEL_DMC12.zip` from the supplied
`1981-dmc-delorean.zip`, then extract its FBX and textures into one directory. From the repo root:

```bash
blender -b --python-exit-code 1 -P tools/model/build_donor.py -- /path/to/FINAL_MODEL_DMC12.fbx
python3 tools/pack.py tools/out/donor-car.glb web/assets/donor/car
python3 tools/pack.py tools/out/donor-wheels.glb web/assets/donor/wheels
```

The importer verifies the source hash, preserves UVs and split normals, translates the source
Phong materials to PBR, and writes a part-selection audit to `tools/out/donor-rig-audit.json`.
Its checked-in output is under `web/assets/donor/`. The small procedural warning-lamp extract
is `tools/model/assets/donor_lamps.npz`; the rest of the moving geometry comes from the FBX.
Source and texture notes are in `web/assets/donor/README.md`.

With the repo served on port 8123, `node tools/modeltest.mjs` tests both models' controls via
their URLs. Set `CHROME` or `URL` to override the browser executable or page.
`node tools/cameratest.mjs` sends real browser touch gestures to check free movement,
pinch zoom, gesture cancellation, seat/orbit behavior and desktop camera controls.
`node tools/lighttest.mjs` checks lighting through the UI on both models, including rendered
lens brightness, indicator cycles and sides, hazards with ignition off, brake/reverse lamps,
and cabin/door controls. Use `URL='http://localhost:8123/web/?lite=1'` to check phone rendering.
Indicators require **Ignition → On**; the engine can remain stopped. Hazards also work with ignition off.
`node tools/dashtest.mjs` checks all six moving needles, odometer updates, warning/backlight
textures and radio power on both models. The reference-drawn US cluster uses a 4096-pixel
canvas; the imported car's cassette radio has a 2048-pixel face, physical knobs/buttons and
a 1024-pixel segmented display. Artwork lives in `web/js/instrument-face.js` and `web/js/radio.js`.
The imported car's centre console is rebuilt in `web/js/console.js`: a 2000-pixel HVAC face,
dished knobs, recessed vent slats, lighter, mirror joystick, window/defrost switch bank,
ashtray and rounded gear knob. The clock uses a 1024-pixel segmented display in the recess
beside the lighter. HVAC printing follows the existing panel lighting and dimmer;
`dashtest.mjs` checks this and clock power. The extra physical controls are visual details;
the existing viewer controls still operate the car.

## How our procedural model is built

```
tools/model/sdf.py, extract.py   SDF primitives, sparse marching cubes, crease refinement,
                                 attribute-aware decimation (meshoptimizer via gltfpack)
tools/model/body.py              body shell: crease line, leaned flanks, wedge nose, fastback,
                                 wheel arches, panel regions (doors, bonnet, cover, glass)
tools/model/details.py           quad sealed-beam headlamps, grille + DMC badge, tail-lamp grid,
                                 louvres, markers, liners, exhaust, lettering
tools/model/mirrors.py           extracted donor mirrors fitted to the window mounts;
                                 exact reflected mesh for the opposite door
tools/model/interior.py          seats, dash + binnacle, console, door cards, steering wheel,
                                 pedals, shifter, handbrake, carpets, seals
tools/model/engine.py            PRV V6 engine bay, front luggage compartment
tools/model/build_edges.py       door edge walls, aperture jambs and rounded rubber seals
tools/model/rear.py              rear fittings, lamp surrounds and visible running gear
tools/model/wheels.py            Blender: procedural wheel assemblies, discs, calipers
tools/model/wheels_pd.py         Blender: fits Peter_D's wheels and tyres into those assemblies
tools/model/assemble.py          Blender: assembles all parts, pivots, bakes two AO sets
                                 (doors shut / open) into vertex attributes, exports glTF
tools/pack.py                    quantised, delta-coded, gzip container (web/assets/*.bin)
tools/tex/                       procedural textures, CC0 scan import; prep_hdri.py (day/night HDRIs),
                                 studio_env.py + studio_fit.py (studio light sets fitted to the photos)
tools/ref/                       reference-photo calibration, renders from the photo cameras, overlays
web/js/                          viewer: materials, environment, car rig, lamps, cluster,
                                 vehicle simulation, procedural engine audio, cameras, UI
```

To rebuild the assets (needs Blender 4 or 5, Python with numpy/scipy/scikit-image/trimesh/Pillow, and
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
windscreen rake, beltline, sail twist, wheel-arch shapes and flares, lamp layout, louvre panel
and bumper bands were read off the calibrated views (the top view gives the plan) and
back-projected into the car frame. The open-door angle was fitted to the door silhouettes, and
the studio light sets (`tools/tex/studio_env.py`) to the photos' stainless tones by
`tools/tex/studio_fit.py`: a parameter fit on measured panel patches, then a gain map over the
directions the panels reflect, from every stainless pixel (`REFL=1 node tools/ref/shots.mjs`
renders those directions). To check the model against the photos:

```bash
python3 -m http.server 8123 &                        # from the repo root
node tools/ref/shots.mjs /tmp/shots                  # the viewer from each photo's camera
python3 tools/ref/compare.py /tmp/shots /tmp/cmp     # photo/render stacks and overlays
node tools/ref/check_rear.mjs                       # rear parts, materials and lamp controls
```

The reference car sits lower than a stock US car on low-profile tyres (wheel centres 271 / 298 mm
above the floor); the model follows it (`STANCE` and `R_F` / `R_R` in `tools/model/body.py`, the
tyre squash in `web/js/car.js`). It has the later bonnet without a fuel flap and Recaro seats; the
model keeps the stock PRV V6 under its engine cover (the photographed car is turbocharged).
The nose and tail panels have a darker finish than the stainless body, with seams on the
flanks behind the corners. The bonnet ends at a split ahead of which the nose panel runs on
to a brow over the lamps (`r_nose` / `r_tail` in `body.py`). The nose uses the `fascia` weight
in `web/js/materials.js`; the rear fascia has a separate smooth satin paint material without
brushed-steel grain. The bumpers and rear valance are graphite grey, with a darker satin
finish on the air dam. At the front, the wing, lower steel strip and air dam share a continuous
rising edge (`front_lower_edge` in `body.py`); the nose cheeks slope forward beneath the rounded
brow, and the recessed chin has rolled corners. These profiles follow the side and front
three-quarter studio views. The upper nose corners taper smoothly into the brow without a
local bulge above the outer lamps. A defined upper edge and a single rounded lower return
join the nose to the bumper ledge. Mirrors have tapered housings, slanted pivot joints,
rounded mounting covers and triangular sails that follow the door skin. Their extraction
bounds include the complete inboard mounting surface.

The open doors include latch plates, front amber and rear red warning lamps, pull loops,
speaker recesses and aperture seals. Their visible gas struts track both mounting points
through the full opening motion. Roof panel corners share the same rounded outline in the
skin, trim and jambs. The windscreen glass and frit extend to the roof header; the builder
rejects a truncated sampling outline. Door-window seals sit above the steel edge; the upper
rear window corners use a shared continuous curve in the steel, glass, seal and inner frame.
The mirrors are extracted from the user-supplied `1981-dmc-delorean.zip`: housing,
glass, pivot and mounting base only (2,909 triangles per side). The assembly is aligned
to the window edge and its contact surface fitted to the curved door. Housing and glass
geometry retain the donor dimensions; the broad glass face uses planar reflection normals.
Both sides come from one mesh, reflected with corrected winding and normals.
`python tools/model/test_mirrors.py` checks extraction bounds, geometry, preserved head shape,
door contact, glass clearance and exact reflection. Source meshes, UVs and extraction
provenance live in `tools/model/assets/`; normal builds do not need the donor archive.
The front jambs stop outside the windscreen opening. Closed-door strut mounts stay under the
sail skin. Rear bumper and vent-strip heights follow the calibrated low rear view;
the twin exhausts pass through a shared central cutout, with the engine and frame exposed
underneath. Each louvre blade is a continuous, slightly crowned solid. The rear grilles have cross braces
and perimeter lips. Their surfaces use shorter triangles
for the vertex AO bake so shadows do not break into large triangular patches.
The rear quarter windows have four curved fins at each aft tip, a recessed black backing,
and glass ending at a curved divider. The windows follow straight rails with rounded tips and blend into a curved
shoulder. The upper sail edge continues straight in plan across the tail-panel seam;
the raked rear return blends in below the lower window rail. The shoulder meets that rail
with a continuous surface. Both wheel-arch flares grow towards their crowns to keep the
overhead outlines smooth; their liners follow the widened lips without changing the openings.
The front arches have a narrow pressed lip blended into the broader wing flare, and the
rubbing-strip ends follow the opening with a small reveal. Finer stainless grain keeps these
contours visible at the reference viewing distances. The tail-panel seams have a consistent rake and a slight convex bow. The front
bumper and steel strip are level across the car, with sloping side returns. The lower rear
apron follows the quarter-panel edge, with a rolled bottom, hose reliefs and a separate seal.
The thin silver band below the bumper has six rounded slots and a central exhaust cutout.
Rear lamps have separate gaskets, rounded grille ribs standing 8 mm ahead of the recessed
fluted lenses, perimeter screw lips and reflector bowls. The fascia rolls into its upper
deck and lower ledge; the bumper and silver band share their rounded corner outline. The
lower apron is a continuous curved shell through the rear corners and side returns.
The plate cassette includes raised pads, a border, fasteners and downward-facing lamps that
follow the parking lights. The bumper wordmark follows the original vector letter outlines, with recessed faces,
rounded moulded bevels and a fine surrounding groove.

`tools/model/rear.py` adds the visible underside fittings from studio views 05/06: a ribbed
casting and sump, pulley faces and belt, engine-cradle plates, suspension links, dampers,
springs, corrugated driveshaft boots and braided hoses with blue fittings. These are visual
reconstructions of the exposed parts; the upper engine remains the stock PRV model. Engine
castings and pipes are no longer clipped at the body floor. Louvre perimeter seals and
fasteners move with the engine cover. The underside is an open perimeter return, so the gaps
between blades show the rear window and engine bay rather than an opaque backing pan. The front intake uses a square wire alpha mask, with a recessed
radiator and retaining rails; its transparent proxy is excluded from the solid AO bake.

## Credits

- Wheels and tyres: ["DeLorean wheels"](https://sketchfab.com/3d-models/delorean-wheels-813336c9381a4772a8a1ed1e7c6fae42)
  by [Peter_D](https://sketchfab.com/better_peter), licensed
  [CC BY 4.0](http://creativecommons.org/licenses/by/4.0/). Decimated for the web and fitted to
  the car's hubs and brakes (`tools/model/wheels_pd.py`); textures re-encoded as JPEG.
- Day and night HDRI environments: CC0 from [Poly Haven](https://polyhaven.com) (Driving School,
  Hansaplatz); see `web/assets/env/NOTES.md`. The studio environment is generated.
- Brushed stainless, leather and carpet maps: CC0 scans from [ambientCG](https://ambientcg.com)
  (Metal009, Leather026, Carpet012), converted by `tools/tex/import_cc0.py`.

- Rear bumper wordmark: DeLorean Motor Company, vector reproduction by Kilyann Le Hen
  ([Wikimedia Commons](https://commons.wikimedia.org/wiki/File:Delorean_DMC-12_Logo.svg),
  PD-textlogo). Source and geometry-mask details: `tools/model/assets/README.md`.

- Imported car and the original model’s door mirrors: extracted from the user-supplied `1981-dmc-delorean.zip`. Source file,
  component selection, hashes and material notes: `tools/model/assets/mirrors.json`.
