# Imported DeLorean

Source: user-supplied `1981-dmc-delorean.zip`, nested `source/FINAL_MODEL_DMC12.zip`,
`FINAL_MODEL_DMC12.fbx` and its texture PNGs.

- Archive SHA-256: `7b4d01a7a130bc47cc4cd4340300e12eb7207b6a35ac2869f2b2b68fe8cdcec2`
- FBX SHA-256: `9ff4e8a6c1e2d9884f6670d7c20e38ea036275ec17f5ae1e9259297cc536f1b9`
- No author or license document was included in the supplied archive.

`tools/model/build_donor.py` imports this exact source in Blender and creates the viewer rig.
It preserves the source geometry, UVs and split normals, separates moving panels along the
existing surface seams, and copies the diffuse and normal maps used by `config.json`.
The missing right front marker lens is reflected from the left. Wipers and live dashboard
faces are supplied by the viewer.
The steering wheel is welded across export seams, reconstructed into quads where possible,
and subdivided twice in Blender. Smooth normals round the rim and padded spokes while
retaining the source UV atlas and steering pivot. Other donor geometry keeps its source normals.

The gear boot receives the same smoothing while retaining its folded leather atlas; its
knob is replaced by a rounded runtime mesh attached to the existing moving shifter pivot.
The console deck retains its geometry with a matte vinyl finish and fine-scale grain.

Door trim is assigned as whole UV patches inside the actual painted door outline. Seat-belt
anchors, seat adjusters, dashboard end trim and patches extending beyond that outline stay
on the body. `tools/model/donor_doors.py` closes each painted skin with a steel backing and
continuous front, rear, lower and roof returns, preserving the glass opening and exterior
seam. The old overlapping return strips are omitted. The skin plus generated backing must
form a closed two-manifold mesh before export. Section-based offsets avoid spikes caused
by extruding the source's tiny folded lips.

Studio views 03, 05, 06 and 07 guide the exposed steel ends, thin rubber perimeter seal,
latch plates and warning-light placement. Front and bottom amber lights and the rear red
light mount directly on each donor door's returns and retain the existing lamp controls.
The latch hardware is visual geometry, not a mechanical latch simulation.
`node tools/doortest.mjs` checks cavity-blocking rays and clear window apertures on both
doors at closed, half-open and fully open poses.

Dashboard artwork is redrawn from the user-supplied `US CLUSTER.jpg`,
`DSC01135-HDR-1-1200x800.jpg`, `1981-delorean-dmc-12-6.avif` and
`car_100002_14.webp` / `car_100002_15.webp` references, with the metric cluster
photos used to cross-check panel construction. The viewer keeps its existing US units.
The baked instrument quad (interior component 121) becomes a plain backing; live gauges
sit in front. Interior components 84–87 and 92–93 are replaced by the detailed radio at
the corrected `RadioFace_Pivot`. Its face is generated from vectors, not enlarged atlas pixels.
The radio retains its existing power-dependent display; the added knobs and buttons are visual details.

`web/js/console.js` replaces the native low-resolution HVAC, vent, lighter, switch,
mirror-control and ashtray detail assemblies. It uses the studio interior close-ups
(`10_interior_radio_hvac.jpg`, `11_interior_console_gauge.jpg`), the supplied stock-radio
photo, and `ref/Delorean_early_1981_clock.jpg`. The existing stock lighter/clock layout is
retained rather than adopting the studio car's aftermarket boost gauge. HVAC artwork is
drawn at 2000 × 1060; molded controls and vent slats are geometry, batched by material.
The green segmented clock now sits beside the lighter. Its ignition behavior is preserved,
and the HVAC legends follow the panel illumination/dimmer. These control meshes are visual;
they do not add a new HVAC or mirror-adjustment simulation.

Phong materials are mapped to PBR by surface type. The steel's material/opacity image is not
used as a normal map (the FBX connects it incorrectly). Glass and mirror shading are assigned
explicitly. The engine's lower service cover and upper louvres open together through the
existing Engine Cover control. This is a viewer rig, not an animation supplied with the FBX.

The interior, engine, chassis and badge atlases use alpha cutouts (`alphaTest: 0.5`),
including the transparent white backgrounds around knobs, pedals and decals. These
materials retain opaque depth writes; glass uses blending separately. The body's livery
alpha is a paint mask and is not used to cut holes in the fascia.
The native roof diffuser has its own `cabin_lens` material, using the interior atlas as
an emission map so its lens pattern and dark border remain visible. Dome On/Off/Door
drives both the diffuser and a downward light at the fixture, avoiding ceiling and mirror glare.
`node tools/donor-materialtest.mjs` checks rendered transparent and opaque texels from all
four atlases, including white cabin lettering, against the viewer's live materials.

`car.json`/`car.bin` and `wheels.json`/`wheels.bin` are generated by `tools/pack.py`.
These are separate from the preserved procedural assets one directory above.
