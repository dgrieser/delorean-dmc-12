# Rear bumper wordmark

`delorean-wordmark.svg` is the DeLorean wordmark reproduced by Kilyann Le Hen
(Wikimedia Commons user Wizly-08), downloaded from:
https://commons.wikimedia.org/wiki/File:Delorean_DMC-12_Logo.svg

Commons identifies the simple text logo as public domain (PD-textlogo). DeLorean
and its stylized wordmark remain trademarks of DeLorean Motor Company.

`delorean-wordmark.png` is a derived, monochrome geometry mask, not a visible
texture. It preserves the SVG glyph outlines without its surrounding black
margin: 2400 pixels across the letters, with 24 pixels of padding on each side.
`wordmark.py` converts it to a signed distance field for the recessed lettering.
The SVG can be rasterized with Inkscape; crop its non-black bounds, resize to
2400 pixels wide keeping its aspect ratio, then add the 24-pixel black border.

The inset construction was cross-checked against the manufacturer's bumper
letter inserts: https://store.classicdmc.com/a2000016-bumper-letters-stainless.html
The model follows the unpainted lettering in the supplied studio photographs.


# Donor door mirrors

`mirror_housing_source.npz` and `mirror_glass_source.npz` contain only the left
exterior mirror from the supplied `1981-dmc-delorean.zip`, including its base,
pivot and glass. They preserve triangle geometry, split normals and UVs in body
coordinates. `FIT` identifies the mounting-base vertices that may follow the
curved door surface. The right side is reflected during the normal build.
The build rejoins matching position/normal corners for continuous ambient
occlusion, retaining the source's hard edges and original triangles.

The full donor car and its textures are not bundled. The mirror's `Swatches_D.png`
UV region is uniformly sRGB (18, 18, 18), represented by a material colour.
The glass has no image texture and uses the viewer's reflective material.

To repeat extraction, unpack `source/FINAL_MODEL_DMC12.zip` from the supplied
archive, then run from the repository root:

```sh
blender -b --python-exit-code 1 -P tools/model/import_mirrors.py -- /path/to/FINAL_MODEL_DMC12.fbx
python tools/model/build_details.py mirror
```

`mirrors.json` records source hashes, mesh names and selected connected components.
The extractor checks the FBX hash before applying that component selection. No
author or license document was included in the supplied archive; none is inferred.
