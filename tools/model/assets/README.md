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
