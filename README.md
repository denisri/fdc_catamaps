# fdc_catamaps
Process SVG Inkscape maps to produce 2D/3D catacombs maps (Fond-du-crew maps)

Catacombs maps using SVG source map with codes inside it.

The program allows to produce:

* 2D "readable" maps with symbols changed to larger ones, second level shifted to avoid superimposition of corridors, enlarged zooms, shadowing etc.

* 3D maps to be used in a 3D visualization program, a webGL server, or the CataZoom app.

Requirements:

* Having inkscape installed on the system and available in the PATH.
  A recent version of inkscape (1.0 at least) is recommended to avoid units and
  scaling problems.
* svg_to_mesh submodule and its requirements (part of this project)
* xml ElementTree
* six
* numpy
* scipy

The 3D part has additional requirements:

* soma.aims (https://github.com/brainvisa/aims-free)
* anatomist (https://github.com/brainvisa/anatomist-free and
  https://github.com/brainvisa/anatomist-gpl)
* json
