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

Usage
-----

* set the ``python`` subdirectory of the project in your ``PYTHONPATH`` environment variable. Under Unix sh/bash shells, this would be::
```
    export PYTHONPATH="~/fdc_catamaps/python:$PYTHONPATH"
```
  (it can be set in a ``.bash_profile`` or ``.bashrc`` init file)

* get or make the source SVG file with codes inside, for instance ``plan_14_fdc_2021_04_29.svg``

* go to the directory containing it
* run the module `catamap` as a program:
```
    python -m catamap --2d plan_14_fdc_2021_04_29.svg
```
It should work using either python2 or python3.
The 2D maps options will produce files with suffixes in the current directory:
modified .svg files, .pdf and .jpg files.

The 3D maps options will produce meshes in a subdirectory.

Comandline options (may be used together):

-h, --help:<br>
    get short help and quit<br>
--2d:<br>
    produce 2D maps<br>
--igc:<br>
    produce 2D maps with IGC maps underneath. Zooms, 2nd level shifts, and
    symbols replacements are not applied.<br>
--igc_private:<br>
    same as --igc but produce a private map (private layers are not removed)<br>
--color:<br>
    recolor the maps using a color model. Available models are (currently):
    igc, bator, black (igc is used automatically in the --igc options)<br>
--3d:<br>
    produce 3D meshes in a subdirectory (default: ``meshes_obj``)<br>
--split:<br>
    split the SVG file into 4 smaller ones, each containing a subset of the
    layers<br>
--join:<br>
    reverse the --split operation: concatenate layers from several files
