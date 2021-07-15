# fdc_catamaps
Process SVG Inkscape maps to produce 2D/3D catacombs maps (Fond-du-crew maps).

Contains a set of python modules / program to produce catacombs maps using SVG source map with codes inside it.

A web site sources is also provided in `catamap_web/`

See more doc on: https://denisri.github.io/fdc_catamaps/

The program allows to produce:

* 2D "readable" maps with symbols changed to larger ones, second level shifted to avoid superimposition of corridors, enlarged zooms, shadowing etc.

* 3D maps to be used in a 3D visualization program, a webGL server, or the CataZoom app.

Requirements
------------

* Having inkscape installed on the system and available in the PATH.
  A recent version of inkscape (1.0 at least) is recommended to avoid units and
  scaling problems.
* Either the Pillow (PIL) python podule (see later) or ImageMagick "convert"
  tool to convert PNG to JPEG. If Pillow is present, then convert will not be
  used. **see notes below for ImgeMagick**

Python modules:

These can be installed using the command:
```
    python -m pip install six numpy scipy Pillow
```
* svg_to_mesh submodule and its requirements (part of this project)
* xml ElementTree
* six
* numpy
* scipy
* Pillow (PIL) optionally for PNG/JPEG image conversion. Otherwise ImageMagick
  "convert" tool will be used (see above)

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

```
usage: catamap [-h] [--2d] [-m DO_2D_MAPS] [--3d] [--color COLOR] [--split]
               [--dpi DPI] [--join] [--output_filename OUTPUT_FILENAME]
               input_file [output_3d_dir]

Catacombs maps using SVG source map with codes inside it. The program allows
to produce: * 2D "readable" maps with symbols changed to larger ones, second
level shifted to avoid superimposition of corridors, enlarged zooms, shadowing
etc. * 3D maps to be used in a 3D visualization program, a webGL server, or
the CataZoom app.

positional arguments:
  input_file            input SVG Inkscape file
  output_3d_dir         output 3D meshes directory (default: meshes_obj)

optional arguments:
  -h, --help            show this help message and exit
  --2d                  Build 2D maps (several maps). the maps list is given
                        via the --maps option. If the latter is not specified,
                        do all.
  -m DO_2D_MAPS, --maps DO_2D_MAPS
                        specify which 2d maps should be built, ex:
                        "public,private,igc". Values are in ("public",
                        "private", "wip", "poster", "igc", "igc_private").
                        Default: all if --2d is used. If this option is
                        specified, --2d is implied (thus is not needed)
  --3d                  Build 3D map meshes in the "meshes_obj/" directory
  --color COLOR         recolor the maps using a color model. Available models
                        are (currently): igc, bator, black (igc is used
                        automatically in the --igc options)
  --split               split the SVG file into 4 smaller ones, each
                        containing a subset of the layers
  --dpi DPI             output JPEG images resolution. May be global (for all
                        outputs): "360", or scoped to a single map: "igc:360".
                        Several --dpi options may specify resolutions for
                        several output maps: "--dpi 200,igc:360,private:280"
  --join                reverse the --split operation: concatenate layers from
                        several files
  --output_filename OUTPUT_FILENAME
                        base filename for output 2D maps. The filename will be
                        suffixed according to maps types (_imprimable,
                        _imprimable_private, etc) (default: same as input
                        file). Be careful that some maps are using files
                        linked in the same input directory, and will not work
                        if the output is in a different directory.
```

Notes
-----

* ImageMagick:

  Warning: If you are using ImageMagick convert:
  https://github.com/ImageMagick/ImageMagick/issues/396
ImageMagick cache (disk limit) size is too small.
Edit /etc/ImageMagick-6/policy.xml and change disk resource limit::

      <policy domain="resource" name="memory" value="12GiB"/>
      <policy domain="resource" name="map" value="20GiiB"/>
      <policy domain="resource" name="width" value="50KP"/>
      <policy domain="resource" name="height" value="50KP"/>
      <policy domain="resource" name="area" value="20GiB"/>
      <policy domain="resource" name="disk" value="80GiB"/>

