#!/usr/bin/env python
# coding: UTF-8

'''
Catacombs maps using SVG source map with codes inside it.

The program allows to produce:

* 2D "readable" maps with symbols changed to larger ones, second level shifted to avoid superimposition of corridors, enlarged zooms, shadowing etc.

* 3D maps to be used in a 3D visualization program, a webGL server, or the CataZoom app.

Requirements
============

* Having inkscape installed on the system and available in the PATH.
  A recent version of inkscape (1.0 at least) is recommended to avoid units and
  scaling problems.
* Either:

  * the Pillow (PIL) python module (see later)
  * or ImageMagick "convert" tool to convert PNG to JPEG. If Pillow is present,
    then convert will not be
    used.

    **Warning:** https://github.com/ImageMagick/ImageMagick/issues/396
    ImageMagick cache (disk limit) size is too small.
    Edit /etc/ImageMagick-6/policy.xml and change disk resource limit::

        <policy domain="resource" name="memory" value="12GiB"/>
        <policy domain="resource" name="map" value="20GiiB"/>
        <policy domain="resource" name="width" value="50KP"/>
        <policy domain="resource" name="height" value="50KP"/>
        <policy domain="resource" name="area" value="20GiB"/>
        <policy domain="resource" name="disk" value="80GiB"/>

Python modules:

These can be installed using the command::

    python -m pip install six numpy scipy Pillow

* :mod:`~catamap.svg_to_mesh` submodule and its requirements (part of this
  project)
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

The maps differences tool (:mod:`~catamap.diff_svg`) also needs:

* yaml (pip module ``pyyaml``)

Usage
=====

* set the ``python`` subdirectory of the project in your ``PYTHONPATH`` environment variable. Under Unix sh/bash shells, this would be::

    export PYTHONPATH="~/fdc_catamaps/python:$PYTHONPATH"

  (it can be set in a ``.bash_profile`` or ``.bashrc`` init file)

* get or make the source SVG file with codes inside, for instance ``plan_14_fdc_2021_04_29.svg``
main
* go to the directory containing it
* run the module ``catamap`` as a program::

    python -m catamap --2d plan_14_fdc_2021_04_29.svg

It should work using either python2 or python3.
The 2D maps options will produce files with suffixes in the current directory:
modified .svg files, .pdf and .jpg files.

The 3D maps option will produce meshes in a subdirectory.

Use the commandline with the '-h' option to get all parameters help.


Inkscape SVG files
==================

SVG files may (should) contain additional XML properties that can be set in the XML editor in the Inkscape software. They allow to specify how objects should be parsed, grouped, represented etc. For now they are mainly used in the 3D part, but the 2D part also uses ``level``, ``label``, and ``private`` information information.

Codes correspond to properties used in the program, and can be set in XML elements in the SVG file.

Bool properties can be written ``true``, ``True``, ``1``, or ``false``, ``False``, ``0``.

Properties are inherited from parent (group/layer) to children. Thus if a layer has the property ``corridor`` set to ``true``, all objects in this layer will be marked as ``corridor``.

In the program, elements are grouped into meshes: a mesh will be the concatenation of all elements of the same kind, to avoid having dozens of thousands of mesh files to load. An object "kind" (a group making a single mesh) is identified by several of its properties, but not all. Namely the identifier is::

    <label>_<level>_<public/private>_<accessible/inaccessible>[_<category>]

Other properties are not discriminative, so in some conditions may not be taken into account. For instance if a layer defines a label, level, public and accessible states, and marks items as corridors, if one element inside adds a property ``block``, it will be part of the same mesh group anyway, and the ``block`` property will be ignored.

Properties list
---------------

**alt_colors:** JSON dict (**2D and 3D maps**)
    color to be used alternatively in maps. This is a string representing a
    JSON format dictionary. Keys are colorsets names, values are a second level
    of dictionary which specifies color properties, a bit like for SVG elements
    style. The
    default colorset for 3D maps is ``map_3d``.
    Ex::

        {"map_3d": "#cccccc4c"}

    see also: :ref:`colorsets`

**arrow:** bool (**3D maps**)
    arrows join a text label to a location on map. They are filar meshes. Most
    of them are just a segment (2 points) but they may contain more points.
    Points orientation is important as the arrow goes from the text (above the
    meshes) down to the pointed item below.
**arrow_base_height_shift:** float (**3D maps**)
    z shift of the base of an arrow element in the upper layer depth. The arrow head shift is specified using height_shift.
**block:** bool (**3D maps**)
    block elements have a ceiling and walls. Meshes are extruded and tesselated
    to be filled.
**border:** bool (**3D maps**)
    not used if I remember...
**category:** str (**3D maps**)
    the category string the element will be associated in the 3D views.
    Categories can be displayed/hidden using buttons or menus in 3D views.
**catflap:** bool (**3D maps**)
    In catflaps, paths are replaced with striped tubes.
**colorset_inheritance:** JSON dict (**2D and 3D maps**)
    used as a property of the ``metadata`` layer only, it specifies colorsets
    which can inherit the colors defined by another, in order to minimally
    specialize it.

    see also: :ref:`colorsets`

**corridor:** bool (**3D maps**)
    corridors have a floor and walls. Meshes are extruded and tesselated to be
    filled.
**date:** str (**2D maps**)
    the date text will be replaced with the date of the map build.
**depth_map:** bool (**3D maps**)
    the layer is a depth map. It should contain a ``level`` property to define
    the level it maps. See :ref:`depth_maps` for details.
**glabel:** str (**2D maps**)
    "group label" used to replace elements with ones from the legends layer.
    The ``glabel`` is associated to one legends element if the legends element
    ``label`` property has the value of the ``glabel`` property of the element
    plus the duffix ``_proto``. Ex, in the legends::

        label: colim_proto

    in the map elements::

        glabel: colim

**height_shift:** float (**3D maps**)
    z shift of the element (esp. for corridor, block, wall elements, but also
    wells and arrows). An element with a height shift will not begin on the
    ground, but above or below as specified.
**hidden:** bool (**2D and 3D maps**)
    removed from 3D maps.
**inaccessible:** bool (**3D maps**)
    inaccessible elements will be separated from others, and set in the
    ``Inaccessible`` display category.
**item_height:** float (**3D maps**)
    height of the element (esp. for corridor, block, wall elements).
    **WARNING:** it is ``item_height``, not ``height`` as height is already an
    official SVG attribute for some elements (rectangles for instance).
**label:** str (**2D and 3D maps**)
    name of the element type
**label_alt_colors:** JSON dict (**2D and 3D maps**)
    Like alt_colors, except that the dict has an upper-level which keys area
    object labels. The dict can be applied hierarchically, thus put in a layer.
    Ex::

        {"repetiteur": {"black": {"bg": "#cccccc4c"}}}

    see also: :ref:`colorsets`

**legend:** bool (**2D maps**)
    set on a layer, indicates that this layer contains the legend symbols and
    can be searched for replacement symbols (wells, etc) which will replace
    those in the map to enlarge them and ease view from a bit further.
**level:** str (**2D and 3D maps**)
    depth level name (sup, inf, surf, tech, metro, esc...). Levels are an
    "open" property, there is no predefined list of levels, apart for 2
    exceptions:

    * items which don't specify a level are set by default to a level named
      ``sup`` (generally superior corridor level).
    * a ``surf`` level represents the ground surface, and is automatically
      built. It is flat, altitude 0 by default, but can be associated to an
      altitude map and geolocalisation information. See :ref:`altitude_maps`
      later.

    Levels are associated to depth maps, so for each level used (except
    ``surf``), a ``depth_map`` layer is supposed to be defined. See
    :ref:`depth_maps`.
**map_transform**: SVG transformation spec (**2D maps**)
    additional transformation applied to elements, used for
    instance to shift lower level parts when they are superimposed under an
    upper level. Without this shift, they would not be seen because they are
    hidden by the upper level. The transform is specified in the same way as
    the standard SVG ``transform`` property.

    This propery can be set to paths, groups, and arrows (which will thus point
    to a shifted location).
**marker:** str (**3D maps**)
    set on a layer to specify that this layer is a **markers layer**. Two types
    of markers are currently recognized: ``sounds`` and ``photos``.

    See :ref:`markers` for more details.

**markers_base_url:** bool (**3D maps**)
    set on a :ref:`marker layer <markers>` to specify that marekrs in this
    layer have URLS which point to the server directory specified here.
    Individual markers will be appended to this base URL. The URL may be
    absolute (``https://photos.google.com/xyzsomething``) or relative to the
    map server (``photos/photo_dir``). If not specified, the default base url
    is the markers type (``photos``, ``sounds``), in relative mode.
**markers_map:** str (**3D maps**)
    Set on a :ref:`marker layer <markers>`: correspondence map file name (CSV
    file) for markers text. See :ref:`markers` for more details.
**non_visibility:** str (**2D maps**)
    list of maps types (json-like), for which this layer is removed. The
    inverse of **visibility** (see below).
**private:** bool (**2D and 3D maps**)
    private elements will only be visible if a code is provided
**radius:** float (**3D maps)
    used in a "marker" layer to specify the max radius between the user click
    and the marker position for it to be triggered. It can be set on the marker
    layer itself, or on any marker item inside.

    See :ref:`markers` for more details.

**replace_children:** bool (**2D maps**)
    should be set only in replacement symbols in the legend layer (wells signs,
    etc) to indicate that children of matching elements should be parsed
    recursively and their children may be replaced also.
**symbol:** bool (**3D maps**)
    not sure it is used, after all...
**text:** bool (**3D maps**)
    text layers.
**title:** bool (**3D maps**)
    The title string(s) will be used and displayed in the web site title.
**upper_level:** str (**3D maps**)
    depth level for the top of elements. Only used for elements joining two levels
    (wells, arrows)
**visibility:** str (**2D and 3D maps**)
    may be either: ``private``: alternative to ``private: true``, or a list of
    maps types (json-like), for which this layer is kept visible. If such a
    list is specified, then maps types not listed here will drop the layer.
    As ``visibility`` has now a broader meaning, it is better to specify
    ``private: true`` for private things, to avoid ambiguities.
**wall:** bool (**3D maps**)
    wall elements have only side walls (no floor or ceiling).
**well:** bool (**3D maps**)
    wells are replaced with custom elements, which type is the element label
    (PE, PS, PSh, échelle, sans, P ossements, ...). Well elements (or groups,
    or layers) shoud specify the level and upper_level.
**well_read_mode:** str (**3D maps**)
    tells if well elements should be read in the XML file as a single "path"
    element (a circle for instance), or a group (a grop containing a circle,
    and additional lines). Thus allowed values are ``path`` or ``group``.

.. _depth_maps:

Depth maps
----------

Depth maps are layers containing depth information, **and nothing else**.

Each depth information specifies the depth of a specifi point in the map. They can be specified in several ways:

* a *text element*: the position of the element (its center if the text is centered) will be used as the position. The text should specify a floating point number which is the depth at this position.
* a group containing a text element and a segment path: the text is a float number specifying the depth, and the segment (2 points, oriented from the text toward the application point) specifies where the depth applied: the end pont of the segment will be assigned the given depth.
* a rectangle: this was originally the way to specify depth, but it proved to be difficult to read and is thus obsolete. Prefer the two above methods. In 2 words, the min of the rectangle is the depth, and the position of the rectangle (its center) is the position. Well, better forget it.


.. _altitude_maps:

Altitude maps
-------------

Altitude maps can be built and used to shift all other depth maps, which are supposed to be relative to the surface ground altitude map (for now at least: we may change this later using an ``upper_level`` property in depth maps which could be any other map).

To work we require more information, because we need actual altitude maps, and a geolocalisation of the inkscape SVG file.

Geolocalisation of the SVG file
+++++++++++++++++++++++++++++++

The SVG file should contain a layer named ``lambert93`` which contains, as its name says it, world coordinates in the **Lambert 93 coordinates system**.

Coordinates can be spacified at any location of the map. At least 3 points are needed to estimate a transformation, but the more points are provided, the more precise the estimation will be. The coordinates transformation between the SVG positions and the Lambert93 coordinates will be estimated as a linear transformation fit to all SVG/Lambert 93 coortinates couples.

A Lambert93 point is specified in this ``lambert93`` layer as a group containing 2 objects:

* a text item with text being the 2 cooridinates separated by a coma, ex::

    652470.89,6858871.84

* a segment line (2 points, oriented) going from the text toward the application point on the map.

Lambert 93 positions can be found using https://www.geoportail.gouv.fr/carte: on the map, select "tools" on the right, and enable "display coordinates". Then select for "reference system" the "Lambert 93" mode.

Altitude maps
+++++++++++++

Altitude maps can be retreived from BDAlti: https://geoservices.ign.fr/documentation/diffusion/telechargement-donnees-libres.html#bd-alti

Then maps have to be converted using tools in :mod:`catamap.altitude.bdalti`.
The ``altitude`` directory should be located in the same directory as the SVG map file.

Example
-------

See the map: :download:`example map <static/example_map.svg>`
The result in 2D is (left: original map, right: result):

.. image:: static/example_map.png
    :height: 400

.. image:: static/example_map_imprimable.jpg
    :height: 400

In 3D: `here <_static/example_3d/index.html>`_

See for instance how wells indications are enlarged in the "printable" 2D map, the inferior level is shifted to allow seing it when it is superimposed with the upper level, while they are still superposed in the 3D map.


.. _colorsets:

Colorsets
---------

Both 2D and 3D maps, while processed, may assign different colorsets to elements, if specified via the ``--color`` option. A colorset is a defined by a name. Each element, group, layer, or labelled element can be assigned a different color for each colorset. Colorsets are defined dynamically in the map SVG source file. XML elements having a ``alt_colors`` property can both define colorsets and assign colors.

A few "hard-coded" colorsets are expected to exist (even it it is not mandatory) and are used by default:

* 3D maps use by default the ``map_3d`` colorset.
* 2D maps using "igc" mode (with ICC maps overlayed) use the ``igc`` colorset.

Colorsets inheritance
+++++++++++++++++++++

Some colorsets may be slight variants to other existing ones. To avoid redefining every element color in the SVG file, it is possible to specify some "colorset inheritances". This is done using the ``colorset_inheritance`` property in the ``metadata`` layer (a hidden layer made for SVG / inkscape). This property is a JSON dictionary, with a ``{'child': 'parent'}`` shape. The meaning is that a child inherits all its parent colors, and then can override some.

Colors specifications
+++++++++++++++++++++

An ``alt_colors`` property applies recursively to all its children. It is a JSON dictionary, whith the followin shape:

* primary keys are colorset names
* primary values are `color specs`

A `color spec` is normally also a dict, with the following shape:

* keys are like in SVG elements style, ``fg`` (foreground), ``bg`` (background), ``stroke-width``
* values are strings, either containing the RGBA color, or a float value for ``stroke-width``.
* colorsets used only in 3D may shunt the second level and specify directly a single RGBA color string as colorspec value.

Ex::

    {"map_3d": "#c0c0c0ff",
     "igc": {"bg": "#ff0000ff"},
     "black": {"fg": "#ffffffff", "bg": "#c0606060ff", "stroke-width": "0.2"}}

A ``label_alt_colors`` property has an additional upper level whick key is the element label, and the primary value is like the ``alt_colors`` dict::

    {"repetiteur": {"black": {"bg": "#c0c0c0ff"}},
     "marches": {"black": {"fg": "#c0c0c0ff"}}}

.. _markers:

Markers
-------

**Markers** are small marker objects pointing to external links, such as photographs, or sounds. When the user clicks on a marker, or sufficiently close to it in a given radius, it triggers a link to an external resource (an web URL).

Markers are recorded in dedicated layers in the SVG file. Such layer must have a ``marker`` property, which value is the type of markers in the layer. Currently two types of markers are handled: ``photos`` (links to photographs URLS) or ``sounds``.

Sounds are handled specificly using a media player inside the 3D map, whereas photographs are just web links, and may actually point to any web resource or page (web page, photo file, video, or anything).

A marker layer can have ``markers_base_url`` or ``radius`` properties, which respectively specify the base URL for all markers, and the max distance to the marker for which a user click will trigger the marker.

The layer contents are similar to depth layers: they are text objects, or groups containing a text object and a line object to make an arrow from the text to the marker exact location. The layer may not have other kind of groups, it is not recursive.

Items in the marker layer are thus text at specified locations. The text is the URL of the resource (sound, photo, ...) and is appended to the base URL above. If no ``markers_base_url`` is specified, the marker value (type) is used as a relative directory as base URL (``sounds/...`` or ``photos/...``).

Each item may get a specific ``radius`` property, which may overload the layer radius. If no radius is specified, a default is used (10., which would correspond to 10 m radisu, depending on the map scale).

If an item text has no file extension, ``.jpg`` will be appended by the server in a photos markers layer. This way the map source, in Inkscape, may display a very short, readable, indication, such as a single number: for instance, ``123`` will be replaced with ``photos/123.jpg``.

On the web server side, photos and sounds directory have to be created and contain the referenced files.

Markers text syntax
+++++++++++++++++++

Markers text may be a filename (which will be prefixed with the contents of the ``markers_base_url`` property, and possibly suffixed with ``.jpg``), or a list of such filenames::

    image1.jpg, video2.mp4, image3.jpg

or::

    image1, video2.mp4, image3

In addition to the "direct URL" mechanism above, it is also possible to specify, for each markers layer, a "correspondance map" file (using the ``markers_map`` property on the layer). This file will be read as a CSV file (with ``tab`` separators). Then texts in markers text in the SGV file will go through this map to get a "final" file name for the marker element. A given marker text can be found several times in the file, and then several files will be associated with the marker element. For instance if you use numbers for markers texts, ``1``, ``2``, ``3`` in the SVG map, a ``markers_map`` can specify final filenames such as::

    20220304_201758.jpg	1
    20220304_201802.jpg	2
    20220304_201804.jpg	1
    20220304_201815.jpg	3
    20220304_202652.jpg	2
    20220304_202810.jpg	1

will assign to marker ``1`` the files: ``20220304_201758.jpg``, ``20220304_201804.jpg``, ``20220304_202810.jpg``, and so on. Each of the file names will undergo the prefix/suffix transformations using ``markers_base_url`` etc.


map_to_meshes module
====================

This module is an extension of the :mod:`~catamap.svg_to_mesh` module and ist main class, :class:`~catamap.svg_to_mesh.SvgToMesh` for more specific purposes. This means the former is dedicated to generically read Inkscape files and convert elements to meshes, while the specialized classes here are dedicated to building catacombs maps.

:class:`~catamap.map_to_meshes.CataSvgToMesh` wiil build 3D maps meshes and objects

:class:`~catamap.map_to_meshes.CataMapTo2DMap` will build "cleaner" 2D maps (with some symbols replaced and enlarged, regions zooms and more, and export PDF and JPG versions.


map_to_meshes module API
------------------------

'''

from __future__ import print_function
from __future__ import absolute_import

#import anatomist.headless as ana
#a = ana.HeadlessAnatomist()

from . import svg_to_mesh
from six.moves import range
from six.moves import zip
from .svg_to_mesh import aims, fake_aims
import numpy as np
from scipy.spatial import Delaunay
import copy
import six
import xml.etree.cElementTree as ET
import datetime
import math
import json
import os
import hashlib
import collections
import sys
import subprocess
import distutils.spawn
import imp
import time  # just for exec time stats
from argparse import ArgumentParser
import textwrap as _textwrap
import argparse
try:
    import PIL.Image
except ImportError:
    PIL = None
# import bdalti module
try:
    from .altitude import bdalti
except ImportError:
    bdalti = None


class xml_help(object):

    '''
'''

    pass


class ItemProperties(object):
    '''
    XML item properties structure, used by
    :class:`~catamap.map_to_meshes.CataSvgToMesh`. They represents properties
    read from the XML file elements.

    Properties match those documented in :class:`~catamap.map_to_meshes.xml_help`, except the ``height`` property which is named ``item_height`` in XML file elements (because ``height`` is already used in SVG).
    '''

    properties = ('name', 'label', 'eid', 'main_group', 'level', 'upper_level',
                  'private', 'inaccessible', 'corridor', 'block', 'wall',
                  'symbol', 'arrow', 'text', 'well', 'catflap', 'hidden',
                  'depth_map', 'height', 'height_shift', 'border',
                  'alt_colors', 'label_alt_colors', 'category', 'layer',
                  'well_read_mode', 'grid_interval', 'marker',
                  'arrow_base_height_shift')

    prop_types = None  # will be initialized when used in get_typed_prop()

    def __init__(self):
        self.reset_properties()

    def reset_properties(self):
        for prop in self.properties:
            setattr(self, prop, None)
        self.private = False
        self.inaccessible = False
        self.corridor = False
        self.block = False
        self.wall = False
        # self.wireframe = False
        self.symbol = False
        self.arrow = False
        self.text = False
        self.well = False
        self.catflap = False
        self.hidden = False
        self.depth_map = False
        self.height = None
        self.height_shift = None
        self.arrow_base_height_shift = None
        self.border = False
        self.marker = None
        self.alt_colors = None
        self.label_alt_colors = None
        self.category = None
        self.layer = False
        self.well_read_mode = None
        self.grid_interval = None

    def __str__(self):
        d = ['{']
        for k in self.properties:
            d.append("'%s': %s, " % (k, repr(getattr(self, k))))
        d.append('}')
        return ''.join(d)

    def copy_from(self, other):
        for prop in self.properties:
            setattr(self, prop, getattr(other, prop))

    @staticmethod
    def get_typed_prop(prop, value):
        if ItemProperties.prop_types is None:
            ItemProperties.prop_types = {
                'private': ItemProperties.is_true,
                'inaccessible': ItemProperties.is_true,
                'corridor': ItemProperties.is_true,
                'block': ItemProperties.is_true,
                'wall': ItemProperties.is_true,
                # 'wireframe': ItemProperties.is_true,
                'symbol': ItemProperties.is_true,
                'arrow': ItemProperties.is_true,
                'text': ItemProperties.is_true,
                'well': ItemProperties.is_true,
                'catflap': ItemProperties.is_true,
                'hidden': ItemProperties.is_true,
                'depth_map': ItemProperties.is_true,
                'height': ItemProperties.float_value,
                'height_shift': ItemProperties.float_value,
                'arrow_base_height_shift': ItemProperties.float_value,
                'border': ItemProperties.float_value,
                'layer': ItemProperties.is_true,
                'grid_interval': ItemProperties.float_value,
            }
        type_f = ItemProperties.prop_types.get(prop, str)
        if type_f is ItemProperties.is_true and value == prop:
            # speclal case which we should handle a better way...
            return True
        return type_f(value)

    @staticmethod
    def is_true(value):
        return value in ('1', 'True', 'true', 'TRUE', 1, True)

    @staticmethod
    def float_value(value):
        if value in (None, 'None'):
            return 0.
        return float(value)

    def fill_properties(self, element, parents=[], set_defaults=True,
                        style=None):
        if parents:
            self.copy_from(parents[-1])
        else:
            self.reset_properties()

        self.layer = False  # this one does not propagate to children

        if element is not None:
            eid, props = self.get_id(element, get_props=True, use_suffix=False)
            if eid and props:
                # properties as layer name suffixes
                for prop, value in props.items():
                    value = ItemProperties.get_typed_prop(prop, value)
                    setattr(self, prop, value)
            if eid:
                self.eid = eid
                if not self.name:
                    self.name = self.eid

            # properties tags
            for prop in ('level', 'upper_level', 'private', 'inaccessible',
                         'category', 'well_read_mode', 'grid_interval',
                         'marker'):
                value = element.get(prop)
                if value is not None:
                    setattr(self, prop,
                            ItemProperties.get_typed_prop(prop, value))

            # alternative to "private: true", using "visibility: private"
            visibility = element.get('visibility')
            if not visibility:
                visibility = []
            elif visibility and visibility.strip().startswith('['):
                visibility = json.loads(visibility)
            else:
                visibility = [visibility]
            if 'private' in visibility:
                self.private = True
            self.visibility = visibility

            non_visibility = element.get('non_visibility')
            if not non_visibility:
                non_visibility = []
            if non_visibility and non_visibility.strip().startswith('['):
                non_visibility = json.loads(non_visibility)
            else:
                non_visibility = [non_visibility]
            self.non_visibility = non_visibility

            for kind in ('corridor', 'block', 'wall', # 'wireframe',
                         'well',
                         'catflap', 'hidden', 'depth_map', 'arrow', 'text'):
                # + border ?
                value = self.is_something(element, kind)
                if value is not None:
                    setattr(self, kind, value)

            # if style is not None and style.get('display') == 'none':
            #     self.hidden = True

            if element.tag == 'text' or element.tag.endswith('text'):
                self.text =  True

            # label suffixes are an old, ambiguous, system. We must disable it
            # in some cases
            use_suffix = True
            if self.depth_map:
                use_suffix = False

            label, props = self.get_label(element, get_props=True,
                                          use_suffix=use_suffix)
            if label and props:
                # properties as layer name suffixes
                for prop, value in props.items():
                    value = ItemProperties.get_typed_prop(prop, value)
                    if value is not None:
                        setattr(self, prop, value)
            if label:
                self.label = label
                self.name = label

            self.height = self.get_height(element)
            self.height_shift = self.get_height_shift(element)
            self.arrow_base_height_shift \
                = self.get_arrow_base_height_shift(element)

            if set_defaults:
                for prop in ('level', 'upper_level', ):
                    if getattr(self, prop) is None:
                        setattr(self, prop,
                                getattr(DefaultItemProperties, prop))

            # build main group (mesh object etc)
            priv_str = 'private' if self.private else 'public'
            access_str = ('inaccessible' if self.inaccessible
                          else 'accessible')
            if self.label is None:
                print('no label for item:', self)
                self.label = 'undefined'
            if self.level is None:
                print('level None in', self)
                self.level = 'undefined'
            tags = [self.label, self.level, priv_str, access_str]
            if self.category:
                tags.append(self.category)
            if self.text:
                tags.append('text')
            self.main_group = '_'.join(tags)

            if element.get(
                    '{http://www.inkscape.org/namespaces/inkscape}'
                    'groupmode') == 'layer':
                self.layer = True

            label_alt_colors = element.get('label_alt_colors')
            if label_alt_colors is not None:
                try:
                    self.label_alt_colors = json.loads(label_alt_colors)
                except:
                    print('error reading JSON in label_alt_colors of', eid,
                          label)
                    print('json code:', label_alt_colors)
                    raise

            alt_colors = element.get('alt_colors')
            if alt_colors is not None:
                try:
                    self.alt_colors = json.loads(alt_colors)
                except:
                    print('error reading JSON in alt_colors of', eid, label)
                    print('json code:', alt_colors)
                    raise

            if self.well and self.well_read_mode is None:
                well_read_mode = DefaultItemProperties.well_read_modes.get(
                    label)
                self.well_read_mode = well_read_mode

            if self.text and self.block:
                self.block = False

    @staticmethod
    def remove_word(label, word):
        ''' remove word suffix to label (which may end with several
        variants, _word_0 etc)
        '''
        if label == word:
            return label
        if label.endswith(' %s' % word) or label.endswith('_%s' % word):
            return label[:-len(word) - 1]
        for pattern in (' %s ', ' %s_', '_%s ', '_%s_'):
            p = pattern % word
            if p in label:
                index = label.find(p)
                sep = p[-1]
                return label.replace(p, sep)
        return label

    @staticmethod
    def remove_label_suffix(label, get_props, use_suffix=True):
        props = {}
        if label is None:
            if get_props:
                return None, None
            return
        if use_suffix:
            for suffix, prop in DefaultItemProperties.layer_suffixes.items():
                new_label = ItemProperties.remove_word(label, suffix)
                if new_label != label and get_props or new_label == suffix:
                    props[prop] = DefaultItemProperties.layers_aliases.get(
                        suffix, suffix)
                label = new_label
        if get_props:
            return label, props
        return label

    @staticmethod
    def get_label(element, get_props=False, use_suffix=True):
        label = element.get('label')
        if label is None:
            label = element.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
        return ItemProperties.remove_label_suffix(label, get_props, use_suffix)

    @staticmethod
    def get_id(element, get_props=False, use_suffix=True):
        label = element.get('id')
        if label is None:
            label = element.get(
                '{http://www.inkscape.org/namespaces/inkscape}id')
        return ItemProperties.remove_label_suffix(label, get_props, use_suffix)

    @staticmethod
    def is_corridor(element):
        return ItemProperties.is_listed_element_type(
            element, 'corridor', DefaultItemProperties.corridor_labels)

    @staticmethod
    def is_block(element):
        return ItemProperties.is_listed_element_type(
            element, 'block', DefaultItemProperties.block_labels)

    @staticmethod
    def is_wall(element):
        return ItemProperties.is_listed_element_type(
            element, 'wall', DefaultItemProperties.wall_labels)

    @staticmethod
    def is_hidden(element):
        return ItemProperties.is_listed_element_type(
            element, 'hidden', DefaultItemProperties.hidden_labels)

    @staticmethod
    def is_well(element):
        return ItemProperties.is_listed_element_type(
            element, 'well', DefaultItemProperties.wells_labels)

    @staticmethod
    def is_catflap(element):
        return ItemProperties.is_listed_element_type(
            element, 'catflap', DefaultItemProperties.catflap_labels)

    @staticmethod
    def is_depth_map(element):
        return ItemProperties.is_listed_element_type(
            element, 'depth_map', DefaultItemProperties.depth_map_labels)

    @staticmethod
    def is_border(element):
        return ItemProperties.is_listed_element_type(
            element, 'border', DefaultItemProperties.border_labels)

    @staticmethod
    def is_something(element, kind):
        return ItemProperties.is_listed_element_type(
            element, kind,
            getattr(DefaultItemProperties, '%s_labels' % kind, ()))

    @staticmethod
    def is_listed_element_type(element, tag, layers_list):
        value = element.get(tag)
        if value is not None:
            return ItemProperties.is_true(value)
        label = ItemProperties.get_label(element)
        if label in layers_list:
            return True
        return None  # we don't know

    def get_height(self, element):
        height = element.get('item_height')
        if height is not None:
            return float(height)

        if self.height is not None:
            return self.height

        for etype, h in DefaultItemProperties.types_heights.items():
            is_type = getattr(self, etype, None)
            if is_type:
                height = h
        h = DefaultItemProperties.heights.get(self.name)
        if h is not None:
            height = h

        return height

    def get_height_shift(self, element):
        height_shift = element.get('height_shift')
        if height_shift is not None:
            return float(height_shift)

        if self.height_shift is not None:
            return self.height_shift

        for etype, shift in DefaultItemProperties.types_height_shifts.items():
            is_type = getattr(self, etype, None)
            if is_type:
                height_shift = shift
        shift = DefaultItemProperties.height_shifts.get(self.name)
        if shift is not None:
            height_shift = shift

        return height_shift

    def get_arrow_base_height_shift(self, element):
        height_shift = element.get('arrow_base_height_shift')
        if height_shift is not None:
            return float(height_shift)

        if self.arrow_base_height_shift is not None:
            return self.arrow_base_height_shift

        return height_shift


class DefaultItemProperties(object):
    ''' Defaults and constant values.

    This is mainly a remaining of the v1 of the software, where fewer things
    were indicated in the SVG file, and the program was written originally for
    a single map (GRS, Paris 14e) with hard-coded labels.
    '''

    ground_level = 'surf'
    level = 'sup'
    upper_level = ground_level

    # layers containing these words are assigned corresponding properties
    # automatically

    layer_suffixes = {
        'inf': 'level',
        'tech': 'level',
        'gtech': 'level',
        'GTech': 'level',
        'surf': 'level',
        'metro': 'level',
        'seine': 'level',
        'private': 'private',
        'inaccessibles': 'inaccessible',
        'inaccessible': 'inaccessible',
        'anciennes': 'inaccessible',
    }
    layers_aliases = {
        'GTech': 'tech',
        'gtech': 'tech',
        'inaccessibles': 'inaccessible',
        'anciennes': 'inaccessible',
    }

    # levels list
    levels = [
        'sup',
        'inf',
        'esc',
        'tech',
        'surf',
        'pe',  # ?
        'metro',
    ]

    # labels lists assigned with specific properties

    corridor_labels = {
        'galeries',
        'galeries big sud',
        'piliers a bras',
        'inaccessible',
        'galeries agrandissements',
        'oss off',
        'anciennes galeries big',
        'aqueduc',
        'remblai epais',
        'remblai leger',
        'ebauches',
        'metro',
        'esc',
        'escaliers',
        'escaliers anciennes galeries big',
        'galeries techniques',
        'galeries techniques despe',
    }

    block_labels = {
        'calcaire 2010', 'calcaire ciel ouvert',
        'calcaire masse2', 'calcaire masse', 'calcaire med',
        'calcaire sup', 'calcaire vdg',
        'piliers a bras',
        'piliers',
        'maconneries',
        u'maçonneries',
        u'maçonneries anciennes galeries big',
        'hagues',
        'hagues effondrees',
        'cuves',
        'mur',
        'mur_ouvert',
        'bassin',
        'bassin_recouvert',
        'rose',
        'repetiteur',
        'eau',
        'grille',
        'porte',
        'porte_ouverte',
        'passage', 'grille-porte',
    }

    wall_labels = {
        'grilles',
    }

    street_labels = {'plaques rues', }

    symbol_labels = {
        'symboles',
        'marches',
        'stair_symbol',
    }

    depth_map_labels = {
        'profondeurs esc',
        'profondeurs galeries',
        'profondeurs',
    }

    depth_map_names = (
        'profondeurs esc_esc_public_accessible',
        'profondeurs galeries_inf_public_accessible',
        'profondeurs galeries_sup_public_accessible',
        'profondeurs_metro_public_accessible',
        # 'profondeurs_seine_public_accessible',
        'profondeurs_tech_public_accessible',
        # 'profondeurs surf',
        # 'profondeurs pe',
    )

    wells_labels = {
        u'échelle vers',
        u'\xe9chelle vers', 'PSh', 'PSh vers',
        'PE', 'PE anciennes galeries big',
        'PS', 'PS anciennes galeries big',
        'PSh', 'PSh anciennes galeries big',
        'P ossements',
        'P ossements anciennes galeries big',
        'echelle', u'échelle', u'échelle anciennes galeries big',
        u'\xe9chelle anciennes galeries big'
        u'\xe9chelle'
        'sans', 'PS sans',
        'PSh sans',
        'PS_sq',
    }

    catflap_labels = {
        'chatieres v3',
        'chatieres private',
        'bas',
        u'injecté',
    }

    hidden_labels = {
        'indications_big_2010', 'a_verifier', 'bord', 'bord_sud',
        u'légende_alt', u'découpage', 'raccords plan 2D',
        'raccords 2D',
        'masque vdg', u'masque cimetière', 'masque plage',
        'agrandissement vdg', u'agrandissement cimetière',
        'agrandissement plage', 'agrandissements fond',
        'couleur_fond', 'couleur_fond sud',
        'planches', 'planches fond', 'calcaire sup',
        'calcaire limites', 'calcaire masse', 'calcaire masse2',
        'lambert93',
        #'légende',
    }
    hidden_labels.update(depth_map_names)

    types_height_shifts = {
        'corridor': 0.,
        'steet_sign': 1.5,
        'symbol': 2.5,
    }

    height_shifts = {
        'aqueduc': 10.,
        'fontis': 2.5,
        'lys': 5.,
        'grande_plaque': 5.,
        'chatieres v3': 0.5,
        'chatieres private': 0.5,
        'chatieres v3_inf': 0.5,
        'chatieres private_inf': 0.5,
        u'injecté': 0.5,
        'bas': 0.5,
        'ossuaire': 5.,
        'stair_symbol': 5.,
        'etiage': 2.5,
        'etiage_water_tri': 2.5,
        'etiage_wall_tri': 2.5,
        'etiage_line': 2.5,
        'rose': 2.5,
        'remblai leger': 0.8,
        'remblai epais': 1.5,
        'remblai leger_inf': 0.8,
        'remblai epais_inf': 1.5,
        'remblai leger inaccessibles': 0.8,
        'remblai epais inaccessibles': 1.5,
        'remblai leger inaccessibles_inf': 0.8,
        'remblai epais inaccessibles_inf': 1.5,
        'calcaire 2010': 0.,  # this one as walls
        'calcaire vdg': 0.,  # this one as walls
        'PE': 0.,
        'PE anciennes galeries big': -9.,
    }

    types_heights = {
        'corridor': 2.,
        'stair': 1.,
        'block': 1.,
        'symbol': 0.3,
    }

    heights = {
        'esc': 1.,
        'cuves': 1.5,
        'plaques rues': 0.5,
        u'plaques rues volées': 0.5,
        'repetiteur': 1.,
        'bassin': 0.3,
        'bassin_recouvert': 0.3,
        'eau': 0.2,
        'rose': 0.2,
        'remblai leger': 1.2,
        'remblai epais': 0.5,
        'remblai leger_inf': 1.2,
        'remblai epais_inf': 0.5,
        'hagues effondrees': 1.2,
        'sans': 1.5,
        'PS sans': 1.5,
        'echelle': 1.5,
        u'échelle': 1.5,
        u'échelle anciennes galeries big': 1.5,
        'PSh sans': 1.5,
        'PE': 10.5,
        'PE anciennes galeries big': -10.,
        'mur': 2.,
    }

    well_read_modes = {
        'PS': 'path',
        'PS galeries big': 'path',
        'PE': 'path',
        'PE galeries big': 'path',
        'P ossements': 'path',
        'P ossements galeries big': 'path',
        'PSh': 'group',
        'PSh galeries big': 'group',
        'PSh vers': 'group',
        'colim': 'group',
        'échelle': 'group',
        'échelle vers': 'group',
        'échelle galeries big': 'group',
        'PSh sans': 'group',
        'sans': 'path',
    }



class CataSvgToMesh(svg_to_mesh.SvgToMesh):
    '''
    Process XML tree to build 3D meshes
    '''

    proto_scale = np.array([[0.5, 0,   0],
                            [0,   0.5, 0],
                            [0,   0,   1]])

    def __init__(self, concat_mesh='list_bygroup', skull_mesh=None,
                 headless=True):
        super(CataSvgToMesh, self).__init__(concat_mesh)
        self.props_stack = []
        self.depth_maps = []
        self.depth_meshes_def = {}
        self.nrenders = 0
        self.z_scale = 0.5
        self.skull_mesh = skull_mesh
        self.water_scale_model = None
        self.stair_symbol_mesh = None
        self.fontis_mesh = None
        self.lily_mesh = None
        self.large_sign_mesh = None
        self.sounds_marker_model = None
        self.photos_marker_model = None
        self.level = ''
        self.sounds = []
        self.sounds_private = []
        self.photos = []
        self.photos_private = []
        self.group_properties = {}
        self.colorset = 'map_3d'  # alt colors to translate to
        self.colorset_inheritance = {}

        if headless:
            try:
                from anatomist import headless as ana
                a = ana.HeadlessAnatomist()
            except:
                headless = False
        if not headless:
            try:
                from anatomist.direct import api as ana
                a = ana.Anatomist()
            except:
                raise RuntimeError('anatomist is not available. It is needed '
                                   'for CataSvgToMesh to work.')

    def filter_element(self, xml_element, style=None):

        clean_return = []
        is_group = False
        if len(xml_element) != 0:
            is_group = True
            clean_return.append(self.exit_group)

            if len(self.props_stack) == 1:
                print(
                    'parse layer', xml_element.get('id'),
                    xml_element.get(
                        '{http://www.inkscape.org/namespaces/inkscape}label'))
                if xml_element.tag.endswith('}metadata'):
                    z_scale = xml_element.get('z_scale')
                    if z_scale:
                        z_scale = float(z_scale)
                        print(z_scale)
                        self.z_scale = z_scale
                    colorset_inheritance = xml_element.get(
                        'colorset_inheritance')
                    if colorset_inheritance:
                        colorset_inheritance = json.loads(colorset_inheritance)
                        self.colorset_inheritance = colorset_inheritance
                        print('COLORSET INHERITANCE:', colorset_inheritance)

        item_props = ItemProperties()
        item_props.fill_properties(xml_element, self.props_stack, style=style)

        if len(self.props_stack) == 1:
            self.explicitly_show.append(item_props.label)


        if is_group:
            # maintain the stack of parent properties to allow inheritance
            self.props_stack.append(item_props)

        if len(self.depth_maps) != 0:
            # while reading depth indications layer, process things differently
            if xml_element.tag.endswith('g'):
                return (self.read_depth_group,
                        [self.clear_depth_group] + clean_return, False)
            elif xml_element.tag.endswith('path'):
                return (self.read_depth_arrow, clean_return, False)
            elif xml_element.tag.endswith('text'):
                return (self.read_depth_text, clean_return, True)
            elif xml_element.tag.endswith('rect'):
                return (self.read_depth_rect, clean_return, True)
            else:
                print('unknown depth child:', xml_element)
                return (self.noop, clean_return, True)

        self.item_props = item_props
        # keep this properties for the whole group (hope there are no
        # inconistencies)
        if item_props.main_group:
            self.group_properties[item_props.main_group] = item_props
            # print(item_props.main_group)

        hidden = self.item_props.hidden
        self.level = self.item_props.level
        self.main_group = self.item_props.main_group

        if xml_element.get('title') in ('true', 'True', '1', 'TRUE'):
            title = [x.text for x in xml_element]
            self.title = getattr(self, 'title', []) + title
            print('TITLE:', title)
            return (self.noop, clean_return, True)

        label = item_props.label

        if label is not None:
            # depths are taken into account even when hidden (because they
            # are normally hidden in the svg file)
            if item_props.depth_map:
                return (self.start_depth_rect,
                        [self.clean_depth] + clean_return, False)
            if item_props.marker:
                print('MARKER:', item_props.marker)
                sname = item_props.marker
                if item_props.private:
                    sname += '_private'
                model = getattr(self, '%s_marker_model' % item_props.marker,
                                None)
                if model is None:
                    model = self.photo_marker_model
                self.read_markers(xml_element, model, sname)
                return (self.noop, clean_return, True)
            if label == 'lambert93':
                print('LAMBERT93')
                self.read_lambert93(xml_element)
                return (self.noop, clean_return, True)

        if hidden:
            # hidden layers are not rendered
            return (self.noop, clean_return, True)

        if item_props.well:
            if item_props.layer:
                return (None, clean_return, False)
            return (self.read_well, clean_return, False)

        if label is not None:
            if label == 'etiage':
                return (self.read_water_scale, clean_return, True)
            elif label in ('fontis', 'fontis_inf', 'fontis private',
                            'fontis private_inf'):
                return (self.read_fontis, clean_return, True)
            elif label in ('stair_symbol', ):
                return (self.read_stair_symbol, clean_return, True)
            elif label == 'arche':
                return (self.read_arch, clean_return, True)
            elif label.startswith('lys'):
                return (self.read_lily, clean_return, True)
            elif label.startswith('grande_plaque'):
                return (self.read_large_sign, clean_return, True)
            elif label == 'ossuaire':
                return (self.read_bones, clean_return, True)

        return (None, clean_return, False)


    def noop(self, xml_path, trans, style=None):
        return None


    def exit_group(self):
        # print('leave group',
        #       self.props_stack[-1].main_group)
        # print('with properties:', self.item_props)
        self.props_stack.pop(-1)


    def read_path(self, xml_path, trans, style=None):
        if self.main_group is None:
            print('path with no group:', xml_path, list(xml_path.items()))
        mesh = super(CataSvgToMesh, self).read_path(xml_path, trans, style)
        props = self.group_properties.get(self.main_group)
        if props and props.arrow:
            # print('arrow')
            vert = mesh.vertex()
            nv = len(vert)
            for i in six.moves.xrange(nv):
                vert[i][2] = i / (nv - 1)
            ## create mesh if it doesn't exist, and assign it arrow indices
            #gmesh = self.mesh_dict.setdefault(self.main_group,
                                              #aims.AimsTimeSurface(2))
            #if not hasattr(gmesh, 'arrow_indices'):
                #gmesh.arrow_indices = []
            ## keep track of each beginning of arrow object in a concatenated
            ## mesh in order to postprocess arrow locations later
            #gmesh.arrow_indices.append(len(gmesh.vertex()))
        return mesh


    def read_paths(self, xml):
        #print('### read_paths')
        if self.skull_mesh is None:
            self.skull_mesh = self.make_skull_model(xml)
        if self.water_scale_model is None:
            self.water_scale_model \
                = self.make_water_scale_model((0., 0., 0.), 1.)
        if self.fontis_mesh is None:
            self.fontis_mesh = self.make_fontis_model(xml)
        if self.stair_symbol_mesh is None:
            self.stair_symbol_mesh = self.make_stair_symbol_model()
        if self.lily_mesh is None:
            self.lily_mesh = self.make_lily_model(xml)
        if self.large_sign_mesh is None:
            self.large_sign_mesh = self.make_large_sign_model(xml)
        if self.sounds_marker_model is None:
            self.sounds_marker_model = self.make_sounds_marker_model()
        if self.photos_marker_model is None:
            self.photos_marker_model = self.make_photos_marker_model()
        res = super(CataSvgToMesh, self).read_paths(xml)

        #print('======= read_path done =======')
        #print('groups properties:', len(self.group_properties))
        #for k, v in self.group_properties.items():
            #print(k, ':', v)

        return res


    def text_description(self, xml_item, trans=None, style=None, text=''):
        # add level information in text objects
        desc = super(CataSvgToMesh, self).text_description(
            xml_item, trans=trans, style=style, text=text)
        if self.level:
            props = desc.get('properties', {})
            props['level'] = self.level
            desc['properties'] = props
        return desc


    def read_well(self, well_xml, trans, style=None):
        props = self.item_props
        #print('read_well', props)
        label = props.label
        if props.well_read_mode == 'group':
            return self.read_well_group(well_xml, trans, style=style)

        if not well_xml.tag.endswith('}path') and not well_xml.tag == 'path':
            return

        #print('read_well path')
        mesh = self.read_path(well_xml, trans, style)
        bmin = list(mesh.vertex()[0])
        bmax = list(bmin)
        for v in mesh.vertex():
            if v[0] < bmin[0]:
                bmin[0] = v[0]
            if v[0] > bmax[0]:
                bmax[0] = v[0]
            if v[1] < bmin[1]:
                bmin[1] = v[1]
            if v[1] > bmax[1]:
                bmax[1] = v[1]
        center = ((bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2)
        radius = (bmax[0] - bmin[0]) / 2
        z = bmin[2] * self.z_scale
        height = 20. * self.z_scale
        wells_spec = self.mesh_dict.setdefault(props.main_group, [])
        wells_spec.append((center, radius, z, height))
        #print('well_type:', well_type, len(wells_spec))

    def read_well_group(self, stair_xml, trans, style=None):
        #print('well with group', props)
        props = self.group_properties[self.main_group]
        props.well = True
        props.corridor = False
        props.block = False
        props.wall = False
        # we are looking for a group with a path child
        if len(stair_xml[:]) == 0:
            return

        #trans = self.get_transform(stair_xml, trans)

        child = stair_xml[0]
        if child is None:
            return

        if child.tag.endswith('}path') or child.tag == 'path':
            trans = self.get_transform(child, trans)

            mesh = self.read_path(child, trans, style)
            bmin = list(mesh.vertex()[0])
            bmax = list(bmin)
            for v in mesh.vertex():
                if v[0] < bmin[0]:
                    bmin[0] = v[0]
                if v[0] > bmax[0]:
                    bmax[0] = v[0]
                if v[1] < bmin[1]:
                    bmin[1] = v[1]
                if v[1] > bmax[1]:
                    bmax[1] = v[1]
            center = ((bmin[0] + bmax[0]) / 2, (bmin[1] + bmax[1]) / 2)
            radius = (bmax[0] - bmin[0]) / 2
            z = bmin[2] * self.z_scale
            height = 20. * self.z_scale
            wells_spec = self.mesh_dict.setdefault(self.main_group, [])
            wells_spec.append((center, radius, z, height))


    def read_bones(self, bones_xml, trans, style=None):
        bbox = self.boundingbox(bones_xml[0], trans)
        mesh = self.mesh_dict.setdefault(self.main_group,
                                         aims.AimsTimeSurface(3))
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  0.]
        tr = aims.AffineTransformation3d()
        tr.setTranslation(center)
        skull_mesh = aims.AimsTimeSurface(self.skull_mesh)
        aims.SurfaceManip.meshTransform(skull_mesh, tr)
        aims.SurfaceManip.meshMerge(mesh, skull_mesh)
        if 'material' not in mesh.header():
            mesh.header().update(skull_mesh.header())
            if 'material' in mesh.header():
                mat = mesh.header()['material']
            else:
                mat = {}
            mat['face_culling'] = 0
            mesh.header()['material'] = mat


    def read_fontis(self, fontis_xml, trans, style=None):
        bbox = self.boundingbox(fontis_xml[0], trans)
        group = self.main_group
        mesh = self.mesh_dict.setdefault(self.main_group,
                                         aims.AimsTimeSurface(3))
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  0.]
        tr = aims.AffineTransformation3d()
        tr.setTranslation(center)
        fontis_mesh = aims.AimsTimeSurface(self.fontis_mesh)
        aims.SurfaceManip.meshTransform(fontis_mesh, tr)
        aims.SurfaceManip.meshMerge(mesh, fontis_mesh)
        if 'material' not in mesh.header():
            mesh.header().update(fontis_mesh.header())
            if 'material' in mesh.header():
                mat = mesh.header()['material']
            else:
                mat = {}
            mat['face_culling'] = 0
            mesh.header()['material'] = mat

    def read_lily(self, lily_xml, trans, style=None):
        bbox = self.boundingbox(lily_xml[0], trans)
        group = self.main_group
        mesh = self.mesh_dict.setdefault(self.main_group,
                                         aims.AimsTimeSurface(3))
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  0.]
        tr = aims.AffineTransformation3d()
        tr.setTranslation(center)
        lily_mesh = aims.AimsTimeSurface(self.lily_mesh)
        aims.SurfaceManip.meshTransform(lily_mesh, tr)
        aims.SurfaceManip.meshMerge(mesh, lily_mesh)
        if 'material' not in mesh.header():
            mesh.header().update(lily_mesh.header())
            if 'material' in mesh.header():
                mat = mesh.header()['material']
            else:
                mat = {}
            mat['face_culling'] = 0
            mesh.header()['material'] = mat


    def read_large_sign(self, lily_xml, trans, style=None):
        bbox = self.boundingbox(lily_xml[0], trans)
        group = self.main_group
        mesh = self.mesh_dict.setdefault(self.main_group,
                                         aims.AimsTimeSurface(3))
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  0.]
        tr = aims.AffineTransformation3d()
        tr.setTranslation(center)
        try:
            lily_mesh = aims.AimsTimeSurface(self.large_sign_mesh)
        except:
            print('Mesh error:', type(self.large_sign_mesh))
            return
            #raise
        aims.SurfaceManip.meshTransform(lily_mesh, tr)
        aims.SurfaceManip.meshMerge(mesh, lily_mesh)
        if 'material' not in mesh.header():
            mesh.header().update(lily_mesh.header())
            if 'material' in mesh.header():
                mat = mesh.header()['material']
            else:
                mat = {}
            mat['face_culling'] = 0
            mesh.header()['material'] = mat


    def read_arch(self, arch_xml, trans, style=None):
        ## don't apply transform, we will do it later on the mesh
        props = self.group_properties[self.main_group]
        props.symbol = True
        bbox = None
        for child in arch_xml:
            bboxc = self.boundingbox(child, trans)
            if bbox is None:
                bbox = bboxc
            else:
                bbox[0] = [min(bbox[0][i], bboxc[0][i]) for i in range(2)]
                bbox[1] = [max(bbox[1][i], bboxc[1][i]) for i in range(2)]
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  0.]
        radius = max(np.array(bbox[1]) - bbox[0]) / 2
        arch_spec = self.mesh_dict.setdefault(self.main_group, [])
        arch_spec.append((center, (radius, trans), 0., 3.))


    def read_water_scale(self, ws_xml, trans, style=None):
        props = self.group_properties[self.main_group]
        props.symbol = True
        bbox = self.boundingbox(ws_xml[0], trans)
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  4.]
        tr = aims.AffineTransformation3d()
        tr.setTranslation(center)
        for mesh_id, ws_model in six.iteritems(self.water_scale_model):
            ws_mesh = aims.AimsTimeSurface(ws_model)
            aims.SurfaceManip.meshTransform(ws_mesh, tr)
            mesh = self.mesh_dict.setdefault(mesh_id, type(ws_mesh)())
            if len(mesh.header()) == 0:
                mesh.header().update(ws_model.header())
                self.group_properties[mesh_id] = props
            aims.SurfaceManip.meshMerge(mesh, ws_mesh)


    def read_stair_symbol(self, st_xml, trans, style=None):
        bbox = self.boundingbox(st_xml[0], trans)
        mesh = self.mesh_dict.setdefault(self.main_group,
                                         aims.AimsTimeSurface(3))
        center = [(bbox[0][0] + bbox[1][0]) / 2,
                  (bbox[0][1] + bbox[1][1]) / 2,
                  0.]
        tr = aims.AffineTransformation3d()
        tr.setTranslation(center)
        stair_mesh = aims.AimsTimeSurface(self.stair_symbol_mesh)
        aims.SurfaceManip.meshTransform(stair_mesh, tr)
        aims.SurfaceManip.meshMerge(mesh, stair_mesh)
        if 'material' not in mesh.header():
            mesh.header().update(stair_mesh.header())
            if 'material' in mesh.header():
                mat = mesh.header()['material']
            else:
                mat = {}
            mat['face_culling'] = 0
            mesh.header()['material'] = mat


    def make_psh_sq_well(self, center, radius, z, height, props, faces=8):
        # square well
        return self.make_psh_well(center, radius, z, height, props, faces=4,
                                  smooth=False, rotate=math.pi / 4)


    def make_psh_well(self, center, radius, z, height, props, faces=8,
                      smooth=True, rotate=0.):
        p1 = aims.Point3df(center[0], center[1], z)
        p2 = aims.Point3df(center[0], center[1], z + height)
        r0 = radius * 0.7
        well = aims.SurfaceGenerator.cylinder({
            'point1': p1, 'point2': p2, 'radius': r0, 'facets': faces,
            'smooth_tube': smooth, 'closed': False})
        if rotate != 0.:
            tr = aims.AffineTransformation3d()
            tr.setTranslation(p1)
            rot = aims.Quaternion()
            rot.fromAxis((0, 0, 1), rotate)
            mat = tr * aims.AffineTransformation3d(rot) * tr.inverse()
            aims.SurfaceManip.meshTransform(well, mat)
        vert = well.vertex()
        poly = well.polygon()
        norm = well.normal()
        a = np.pi / 6.
        hl = radius - r0
        nv0 = len(vert)
        nv = nv0
        stair_step = 0.3 * self.z_scale
        phb0 = p1 + r0 * aims.Point3df(-np.sin(a), np.cos(a), 0.)
        phb1 = p1 + r0 * aims.Point3df(np.sin(a), np.cos(a), 0.)
        phb2 = p1 + r0 * aims.Point3df(np.cos(a), np.sin(a), 0.)
        phb3 = p1 + r0 * aims.Point3df(np.cos(a), -np.sin(a), 0.)
        phb5 = p1 + r0 * aims.Point3df(-np.sin(a), -np.cos(a), 0.)
        phb4 = p1 + r0 * aims.Point3df(np.sin(a), -np.cos(a), 0.)
        phb7 = p1 + r0 * aims.Point3df(-np.cos(a), np.sin(a), 0.)
        phb6 = p1 + r0 * aims.Point3df(-np.cos(a), -np.sin(a), 0.)

        for zbari in range(1, int(height / stair_step)):
            zbar = z + zbari * stair_step
            ph0 = aims.Point3df(phb0[0], phb0[1], zbar)
            ph1 = aims.Point3df(phb1[0], phb1[1], zbar)
            ph2 = aims.Point3df(phb2[0], phb2[1], zbar)
            ph3 = aims.Point3df(phb3[0], phb3[1], zbar)
            ph4 = aims.Point3df(phb4[0], phb4[1], zbar)
            ph5 = aims.Point3df(phb5[0], phb5[1], zbar)
            ph6 = aims.Point3df(phb6[0], phb6[1], zbar)
            ph7 = aims.Point3df(phb7[0], phb7[1], zbar)

            vert += [ph0, ph1, ph0 + (0., hl, 0.), ph1 + (0., hl, 0.),
                     ph2, ph3, ph2 + (hl, 0., 0.), ph3 + (hl, 0., 0.),
                     ph4, ph5, ph4 + (0., -hl, 0.), ph5 + (0., -hl, 0.),
                     ph6, ph7, ph6 + (-hl, 0., 0.), ph7 + (-hl, 0., 0.)]
            poly += [(nv, nv + 1, nv + 3), (nv, nv + 3, nv + 2),
                     (nv + 4, nv + 5, nv + 7), (nv + 4, nv + 7, nv + 6),
                     (nv + 8, nv + 9, nv + 11), (nv + 8, nv + 11, nv + 10),
                     (nv + 12, nv + 13, nv + 15), (nv + 12, nv + 15, nv + 14)]
            nv += 16
        norm += [(0., 0., 1.)] * (len(vert) - nv0)
        color = self.get_alt_color(props)
        if not color:
            color = [0.5, 0.7, .6, 1.]
        well.header()['material'] = {'diffuse': color,
                                     'face_culling': 0}
        return well


    def make_ladder(self, center, radius, z, height, props):
        p1 = aims.Point3df(center[0], center[1], z)
        p2 = aims.Point3df(center[0], center[1], z + height)
        pole1 = p1 + aims.Point3df(radius, 0., 0.)
        pole2 = p1 - aims.Point3df(radius, 0., 0.)
        r0 = 0.05
        r1 = 0.025
        ladder = aims.SurfaceGenerator.cylinder({
            'point1': pole1,
            'point2': p2 + aims.Point3df(radius, 0., 0.), 'radius': r0,
            'facets': 4, 'smooth': True, 'closed': False})
        ladder2 = aims.SurfaceGenerator.cylinder({
            'point1': pole2,
            'point2': p2 - aims.Point3df(radius, 0., 0.), 'radius': r0,
            'facets': 4, 'smooth': True, 'closed': False})
        aims.SurfaceManip.meshMerge(ladder, ladder2)
        stair_step = 0.3 * self.z_scale
        for zbari in range(1, int(height / stair_step)):
            zbar = z + zbari * stair_step
            b1 = aims.Point3df(pole1[0], pole1[1], zbar)
            b2 = aims.Point3df(pole2[0], pole2[1], zbar)
            bar = aims.SurfaceGenerator.cylinder({
                'point1': b1, 'point2': b2, 'radius': r1, 'facets': 4,
                'smooth': True, 'closed': False})
            aims.SurfaceManip.meshMerge(ladder, bar)
        color = self.get_alt_color(props)
        if not color:
            color = [1., 0., .6, 1.]
        ladder.header()['material'] = {'diffuse': color}
        return ladder


    def make_spiral_stair(self, center, radius, z, height, props=None):
        p1 = aims.Point3df(center[0], center[1], z)
        p2 = aims.Point3df(center[0], center[1], z + height)
        r0 = radius * 0.25
        well = aims.SurfaceGenerator.cylinder({
            'point1': p1, 'point2': p2, 'radius': r0, 'facets': 8,
            'smooth': True, 'closed': False})
        vert = well.vertex()
        poly = well.polygon()
        norm = well.normal()
        a = np.pi / 6.
        nv0 = len(vert)
        nv = nv0
        stair_step = 0.2 * self.z_scale
        angle = 0.
        for zbari in range(1, int(height / stair_step)):
            zbar = z + zbari * stair_step
            ph1 = aims.Point3df(p1)
            ph1[2] = zbar
            ph0 = ph1 - (0., 0., stair_step)
            ph2 = ph0 + radius * aims.Point3df(np.cos(angle), np.sin(angle),
                                               0.)
            ph3 = ph2 + aims.Point3df(0., 0., stair_step)
            angle += a
            ph4 = ph1 + radius * aims.Point3df(np.cos(angle), np.sin(angle),
                                               0.)
            vert += [ph0, ph1, ph2, ph3, ph1, ph3, ph4]
            poly += [(nv, nv + 2, nv + 1), (nv + 1, nv + 2, nv + 3),
                     (nv + 4, nv + 5, nv + 6)]
            nv += 7
        well.updateNormals()
        color = self.get_alt_color(props)
        if not color:
            color = [1., .6, 0., 1.]
        well.header()['material'] = {'diffuse': color,
                                     'face_culling': 0}
        return well


    def make_ps_sq_well(self, center, radius, z, height, well_type, props):
        return self.make_ps_well(center, radius, z, height, well_type, props,
                                 faces=4, smooth=False, rotate=math.pi / 4)

    def make_ps_well(self, center, radius, z, height, well_type, props,
                     faces=8, smooth=True, rotate=0.):
        '''PS or PE (blue), P ossements (yellow)
        '''
        p1 = aims.Point3df(center[0], center[1], z)
        p2 = aims.Point3df(center[0], center[1], z + height)
        well = aims.SurfaceGenerator.cylinder({
            'point1': p1, 'point2': p2, 'radius': radius, 'facets': faces,
            'smooth_tube': smooth, 'closed': False})
        if rotate != 0.:
            tr = aims.AffineTransformation3d()
            tr.setTranslation(p1)
            rot = aims.Quaternion()
            rot.fromAxis((0, 0, 1), rotate)
            mat = tr * aims.AffineTransformation3d(rot) * tr.inverse()
            aims.SurfaceManip.meshTransform(well, mat)
        color = self.get_alt_color(props)
        if not color:
            color = [0., 1., .6, 1.]
            if well_type.startswith('PE'):
                color = [0., 0.7, 1., 1.]
            elif well_type == 'PS' or well_type.startswith('PS_') \
                    or well_type.startswith('PS '):
                color = [1., 1., 1., 1.]
            elif well_type.startswith('P ossements'):
                color = [1., 1., 0., 1.]
        well.header()['material'] = {'diffuse': color, 'face_culling': 0}
        return well


    def make_well(self, center, radius, z, height, well_type=None, props=None):
        if well_type is None and props is not None:
            well_type = props.label
        if well_type == 'PS':
            return self.make_ps_well(center, radius, z, height, well_type,
                                     props)
        elif well_type == 'PS_sq':
            return self.make_ps_sq_well(center, radius, z, height, well_type,
                                        props)
        if well_type in ('PSh', 'sans', 'PSh sans', 'PSh sans_sq'):
            return self.make_psh_well(center, radius, z, height, props)
        elif well_type in ('PSh_sq', 'sans_sq'):
            return self.make_psh_sq_well(center, radius, z, height, props)
        elif well_type in ('echelle', u'échelle'):
            return self.make_ladder(center, radius, z, height, props)
        elif well_type.startswith('colim'):
            return self.make_spiral_stair(center, radius, z, height, props)

        if well_type.endswith('_sq'):
            return self.make_ps_sq_well(center, radius, z, height, well_type,
                                        props)

        return self.make_ps_well(center, radius, z, height, well_type, props)


    def make_arche(self, center, radius_and_trans, z, height, well_type=None,
                   props=None):
        # translate method name
        return self.make_arch(center, radius_and_trans, z, height,
                              well_type=well_type, props=props)

    def make_arch(self, center, radius_and_trans, z, height, well_type=None,
                  props=None):
        radius, trans = radius_and_trans
        # get transform parent to children
        tmat = np.eye(4)
        tmat[:2, :2] = trans[:2, :2]
        tmat[:2, 3:] = trans[:2, 2:3]
        # mesh will be created in source space, apply its source space center
        tr = aims.AffineTransformation3d(tmat)
        tr = tr.inverse()
        center0 = tr.transform((0, 0, 0))
        # source scale
        scl0 = (tr.transform((1, 0, 0)) - center0).norm()
        scl1 = (tr.transform((0, 1, 0)) - center0).norm()
        scl = (scl0 + scl1) / 2
        #print('arch:', center, ', scl:', scl, scl0, scl1, ', radius:', radius)
        radius = radius * scl * 0.5
        nf = 6
        wp = radius * 2.   # radius of the vault curve
        r0 = radius * 0.2 # radius of pillar stones
        amax = np.pi * .35 # max angle of the vault
        zscl = 1. # Z scaling of the vault ellipse
        wheight = 1.5 # straight wall height
        a0 = amax * 0.98
        c0 = center0 + (-wp * np.cos(a0), 0, wheight)

        arch = aims.AimsTimeSurface_3()
        cyl = aims.SurfaceGenerator.cylinder(c0 + (wp, 0, -wheight),
                                             c0 + (wp, 0, 0.07),
                                             r0, r0, nf, False, False)
        aims.SurfaceManip.meshMerge(arch, cyl)

        for i in range(4):
            alpha = i * amax / 4
            alpha2 = (i + 1.07) * amax / 4
            c1 = c0 + (wp * np.cos(alpha), 0, wp * np.sin(alpha) * zscl)
            c2 = c0 + (wp * np.cos(alpha2), 0, wp * np.sin(alpha2) * zscl)
            cyl = aims.SurfaceGenerator.cylinder(c1, c2, r0, r0, nf, False,
                                                 False)
            aims.SurfaceManip.meshMerge(arch, cyl)

        c0 = center0 + (wp * np.cos(a0), 0, wheight)
        cyl = aims.SurfaceGenerator.cylinder(c0 + (-wp, 0, -wheight),
                                             c0 + (-wp, 0, 0.07),
                                             r0, r0, nf, False, False)
        aims.SurfaceManip.meshMerge(arch, cyl)
        for i in range(4):
            alpha = i * amax / 4
            alpha2 = (i + 1.07) * amax / 4
            c1 = c0 + (-wp * np.cos(alpha), 0, wp * np.sin(alpha) * zscl)
            c2 = c0 + (-wp * np.cos(alpha2), 0, wp * np.sin(alpha2) * zscl)
            cyl = aims.SurfaceGenerator.cylinder(c1, c2, r0, r0, nf, False,
                                                 False)
            aims.SurfaceManip.meshMerge(arch, cyl)

        tmat = np.eye(4)
        tmat[:2, :2] = trans[:2, :2]
        tmat[:2, 3:] = trans[:2, 2:3]
        tmat[2, 3] = z
        tr = aims.AffineTransformation3d(tmat)
        aims.SurfaceManip.meshTransform(arch, tr)
        tmat2 = np.eye(4)
        tmat2[:3, 3] += center
        tr = aims.AffineTransformation3d(tmat2)
        aims.SurfaceManip.meshTransform(arch, tr)
        arch.header()['material'] = {'diffuse': [1., 1., 0.5, 1.]}
        return arch

    def start_depth_rect(self, child_xml, trans, style=None):
        level = self.item_props.level
        mesh_def = self.depth_meshes_def.get(level)
        if mesh_def is not None:
            print('Warning: several depth meshes for level',
                  level, ':', mesh_def[1])
            depth_mesh = mesh_def[0]
        else:
            depth_mesh = self.mesh_dict.setdefault(self.main_group,
                                                   aims.AimsTimeSurface_3())
            depth_mesh.header()['material'] = {'face_culling': 0,
                                              'diffuse': [0., 0.6, 0., 1.]}
        self.depth_maps.append(True)
        self.depth_meshes_def[level] = (depth_mesh, self.item_props)
        # print('start_depth_rect', self.main_group, '///', level)
        # print('level:', level)
        # print(self.item_props)

    def clean_depth(self):
        self.depth_maps.pop()


    def read_depth_group(self, child_xml, trans, style=None):
        if hasattr(self, 'depth_group'):
            raise RuntimeError(
                'Nested depth group in main_group %s, element: %s, items: %s'
                % (self.main_group, repr(child_xml),
                   repr(list(child_xml.items()))))
        self.depth_group = {}


    def clear_depth_group(self):
        if not hasattr(self, 'depth_group'):
            raise RuntimeError(
                'End of depth group outside of depth group. Current '
                'main_group: %s' % str(self.main_group))
        depth_mesh = self.mesh_dict[self.main_group]
        pos = self.depth_group.get('position')
        z = self.depth_group.get('depth')
        if pos is not None and z is not None:
            depth_mesh.vertex().append((pos[0], pos[1], -z * self.z_scale))
        del self.depth_group


    def read_depth_arrow(self, child_xml, trans, style=None):
        mesh = super(CataSvgToMesh, self).read_path(child_xml, trans, style)
        if len(mesh.vertex()) != 0:
            try:
                self.depth_group['position'] = mesh.vertex()[-1][:2]
            except Exception as e:
                print('failed depth arrow, main_group:', self.main_group,
                      ', vertices:')
                print(np.array(mesh.vertex()))
                print(e)


    def read_depth_text(self, child_xml, trans, style=None):
        text_span = [x for x in child_xml if x.tag.endswith('tspan')]
        if len(text_span) != 0:
            text = text_span[0].text
            try:
                depth = float(text)
            except ValueError:
                print('error in SVG, in depth text: found non-float value:',
                      repr(text), 'in element:', child_xml.get('id'),
                      child_xml.get('x'), child_xml.get('y'))
                raise
            if hasattr(self, 'depth_group'):
                self.depth_group['depth'] = depth
            else:
                # text outside a group: use its position
                try:
                    x = float(child_xml.get('x'))
                    y = float(child_xml.get('y'))
                except TypeError:
                    print('error in depth text position:', child_xml,
                          child_xml.get('x'), child_xml.get('y'),
                          ', in element:', child_xml.get('id'))
                    raise
                if trans is not None:
                    x, y = trans.dot([[x], [y], [1]])[:2]
                    x = x[0, 0]
                    y = y[0, 0]
                depth_mesh = self.mesh_dict[self.main_group]
                depth_mesh.vertex().append((x, y, -depth * self.z_scale))


    def read_depth_rect(self, rect_xml, trans, style=None):
        props = self.item_props  # self.group_properties.get(self.main_group)
        if not props.depth_map:
            # skip non-depth rects
            return
        depth_mesh = self.mesh_dict[self.main_group]
        x = float(rect_xml.get('x'))
        y = float(rect_xml.get('y'))
        if trans is not None:
            x, y = trans.dot([[x], [y], [1]])[:2]
            x = x[0, 0]
            y = y[0, 0]
        z = -np.max((float(rect_xml.get('width')),
                     float(rect_xml.get('height')))) * 10.
        depth_mesh.vertex().append((x, y, z * self.z_scale))

    def read_markers_map(self, filename):
        import csv
        #def _parse(item):
            #item = item.strip()
            #if '"' not in item and "'" not in item:
                #return [s.strip() for s in item.split(' ')]
            #q = item.find('"')
            #if q >= 0:
                #items = item.split('"')
            #else:
                #items = item.split("'")
            #parsed = []
            #i = 0
            #for item in items:
              #if i % 2 == 0:
                  #parsed += _parse(item)
              #else:
                  #parsed.append(item)
              #i += 1
            #return parsed

        try:
            mmap = {}
            with open(filename) as f:
                #for line in f.readlines():
                    #items = line.strip().split('\t')
                    #row = []
                    #for item in items:
                        #row += _parse(item)

                dialect = csv.Sniffer().sniff(f.read(1024))
                f.seek(0)
                #reader = csv.reader(f, delimiter='\t')
                reader = csv.reader(f, dialect=dialect)
                for row in reader:
                    if row:
                        if len(row) == 1:  # no \t separtator
                            row = [x.strip() for x in row[0].split()]
                        if len(row) == 1:  # still no split
                            print('marker without identifier:', row[0])
                            continue
                        if len(row) == 0:
                            continue  # empty line
                        mmap.setdefault(row[1], []).append(row[0])
        except Exception as e:
            print('error reading markers map file:', filename, file=sys.stderr)
            raise
        return mmap

    def read_markers(self, xml, marker_model, mtype, trans=None, style=None):
        print('READ', mtype.upper())
        if not hasattr(self, mtype):
            setattr(self, mtype, {})
        markers = getattr(self, mtype)
        if trans is None:
            trans = self.get_transform(xml)
        if trans is None:
            trans = np.matrix(np.eye(3))
        # print('trans:', trans)
        base_url = xml.get('markers_base_url')
        markers_map = {}
        markers_map_file = xml.get('markers_map')
        if markers_map_file:
            markers_map = self.read_markers_map(markers_map_file)
        if base_url is None:
            base_url = mtype + '/'
        if not base_url.endswith('/'):
            base_url += '/'

        layer_radius = xml.get('radius')
        if layer_radius is not None:
            layer_radius = float(layer_radius)
        else:
            layer_radius = 10.

        used_texts = {}
        missing = []

        for xml_element in xml:
            level = xml_element.get('level')
            if level is None:
                level = self.item_props.level
            text = None
            pos = None
            trans2 = xml_element.get('transform')
            trans_el = trans
            if trans2 is not None:
                transm = self.get_transform(trans2)
                trans_el = trans * transm
            if xml_element.tag.split('}')[-1] != 'g':
                xml_element = [xml_element]
            for sub_el in xml_element:
                tag = sub_el.tag.split('}')[-1]
                if tag == 'text':
                    if pos is None:
                        try:
                            pos = [float(sub_el.get('x')),
                                  float(sub_el.get('y'))]
                        except Exception as e:
                            if len(sub_el[:]) != 0 and sub_el[0].get('x') \
                                    and sub_el[0].get('y'):
                                try:
                                    pos = [float(sub_el[0].get('x')),
                                           float(sub_el[0].get('y'))]
                                except Exception as e:
                                    print(
                                        'error while reading marker',
                                        sub_el.get('id'))
                                    raise
                            else:
                                print(
                                    'error while reading marker',
                                    sub_el.get('id'))
                                raise
                        x, y = trans_el.dot([[pos[0]], [pos[1]], [1]])[:2]
                        pos = [x[0, 0], y[0, 0]]
                    text = sub_el[0].text.strip()
                elif tag == 'path':
                    trans3 = sub_el.get('transform')
                    trans_el2 = trans_el
                    if trans3 is not None:
                        transm = self.get_transform(trans3)
                        trans_el2 = trans_el * transm
                    mesh = super(CataSvgToMesh, self).read_path(sub_el,
                                                                trans_el2,
                                                                style)
                    if len(mesh.vertex()) != 0:
                        try:
                            pos = mesh.vertex()[-1][:2]
                        except:
                            print('failed marker arrow in', mtype,
                                  ', vertices:')
                            print(np.array(mesh.vertex()))
            radius = xml.get('radius')
            if radius is not None:
                radius = float(radius)
            else:
                radius = layer_radius

            if text and pos:
                if text.startswith('['):  # list
                    texts = [t.strip() for t in text[1:-1].split(',')]
                else:
                    texts = [text]
                images = []
                for text in texts:
                    imlist = markers_map.get(text)
                    if imlist is None:
                        if markers_map:
                            missing.append((text, pos))
                        imlist = [text]
                    images += imlist
                    used_texts.setdefault(text, []).append(pos)
                markers.append([pos + [level, radius],
                                [base_url + image for image in images]])
                # print('%s:' % mtype, markers[-1])
        print('read', len(markers), mtype)
        # check and print duplicates
        dup = False
        for text, pos in used_texts.items():
            if len(pos) != 1:
                if not dup:
                    print('** Duplicate markers texts in layer', mtype, ': **')
                    dup = True
                print('marker:', text, 'at positions:', pos)
        if missing:
            print('** Missing correspondance for marker texts: **')
            for m in missing:
                print(m[0], 'at position:', m[1])


    def read_lambert93(self, xml, trans=None):
        print('READ LAMBERT93')
        if trans is None:
            trans = np.matrix(np.eye(3))
        lambert_map = []
        for xml_element in xml:
            if xml_element.tag.split('}')[-1] != 'g':
                raise ValueError('lambert93 element is not a group:',
                                 xml_element)
            text = None
            pos = None
            trans2 = xml_element.get('transform')
            trans_el = np.matrix(np.eye(3))
            if trans2 is not None:
                transm = self.get_transform(trans2)
                if trans is None:
                    trans_el = transm
                else:
                    trans_el = trans * transm
            for sub_el in xml_element:
                tag = sub_el.tag.split('}')[-1]
                if tag == 'text':
                    if pos is None:
                        pos = [float(sub_el.get('x')),
                               float(sub_el.get('y'))]
                    text = sub_el[0].text
                elif tag == 'path':
                    trans3 = sub_el.get('transform')
                    trans_el2 = trans_el
                    if trans3 is not None:
                        transm = self.get_transform(trans3)
                        trans_el2 = trans_el * transm
                    mesh = super(CataSvgToMesh, self).read_path(sub_el,
                                                                trans_el2,
                                                                style=None)
                    if len(mesh.vertex()) != 0:
                        try:
                            pos = mesh.vertex()[-1][:2]
                        except:
                            print('failed lambert93 arrow, vertices:')
                            print(np.array(mesh.vertex()))
            if text and pos:
                lamb = text.strip().split(',')
                if len(lamb) != 2:
                    print('incorrect lambert93 coordinates:', text)
                    continue
                lambert_map.append((pos, [float(x) for x in lamb]))
                print('lambert93:', lambert_map[-1])

        self.lambert93_coords = lambert_map
        # regress
        from scipy import stats
        x = [l[0][0] for l in lambert_map]
        y = [l[1][0] for l in lambert_map]
        lamb_x = stats.linregress(x, y)
        x = [l[0][1] for l in lambert_map]
        y = [l[1][1] for l in lambert_map]
        lamb_y = stats.linregress(x, y)
        class xy(object):
            pass
        self.lambert_coords = xy()
        self.lambert_coords.x = lamb_x
        self.lambert_coords.y = lamb_y


    def change_level(self, mesh, dz):
        vert = mesh.vertex()
        for v in vert:
            v[2] += dz


    @staticmethod
    def delaunay(mesh):
        points = np.array([[p[0], p[1]] for p in mesh.vertex()])
        tri = Delaunay(points)
        mesh.polygon().assign(tri.simplices)
        #mesh.header()['material']['face_culling'] = 0


    @staticmethod
    def build_depth_win(depth_mesh, size=(1000, 1000), object_win_size=(8, 8)):
        headless = False
        if headless:
            import anatomist.headless as ana
            a = ana.HeadlessAnatomist()
        else:
            import anatomist.api as ana
            a = ana.Anatomist()
        from soma.qt_gui.qt_backend import Qt
        import time

        win = a.createWindow('Axial') #, options={'hidden': 1})
        Qt.qApp.processEvents()
        time.sleep(0.5)
        win.windowConfig(view_size=size, cursor_visibility=0)

        Qt.qApp.processEvents()
        time.sleep(0.5)
        Qt.qApp.processEvents()
        admesh = a.toAObject(depth_mesh)
        a.releaseObject(admesh)
        for i in range(10):
            time.sleep(0.2)
            Qt.qApp.processEvents()
        win.addObjects(admesh)
        for i in range(10):
            time.sleep(0.2)
            Qt.qApp.processEvents()
        view = win.view()
        bbmin = view.boundingMin()
        bbmax = view.boundingMax()
        bbsize = bbmax - bbmin

        # close up on center
        tbbmin = (bbmin + bbmax) / 2 \
            - aims.Point3df(object_win_size[0], object_win_size[1], 0)
        tbbmax = (bbmin + bbmax) / 2 \
            + aims.Point3df(object_win_size[0], object_win_size[1], 0)
        tbbmin[2] = bbmin[2]
        tbbmax[2] = bbmax[2]
        view.setExtrema(tbbmin, tbbmax)
        #view.qglWidget().updateGL()
        view.paintScene()
        #view.updateGL()
        return win, admesh


    def load_ground_altitude(self, filename):
        self.ground_img = None
        self.alt_bounds = None
        try:
            print('load ground altitude image:', filename)
            ground_img = aims.read(filename)
            alt_extr_filename = os.path.join(os.path.dirname(filename),
                                             'global.json')
            print('realding altidude extrema:', alt_extr_filename)
            alt_extr = json.load(open(alt_extr_filename))
            print('extrema:', alt_extr)

            scl_min = alt_extr['scale_min']
            scl_max = alt_extr['scale_max']
        except:
            print('no ground image', filename)
            return
        conv = aims.Converter(intype=ground_img, outtype=aims.Volume_FLOAT)
        self.ground_img \
            = conv(ground_img) * (scl_max - scl_min) / 255. + scl_min
        xml = self.svg.getroot()
        layers = [l for l in xml
                  if l.get('{http://www.inkscape.org/namespaces/inkscape}label')
                     == 'altitude']
        if len(layers) == 0:
            return
        layer = layers[0]
        grp = layer[0]
        self.main_group = 'altitude'
        self.alt_bounds = self.boundingbox(grp, None)


    def load_ground_altitude_bdalti(self, filename):
        '''
        filename:
            json map, to be used with the API module bdalti.py
        '''
        if bdalti is None:
            print('warning, bdalti module is not present')
            return
        if os.path.exists(filename):
            with open(filename) as f:
                self.bdalti_map = json.load(f)
            self.bdalti_base = os.path.dirname(filename)
        else:
            print('warning, BDAlti meta-map is not available, file %s '
                  'does not exist' % filename)


    def ground_altitude(self, pos, use_scale=True):
        if hasattr(self, 'bdalti_map') and hasattr(self, 'lambert_coords'):
            alt = self.ground_altitude_bdalti(pos)
        else:
            alt = self.ground_altitude_topomap(pos)
        if use_scale:
            # scale ground altitude the same way as depths in the map
            alt *= self.z_scale
        return alt


    def ground_altitude_topomap(self, pos):
        if not hasattr(self, 'alt_bounds') or self.alt_bounds is None \
                or self.ground_img is None:
            return 0.
        x = int((pos[0] - self.alt_bounds[0][0])
                / (self.alt_bounds[1][0] - self.alt_bounds[0][0])
                * (self.ground_img.getSizeX() - 0.001))
        y = int((pos[1] - self.alt_bounds[0][1])
                / (self.alt_bounds[1][1] - self.alt_bounds[0][1])
                * (self.ground_img.getSizeY() - 0.001))
        if x < 0 or y < 0 or x >= self.ground_img.getSizeX() \
                or y >= self.ground_img.getSizeY():
            return 50.  # arbitrary
        gray = self.ground_img.at(x, y)
        return gray


    def ground_altitude_bdalti(self, pos):
        x = pos[0] * self.lambert_coords.x.slope \
            + self.lambert_coords.x.intercept
        y = pos[1] * self.lambert_coords.y.slope \
            + self.lambert_coords.y.intercept
        z = bdalti.get_z(x, y, self.bdalti_map, self.bdalti_base,
                         background_z=50.)
        return z


    def add_ground_alt(self, mesh, verbose=False):
        print('add_ground_alt on:', mesh)
        for v in mesh.vertex():
            if verbose: print(v[2], end=' ')
            v[2] += self.ground_altitude(v[:2])
            if verbose: print('->', v[2])


    def build_depth_wins(self, size=(1000, 1000),
                         object_win_size=(8, 8)):
        self.depth_meshes = {}
        self.depth_wins = {}

        for level, mesh_def in self.depth_meshes_def.items():
            print('building depth map', level)
            depth_mesh, props = mesh_def
            win, amesh = self.build_depth_win(depth_mesh, size,
                                              object_win_size)
            self.depth_meshes[level] = amesh
            self.depth_wins[level] = win


    def release_depth_wins(self):
        del self.depth_meshes, self.depth_wins


    def get_depth(self, pos, view, object_win_size=(8, 8)):
        if view is None:
            # surface map
            return self.ground_altitude(pos)
        #pt = objectPositionFromWindow(pos)
        pt = aims.Point3df()
        ok = view.cursorFromPosition(pos, pt)
        if ok and (pt[0] < 0 or pt[0] >= view.width()
                   or pt[1] < 0 or pt[1] >= view.height()):
            ok = False
        if not ok:
            tbbmin = pos \
                - aims.Point3df(object_win_size[0], object_win_size[1], 0)
            tbbmax = pos \
                + aims.Point3df(object_win_size[0], object_win_size[1], 0)
            bbmin = view.boundingMin()
            bbmax = view.boundingMax()
            tbbmin[2] = bbmin[2]
            tbbmax[2] = bbmax[2]
            view.setExtrema(tbbmin, tbbmax)
            #view.qglWidget().updateGL()
            view.paintScene()
            ##view.updateGL()
            self.nrenders += 1
            ok = view.cursorFromPosition(pos, pt)
        if ok:
            ok = view.positionFromCursor(int(pt[0]), int(pt[1]), pt)
            if ok:
                return pt[2]
        #print('get_depth: point not found:', pos, pt)
        return None


    def get_alt_color(self, props, colorset=None, conv=True, get_bg=True):
        if colorset is None:
            colorset = self.colorset
        col = None
        while col is None and colorset:
            col = self.get_alt_color_s(props, colorset, conv)
            if col is None:
                colorset = self.colorset_inheritance.get(colorset)
        if isinstance(col, dict) and get_bg:
            bg = col.get('bg')
            if not bg:
                bg = col.get('fg')
            if bg is not None:
                col = bg
        return col


    @staticmethod
    def get_alt_color_s(props, colorset='map_3d', conv=True):
        if not props:
            return None
        color = None
        if props.label_alt_colors:
            color = props.label_alt_colors.get(props.label, {}).get(colorset)
        if not color:
            if not props.alt_colors:
                return None
            color = props.alt_colors.get(colorset)

        def convert_color(color):
            if isinstance(color, str) and color.startswith('#'):
                c1 = color[1::2]
                c2 = color[2::2]
                col = [float(int('%s%s' % (x, y), base=16)) / 255. for x,y in
                      zip(c1, c2)]
                #print('alt color:', props.main_group, col)
                return col
            try:
                return float(color)
            except Exception:
                return color

        if color:
            if not conv:
                return color
            if isinstance(color, str):
                return convert_color(color)
            elif isinstance(color, dict):
                return {k: convert_color(v) for k, v in color.items()}


    def apply_depths(self, meshes):
        self.nrenders = 0

        object_win_size = (2., 2.)
        self.build_depth_wins((250, 250))

        #return  # FIXME

        for main_group, mesh_l in meshes.items():
            props = self.group_properties.get(main_group)
            if not props:
                print('skip group', main_group, 'with no properties')
                continue

            if props.text or props.depth_map or props.arrow:
                # text and arrows will be done just after.
                # depth maps will not need it
                continue

            level = props.level
            win = self.depth_wins.get(level)
            debug = False
            if win is not None:
                view = win.view()
            else:
                view = None

            not_ok = 0
            if mesh_l is not None:
                print('processing corridor depth:', main_group, '(level:',
                      level, ')')
                alt_color = self.get_alt_color(props)

                hshift = (props.height_shift
                          if props.height_shift else 0.) * self.z_scale
                failed = 0
                done = 0
                if not isinstance(mesh_l, list):
                    mesh_l = [mesh_l]
                for mesh in mesh_l:
                    if not hasattr(mesh, 'vertex'):
                        # not a mesh: skip it
                        continue
                    if alt_color:
                        if 'material' not in mesh.header():
                            mesh.header()['material'] = {}
                        mesh.header()['material']['diffuse'] = alt_color
                    for v in mesh.vertex():
                        z = self.get_depth(v, view, object_win_size)
                        if z is not None:
                            v[2] += z + hshift
                        else:
                            failed += 1
                            if debug:
                                print('missed Z:', v)
                    done += len(mesh.vertex())
                if failed != 0:
                    print('failed:', failed, '/', done)
                    if float(failed) / done >= 0.2:
                        print('abnormal failure rate - '
                          'malfunction in 3D renderings ?')
                        debug = True

        # apply texts depths
        text_zshift = 5.
        for main_group, mesh_items in six.iteritems(meshes):
            props = self.group_properties.get(main_group)
            if not props or not props.text:
                continue

            for text_item in mesh_items['objects']:
                position = text_item.get('properties', {}).get('position')
                if position is not None:
                    level = text_item.get('properties', {}).get('level',
                                                                '')
                    win = self.depth_wins[level]
                    if win is not None:
                        view = win.view()
                        hshift = ((props.height_shift
                                   if props.height_shift else 0.)
                                  + text_zshift) * self.z_scale
                        z = self.get_depth(position, view, object_win_size)
                        if z is not None and z + hshift > position[2]:
                            position[2] = z + hshift

        print('built depths in', self.nrenders, 'renderings')


    def apply_arrow_depth(self, mesh, props):
        alt_color = self.get_alt_color(props)
        if alt_color:
            mesh.header()['material']['diffuse'] = alt_color

        arrow_type = props.label
        level = props.level
        tz_level = props.upper_level
        hshift = props.height_shift
        if hshift is None:
            hshift = 0.
        hshift *= self.z_scale
        text_hshift = props.arrow_base_height_shift
        if text_hshift is None:
            text_hshift = 4.
        text_hshift *= self.z_scale
        text_win = self.depth_wins.get(tz_level)
        object_win_size = (8, 8)
        win = self.depth_wins.get(level)
        hshift1 = hshift + text_hshift
        view = None
        text_view = None
        if win is not None:
            view = win.view()
        if text_win is not None:
            text_view = text_win.view()

        # print('ARROW DEPTH for', props)
        for v in mesh.vertex():
            z = self.get_depth(v, view, object_win_size)
            if z is not None:
                z += hshift
                old_z = v[2]  # old_z is a weight between text and z
                text_z = self.get_depth(v, text_view, object_win_size)
                if text_z is None:
                    text_z = 0.
                text_z += text_hshift
                new_z = z * old_z + text_z * (1. - old_z)
                # print('w:', old_z, ', t: ', text_z, ', a:', z, ':', new_z)
                v[2] = new_z
            else:
                pass # warn ?


    def build_wells_with_depths(self, meshes):

        views = {level: win.view() for level, win in self.depth_wins.items()}

        for main_group in list(meshes.keys()):
            specs = meshes[main_group]
            props = self.group_properties.get(main_group)
            if not props or not specs:
                continue
            method = None
            stype = props.label
            if hasattr(self, 'make_%s' % stype):
                method = getattr(self, 'make_%s' % stype)
            elif props.well:
                method = self.make_well
            if method:
                level = props.level
                next_level = props.upper_level
                view = views.get(level)
                view_up = views.get(next_level)

                wells = None
                for ws in specs:
                    try:
                        center, radius, z, height = ws
                    except TypeError:
                        import traceback
                        traceback.print_exc()
                        print('= while processing', main_group)
                        print('ws:', ws)
                        print('method:', method)
                        print('specs:', specs)
                        raise
                    c3 = (center[0], center[1], 0.)
                    z0 = self.get_depth(c3, view)
                    if z0 is not None:
                        z = z0
                    z0 = self.get_depth(c3, view_up)
                    if z0 is not None:
                        height = z0 - z
                    shift = props.height_shift
                    if shift is None:
                        shift = 0.
                    pheight = props.height
                    if pheight is None:
                        pheight = 0.
                    well = method(center, radius,
                                  z + shift * self.z_scale,
                                  height + pheight * self.z_scale,
                                  well_type=None,
                                  props=props)
                    if wells is None:
                        wells = well
                    else:
                        aims.SurfaceManip.meshMerge(wells, well)
                meshes[main_group + '_tri'] = wells
                self.group_properties[main_group + '_tri'] = props


    def tesselate(self, mesh, flat=False):
        import anatomist.api as ana
        a = ana.Anatomist()
        a.setUserLevel(5)  # needed to use tesselation fusion
        orig_pos = np.array(mesh.vertex())
        if 'transformation' in mesh.header():
            # if the mesh has a 3D transformation, don't do that
            flat = False
        if flat:
            # tessalate at constant Z, then set back Z after tesselation
            for v in mesh.vertex():
                v[2] = 0.
        amesh = a.toAObject(mesh)
        a.releaseObject(amesh)
        all_obj = a.getObjects()
        atess = a.fusionObjects([amesh], method='TesselationMethod')
        if not atess:
            print('cannot make tesselation object for:', amesh.name)
            return None
        atess_m = [o for o in a.getObjects()
                   if o not in all_obj and o != atess][0]
        # force tesselating
        atess.render([], ana.cpp.ViewState())
        tess = a.toAimsObject(atess_m)
        if flat:
            #print('tesselate flat. orig vert:', len(orig_pos), len(tess.vertex()))
            for v, ov in zip(mesh.vertex(), orig_pos):
                v[2] = ov[2]
                # find nearest vertex for tesselated
        if len(tess.vertex()) == 0:
            return None  # no tesselation
        if flat:
            mvert = np.array(orig_pos)[:, :2]
            for tv in tess.vertex():
                i = np.argmin(np.sum((mvert - tv[:2]) ** 2, axis=1))
                tv[2] = orig_pos[i][2]
        del atess
        del atess_m
        del amesh
        tess.header().update(mesh.header())
        if 'polygon_dimension' in tess.header():
            del tess.header()['polygon_dimension']
        if 'material' in tess.header():
            mat = tess.header()['material']
        else:
            mat = {}
        mat['face_culling'] = 0
        return tess


    def make_cat_flap(self, mesh, color=[1., 0., 0., 0.8]):
        def connected_meshes(mesh):
            vert_mesh = {}
            for link in mesh.polygon():
                mesh1 = vert_mesh.get(link[0])
                mesh2 = vert_mesh.get(link[1])
                if mesh1 is None and mesh2 is None:
                    # segment in new mesh
                    mesh1 = [link[0], link[1]]
                    vert_mesh[link[0]] = mesh1
                    vert_mesh[link[1]] = mesh1
                elif mesh1 is None:
                    # prepend to mesh2
                    mesh2.insert(0, link[0])
                    vert_mesh[link[0]] = mesh2
                elif mesh2 is None:
                    # append to mesh1
                    mesh1.append(link[1])
                    vert_mesh[link[1]] = mesh1
                else:
                    # connect 2 meshes
                    if mesh1 is mesh2:
                        # loop
                        # print('mesh1 is mesh2')
                        if link[0] == mesh1[-1]:
                            mesh1.append(link[1])
                        continue
                    mesh1 += mesh2
                    for v in mesh2:
                        vert_mesh[v] = mesh1
            # check duplicates
            meshes = []
            for m in vert_mesh.values():
                if len([n for n in meshes if n is m]) == 0:
                    meshes.append(m)
            return meshes

        def slice_segment(mesh, v0, v, alt, offset, slen, xradius,
                          zradius, connected=False, prev_v=None, next_v=None):

            def shift_point(p, shift_s, sh_fac):
                return p \
                    + ((p.dot(shift_s[0]) + shift_s[1]) * shift_s[2]
                       * sh_fac[0] \
                    + (p.dot(shift_s[3]) + shift_s[4]) * shift_s[5] \
                       * sh_fac[1]) * shift_s[6]

            def section_vertices(v0, xdir, zdir, xradius, zradius, shift_s,
                                 sh_fac):
                pts = [v0 - xdir * xradius - zdir * zradius / 2,
                       v0 - xdir * xradius + zdir * zradius / 2,
                       v0 - xdir * xradius / 2 + zdir * zradius,
                       v0 + xdir * xradius / 2 + zdir * zradius,
                       v0 + xdir * xradius + zdir * zradius / 2,
                       v0 + xdir * xradius - zdir * zradius / 2,
                       v0 + xdir * xradius / 2 - zdir * zradius,
                       v0 - xdir * xradius / 2 - zdir * zradius]
                return [shift_point(p, shift_s, sh_fac) for p in pts]

            def add_prev_section_vertices(mesh, alt, connected, v0, xdir,
                                          zdir, xradius, zradius, shift_s,
                                          sh_fac):
                vert = mesh[alt].vertex()
                if not connected or len(mesh[1-alt].vertex()) == 0:
                    vert += section_vertices(v0, xdir, zdir, xradius, zradius,
                                             shift_s, sh_fac)
                else:
                    vert += mesh[1-alt].vertex()[-8:]

            def section_polygons(n):
                poly = [((n+i, n+i+8, n+8+(i+1)%8),
                         (n+i, n+8+(i+1)%8, n+(i+1)%8))
                        for i in range(8)]
                #poly = [((n+i+8, n+i, n+8+(i+1)%8),
                         #(n+8+(i+1)%8, n+i, n+(i+1)%8))
                        #for i in range(8)]
                return [p for dp in poly for p in dp]

            def build_shift(v0, prev_v, direc):
                if prev_v is None:
                    return (aims.Point3df(0, 0, 0), 0., 0.)
                prev_direc = (v0 - prev_v).normalize()
                diff_axis = prev_direc.crossed(direc) # rotation axis
                if diff_axis.norm2() != 0:
                    diff_plane = direc.crossed(diff_axis).normalize()
                    diff_offset = -diff_plane.dot(v0)
                    n = diff_axis.norm()
                    if diff_axis.norm() > 0.95:
                        n = 0.95
                    diff_angle = math.asin(n) / 2
                    diff_depth = math.tan(diff_angle)
                else:
                    return (aims.Point3df(0, 0, 0), 0., 0.)
                shift_s = (diff_plane, diff_offset, -diff_depth)
                return shift_s

            def build_shift2(next_v, v, direc):
                if next_v is None:
                    return (aims.Point3df(0, 0, 0), 0., 0.)
                next_direc = (next_v - v).normalize()
                diff_axis = direc.crossed(next_direc) # rotation axis
                if diff_axis.norm2() != 0:
                    diff_plane = direc.crossed(diff_axis).normalize()
                    diff_offset = -diff_plane.dot(v)
                    n = diff_axis.norm()
                    if diff_axis.norm() > 0.95:
                        n = 0.95
                    diff_angle = math.asin(n) / 2
                    diff_depth = math.tan(diff_angle)
                else:
                    return (aims.Point3df(0, 0, 0), 0., 0.)
                shift_s = (diff_plane, diff_offset, diff_depth)
                return shift_s

            direc = (v - v0).normalize()
            mlen = (v - v0).norm()
            if mlen == 0:
                # zero length segment: nothing to do.
                return alt, offset

            # section plane
            xdir = direc.crossed((0., 0., 1.))
            if xdir.norm2() == 0:
                xdir = aims.Point3df(1, 0, 0)
                zdir = aims.Point3df(0, 1, 0)
            else:
                zdir = xdir.crossed(direc)

            prev_shift_s = build_shift(v0, prev_v, direc)
            #next_v = None
            next_shift_s = build_shift2(next_v, v, direc)
            shift_s = prev_shift_s + next_shift_s + (direc, )

            x = 0.
            vert = [m.vertex() for m in mesh]
            poly = [m.polygon() for m in mesh]

            ## DEBUG
            #n = vert[0].size()
            #vert[0] += [v, v + shift_s[3]* 2, v + direc]
            #poly[0] += [(n, n+1, n+2)]
            #n = vert[1].size()
            #if next_v:
                #prev_direc = (next_v - v).normalize()
                #vert[1] += [v, v+shift_s[3]* 1.5, v0 + prev_direc*0.6]
                #poly[1] += [(n, n+1, n+2)]

            if offset > 0:
                x = min((slen - offset, mlen))
                add_prev_section_vertices(mesh, alt, False, v0, xdir,
                                          zdir, xradius, zradius, shift_s,
                                          (1., 0))
                sfac = x / mlen
                vert[alt] += section_vertices(v0 + direc * x, xdir, zdir,
                                              xradius, zradius, shift_s,
                                              (1.-sfac, sfac))
                poly[alt] += section_polygons(len(vert[alt]) - 16)
                connected = True
                if x <= mlen:
                    alt = 1 - alt
            x2 = x
            for x in np.arange(x, mlen - slen, slen):
                x2 = min(x + slen, mlen)
                sfac = x / mlen
                add_prev_section_vertices(mesh, alt, connected,
                                          v0 + direc * x, xdir, zdir, xradius,
                                          zradius, shift_s, (1.-sfac, sfac))
                sfac = x2 / mlen
                vert[alt] += section_vertices(v0 + direc * x2, xdir, zdir,
                                              xradius, zradius, shift_s,
                                              (1.-sfac, sfac))
                poly[alt] += section_polygons(len(vert[alt]) - 16)
                connected = True
                if x2 <= mlen:
                    alt = 1 - alt
            if x2 < mlen:
                sfac = x2 / mlen
                add_prev_section_vertices(mesh, alt, connected,
                                          v0 + direc * x2, xdir, zdir,
                                          xradius, zradius, shift_s,
                                          (1.-sfac, sfac))
                vert[alt] += section_vertices(v0 + direc * mlen, xdir, zdir,
                                              xradius, zradius, shift_s,
                                              (0., 1.))
                poly[alt] += section_polygons(len(vert[alt]) - 16)
                connected = True
            offset = (offset + mlen) - int((offset + mlen) / slen) * slen
            return alt, offset

        slen = 1. # length of zebra item
        cols = [color, [1., 1., 1., 0.8]] # alterning colors
        xradius = 0.3
        zradius = 0.2
        meshes = connected_meshes(mesh)
        vert = mesh.vertex()
        smesh = [aims.AimsSurfaceTriangle(), aims.AimsSurfaceTriangle()]
        smesh[0].header()['material'] = {'diffuse': cols[0]}
        smesh[1].header()['material'] = {'diffuse': cols[1]}
        alt = 0
        for sub_mesh in meshes:
            offset = 0.
            connected = False
            prev_v = None
            #smesh = [aims.AimsSurfaceTriangle(), aims.AimsSurfaceTriangle()]
            v0 = vert[sub_mesh[0]]
            n = len(sub_mesh)
            for i, v in enumerate(sub_mesh[1:]):
                v1 = vert[v]
                if i >= n - 2:
                    next_v = None
                else:
                    next_v = vert[sub_mesh[i + 2]]
                alt, offset = slice_segment(smesh, v0, v1, alt, offset,
                                            slen, xradius, zradius, connected,
                                            prev_v, next_v)
                connected = True
                prev_v = v0
                v0 = v1

        smesh[0].updateNormals()
        smesh[1].updateNormals()

        return smesh


    def recolor_text_specs(self, text_specs, diffuse):
        for tospec in text_specs['objects']:
            for tspec in tospec['objects']:
                props = tspec.setdefault('properties', {})
                material = props.setdefault('material', {})
                material['diffuse'] = diffuse


    def postprocess(self, meshes):
        # lighen texts for black background
        tspec = meshes.get('annotations_text')
        if tspec is not None:
            self.recolor_text_specs(tspec, [.8, .8, .8, 1.])
        tspec = meshes.get('rues sans plaques_text')
        if tspec is not None:
            self.recolor_text_specs(tspec, [.6, .6, .6, 1.])

        # move arrows in order to follow text in 3D
        self.attach_arrows_to_text(meshes, with_squares=False)

        # get ground altitude map
        #self.load_ground_altitude(
            #os.path.join(os.path.dirname(self.svg_filename),
                         #'altitude', 'real', 'alt_image.png'))
        bdalti_map = os.path.join(
            os.path.dirname(self.svg_filename),
            'altitude', 'BDALTIV2_2-0_75M_ASC_LAMB93-IGN69_FRANCE_2020-04-28',
            'BDALTIV2', 'map.json')
        self.load_ground_altitude_bdalti(bdalti_map)

        # make depth maps
        for level, mesh_def in self.depth_meshes_def.items():
            mesh, props = mesh_def
            if mesh is not None:
                self.add_ground_alt(mesh)
                self.delaunay(mesh)

        meshes['grille surface'] = self.build_ground_grid()
        props = ItemProperties()
        props.level = 'surf'
        props.category = 'Surface'
        self.group_properties['grille surface'] = props

        # apply depths to corridors
        self.apply_depths(meshes)

        # build wells with inf/sup depths
        self.build_wells_with_depths(meshes)

        # apply real depths to arrows
        for main_group in list(meshes.keys()):
            props = self.group_properties.get(main_group)
            if not props or not props.arrow:
                continue
            mesh_l = meshes.get(main_group)
            if not mesh_l:
                contine
            if not isinstance(mesh_l, list):
                mesh_l = [mesh_l]
            for mesh in mesh_l:
                self.apply_arrow_depth(mesh, props)
                if 'material' not in mesh.header():
                    mesh.header()['material'] \
                        = {'diffuse': [1., 0.5, 0., 1.]}
                mesh.header()['material']['line_width'] = 2.

        # extrude corridors walls
        for main_group in list(meshes.keys()):
            # here we iterate through list(keys) instead of using items()
            # because some processings will insert new meshes in meshes,
            # and this would make the iteration fail
            props = self.group_properties.get(main_group)
            if not props:
                continue
            print('extrude:', main_group, props.corridor, props.block)
            # print(props)
            mesh_l = meshes[main_group]
            if mesh_l and props.corridor or props.block or props.wall:
                if not isinstance(mesh_l, list):
                    mesh_l = [mesh_l]
                for mesh in mesh_l:
                    if not hasattr(mesh, 'vertex'):
                        # not a mesh
                        continue
                    height = props.height * self.z_scale
                    ceil, wall = self.extrude(mesh, height)
                    if 'material' not in ceil.header():
                        ceil.header()['material'] \
                            = {'diffuse': [0.3, 0.3, 0.3, 1.]}
                    elif 'diffuse' not in ceil.header()['material']:
                        ceil.header()['material']['diffuse'] = [0.3, 0.3,
                                                                0.3, 1.]
                    else:
                        color = list(ceil.header()['material']['diffuse'])
                        intensity \
                            = np.sqrt(np.sum(np.array(color[:3])**2) / 3)
                        if intensity <= 0.75:
                            for i in range(3):
                                c = color[i] + 0.4
                                #if c > 1.:
                                    #c = 1.
                                color[i] = c
                            m = max(color[:3])
                            if m > 1.:
                                for i in range(3):
                                    color[i] /= m
                        else:
                            for i in range(3):
                                c = color[i] - 0.4
                                if c < 0.:
                                    c = 0.
                                color[i] = c
                        ceil.header()['material']['diffuse'] = color
                    meshes.setdefault(main_group + '_wall', []).append(wall)
                    meshes.setdefault(main_group + '_ceil', []).append(ceil)
                    self.group_properties[main_group + '_wall'] = props
                    self.group_properties[main_group + '_ceil'] = props
                    self.group_properties[main_group + '_floor'] = props

                    # build floor or ceiling meshes using tesselated objects
                    # (anatomist)
                    if props.block:
                        # "blocks" have a closed ceiling
                        tess_mesh = self.tesselate(ceil, flat=True)
                        if tess_mesh is not None:
                            meshes.setdefault(main_group + '_ceil_tri',
                                              []).append(tess_mesh)
                            self.group_properties[main_group + '_ceil_tri'] \
                                = props

                    if props.corridor:
                        # corridor have a closed floor
                        # print('tesselate corridor:', props.main_group)
                        tess_mesh = self.tesselate(mesh, flat=True)
                        if tess_mesh is not None:
                            meshes.setdefault(main_group+ '_floor_tri',
                                              []).append(tess_mesh)
                            self.group_properties[main_group + '_floor_tri'] \
                                = props

        # merge meshes in each group
        self.merge_meshes_by_group(meshes)

        # fix normals of limestone parts
        for corridor, mesh in six.iteritems(meshes):
            if corridor.startswith('calcaire') \
                    and corridor.endswith('_ceil_tri'):
                mesh.normal().assign(
                    np.array([0., 0., 1.]) * np.ones((len(mesh.vertex()), 1)))

        # make cat flap mesh
        catflap_col = {'bas': [0.85, 0.56, 0.16, 0.8],
                       u'injecté': [0.66, 0.61, 0.63, 0.8]}
        for main_group in list(meshes.keys()):
            props = self.group_properties.get(main_group)
            if not props or not props.catflap:
                continue
            mesh = meshes[main_group]
            if mesh is not None:
                color = catflap_col.get(props.label)
                if color is None:
                    color = mesh.header().get('material', {}).get('diffuse')
                    if not color:
                        color = [1., 0., 0., 0.8]
                cat_flap = self.make_cat_flap(mesh, color)
                meshes['%s_0' % main_group] = cat_flap[0]
                meshes['%s_1' % main_group] = cat_flap[1]
                self.group_properties['%s_0' % main_group] = props
                self.group_properties['%s_1' % main_group] = props
                del meshes[main_group]

        # sounds and photos depth + markers meshes
        object_win_size = [8, 8]

        protos = {'sounds': 'sounds_marker_model',
                  'sounds_private': 'sounds_marker_model',
                  'photos': 'photos_marker_model',
                  'photos_private': 'photos_marker_model'}

        for mtype, proto in protos.items():
            mesh = None
            mesh_proto = getattr(self, proto)
            print(mtype, 'proto:', len(mesh_proto.vertex()))
            for mpos in getattr(self, mtype):
                pos = mpos[0][:3]
                radius = mpos[0][3]
                level = pos[2]
                win = self.depth_wins[level]
                z = self.get_depth(pos[:2] + [0.], win.view(),
                                    object_win_size)
                if z is None:
                    print('failed to get depth for:', mtype, pos, level)
                    z = 0.
                mpos[0][2] = z
                pos[2] = z
                # print('marker:', level, pos)
                mmesh = type(mesh_proto)(mesh_proto)  # copy
                trans = aims.AffineTransformation3d()
                trans.setTranslation(pos)
                aims.SurfaceManip.meshTransform(mmesh, trans)
                if mesh is None:
                    mesh = mmesh
                else:
                    aims.SurfaceManip.meshMerge(mesh, mmesh)
                # print('marker:', pos, len(mesh.vertex()))
            if mesh is not None:
                main_group = '%s_mesh' % mtype
                self.mesh_dict[main_group] = mesh
                meshes[main_group] = mesh
                props = ItemProperties()
                props.category = 'markers'
                self.group_properties[main_group] = props
                print('--- marker mesh:', main_group, len(mesh.vertex()), props)
            else: print('NO MARKER MESH:', mtype)


    def attach_arrows_to_text(self, meshes, with_squares=False):
        # find text attached to each arrow
        for arrow, mesh_l in meshes.items():
            props = self.group_properties.get(arrow)
            if props and props.arrow and mesh_l:
                if not isinstance(mesh_l, list):
                    mesh_l = [mesh_l]
                for mesh in mesh_l:
                    if not hasattr(mesh, 'vertex'):
                        print('*** WARNING: ***')
                        print('A non-mesh object lies in an arrows '
                              'layer/group')
                        print(props)
                        print('faulty mesh:', mesh)
                        continue
                    text_o = self.find_text_for_arrow(meshes, mesh)
                    if text_o:
                        props = text_o['properties']
                        pos = props['position']
                        vert = mesh.vertex()
                        size = props['size']
                        # vert2 = aims.vector_POINT3DF(vert)
                        decal = aims.Point3df(pos[0], pos[1], vert[0][2]) \
                            - vert[0]
                        #print('decal text', text_o['objects'][0]['properties']['text'], list(decal), 'to:', pos, ', size', size)
                        n = len(vert)
                        for i, v in enumerate(vert):
                            # v += decal * float(n - i) / n
                            v += decal * (1. - v[2])
                        if with_squares:
                            # debug: display rectangle around text location
                            size = props['size']
                            x0 = pos[0] - size[0] / 2
                            x1 = pos[0] + size[0] / 2
                            y0 = pos[1] - size[1] / 2
                            y1 = pos[1] + size[1] / 2
                            vert = mesh.vertex()
                            z = vert[0][2]
                            n = len(vert)
                            vert += [(x0, y0, z), (x1, y0, z), (x1, y1, z),
                                     (x0, y1, z)]
                            poly = mesh.polygon()
                            poly += [(n, n+1), (n+1, n+2), (n+2, n+3),
                                     (n+3, n)]


    def find_text_for_arrow(self, meshes, mesh):
        dmin = -1
        text_min = None
        point = mesh.vertex()[0][:2]
        #print('find_text_for_arrow', mesh, point)
        for mtype, mesh_items in six.iteritems(meshes):
            if mtype.endswith('_text'):
                #print(mtype, ' text:', mesh_items)
                for text in mesh_items['objects']:
                    #print('text:', text)
                    props = text['properties']
                    #print('props:', props)
                    pos = props.get('position')
                    size = props['size']
                    #print('pos:', pos, ', size:', size)
                    # distances to each segment
                    x0 = pos[0] - size[0] / 2
                    x1 = pos[0] + size[0] / 2
                    y0 = pos[1] - size[1] / 2
                    y1 = pos[1] + size[1] / 2
                    if point[0] < x0:
                        d0 = x0 - point[0]
                    elif point[0] > x1:
                        d0 = point[0] - x1
                    else:
                        d0 = 0
                    if point[1] < y0:
                        d1 = y0 - point[1]
                    elif point[1] > y1:
                        d1 = point[1] - y1
                    else:
                        d1 = 0
                    d = d0 * d0 + d1 * d1
                    if dmin < 0 or d < dmin:
                        dmin = d
                        text_min = text
                    if d == 0:
                        # found a good match, skip other tests
                        break
        return text_min


    def build_ground_grid(self):
        layer = [l for l in self.svg.getroot()
                 if l.get('{http://www.inkscape.org/namespaces/inkscape}label')
                     in ('bord_sud', 'bord complet')]
        if not layer:
            print('No border layer found. Not building ground grid.')
            return aims.AimsTimeSurface_2()  # no layer
        layer = layer[0]
        label = layer.get('{http://www.inkscape.org/namespaces/inkscape}label')
        self.main_group = label
        bounds = self.boundingbox(layer)
        # print('ground grid bounds:', bounds)
        props = [y for x, y in self.group_properties.items()
                 if y.label == label]
        interval = 5.
        if props:
            props = props[0]
            if props.grid_interval:
                interval = props.grid_interval

        grid = np.mgrid[bounds[0][0]:bounds[1][0]:interval,
                        bounds[0][1]:bounds[1][1]:interval].T
        grid_v = grid.reshape((grid.shape[0] * grid.shape[1], 2))
        grid_v = np.hstack((grid_v, np.zeros((grid_v.shape[0], 1))))
        grid_s = [(i + j*grid.shape[1], i+1 + j*grid.shape[1])
                  for j in range(grid.shape[0])
                  for i in range(grid.shape[1] - 1)] \
            + [(i + j*grid.shape[1], i + (j + 1) * grid.shape[1])
                  for j in range(grid.shape[0] - 1)
                  for i in range(grid.shape[1])]
        mesh = aims.AimsTimeSurface_2()
        mesh.vertex().assign(grid_v)
        mesh.polygon().assign(grid_s)
        mesh.header()['material'] = {'diffuse': [0.9, 0.9, 0.9, 1.]}
        self.ground_grid = mesh
        # print('ground grid:', mesh.vertex().size(), 'vertices')
        return mesh


    def make_skull_model(self, xml):
        cm = CataMapTo2DMap()
        protos = cm.find_protos(xml)
        if not protos:
            return
        skproto = protos.get('label')
        if not skproto:
            return
        skproto = skproto.get('ossuaire')
        if skproto is None:
            return
        self.main_group = 'ossuaire_model'
        skmesh_l = aims.AimsTimeSurface_2()
        for child in skproto['element']:
            aims.SurfaceManip.meshMerge(
                skmesh_l, self.read_path(child,
                                         self.proto_scale * skproto['trans']))
        skmesh_up_l, skmesh_w = self.extrude(skmesh_l, 1.)
        skmesh_bk = self.tesselate(skmesh_l)
        skmesh_up = self.tesselate(skmesh_up_l)
        aims.SurfaceManip.invertSurfacePolygons(skmesh_w)
        skmesh_w.updateNormals()
        aims.SurfaceManip.invertSurfacePolygons(skmesh_bk)
        skmesh_bk.updateNormals()
        aims.SurfaceManip.meshMerge(skmesh_w, skmesh_bk)
        aims.SurfaceManip.meshMerge(skmesh_w, skmesh_up)
        vert = np.asarray(skmesh_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        bbmax = aims.Point3df(np.max(vert, axis=0))
        center = (bbmin + bbmax) / 2
        vert -= center
        skmesh_w.vertex().assign(vert)
        q = aims.Quaternion()
        q.fromAxis([1., 0., 0.], -np.pi / 2)
        tr = aims.AffineTransformation3d(q)
        aims.SurfaceManip.meshTransform(skmesh_w, tr)
        vert = np.asarray(skmesh_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        vert += [0., 0., 1.5 - bbmin[2]]
        skmesh_w.vertex().assign(vert)
        return skmesh_w


    def make_fontis_model(self, xml):
        cm = CataMapTo2DMap()
        protos = cm.find_protos(xml)
        if not protos:
            return
        fproto = protos['label'].get('fontis')
        if fproto is None:
            return
        self.main_group = 'fontis'
        fmesh_l = aims.AimsTimeSurface_2()
        fmesh_l.header()['material'] = {'diffuse': [0.74, 0.33, 0., 1.]}
        for child in fproto['element'][1:]:
            aims.SurfaceManip.meshMerge(
                fmesh_l, self.read_path(child,
                                        self.proto_scale * fproto['trans']))
        fmesh_up_l, fmesh_w = self.extrude(fmesh_l, 0.3)
        fmesh_bk = self.tesselate(fmesh_l)
        fmesh_up = self.tesselate(fmesh_up_l)
        aims.SurfaceManip.invertSurfacePolygons(fmesh_w)
        fmesh_w.updateNormals()
        aims.SurfaceManip.invertSurfacePolygons(fmesh_bk)
        fmesh_bk.updateNormals()
        aims.SurfaceManip.meshMerge(fmesh_w, fmesh_bk)
        aims.SurfaceManip.meshMerge(fmesh_w, fmesh_up)
        vert = np.asarray(fmesh_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        bbmax = aims.Point3df(np.max(vert, axis=0))
        center = (bbmin + bbmax) / 2
        vert -= center
        fmesh_w.vertex().assign(vert)
        vert = np.asarray(fmesh_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        vert += [0., 0., - bbmin[2]]
        fmesh_w.vertex().assign(vert)
        return fmesh_w


    def make_water_scale_model(self, pos, size):
        s1 = size * 0.1
        s2 = size * 0.2
        s9 = size * 0.9
        s95 = size * 0.95
        p = aims.Point3df(pos)
        para = aims.SurfaceGenerator.parallelepiped_wireframe(
            p - (size, size, s1), p + (size, size, s1))
        para2 = aims.SurfaceGenerator.parallelepiped_wireframe(
            p - (s9, s9, s1), p + (s9, s9, s1))
        para3 = aims.SurfaceGenerator.parallelepiped_wireframe(
            p + (-s2, s95, -size), p + (s2, size, size))
        aims.SurfaceManip.meshMerge(para, para2)
        aims.SurfaceManip.meshMerge(para, para3)
        para.header()['material'] = {'diffuse': [1., 0.9, 0.64, 1.]}

        mesh = aims.AimsTimeSurface_3()
        cube = aims.SurfaceGenerator.cube((0., 0., 0.), size)
        vert = np.asarray(cube.vertex()) * (1., 1., 0.1)
        vert2 = np.asarray(cube.vertex()) * (.9, .9, 0.1)
        mesh.vertex().assign(np.vstack((vert, vert2)) + pos)
        poly = np.asarray(cube.polygon()[2:-2])
        poly2 = poly + len(cube.vertex())
        c = np.array(poly2[:, 2])
        poly2[:, 2] = poly2[:, 1]
        poly2[:, 1] = c

        poly = np.vstack((poly, poly2))

        poly2 = np.array([(0, 24, 3), (3, 24, 27), (3, 27, 6), (6, 27, 30),
                          (6, 30, 9), (9, 30, 33), (9, 33, 0), (0, 33, 24)])
        poly3 = np.vstack((poly2[:, 0], poly2[:, 2], poly2[:, 1])).T + 12

        poly = np.vstack((poly, poly2, poly3))
        mesh.polygon().assign(poly)

        vert3 = np.asarray(cube.vertex()) * (0.2, 0.025, 1.) \
            + (0, size * 0.975, 0) + pos
        cube.vertex().assign(vert3)
        aims.SurfaceManip.meshMerge(mesh, cube)

        mesh.header()['material'] = {'diffuse': [.96, 0.88, 0.64, 1.]}

        water = aims.AimsTimeSurface_3()
        vert3 = np.hstack((vert2[(0, 3, 6, 9), :2], np.zeros((4, 1)))) + pos
        water.vertex().assign(vert3)
        water.polygon().assign([(0, 2, 1), (0, 3, 2)])
        water.header()['material'] = {'diffuse': [0.5, 0.6, 1., 0.7],
                                      'face_culling': 0}

        return {'etiage_line': para,
                'etiage_wall_tri': mesh,
                'etiage_water_tri': water}


    def make_lily_model(self, xml):
        cm = CataMapTo2DMap()
        protos = cm.find_protos(xml)
        if not protos:
            return
        lproto = protos['label'].get('lys')
        if lproto is None:
            print('No proto for lys')
            return
        self.main_group = 'lys'
        lily_l = aims.AimsTimeSurface_2()
        for child in lproto['element']:
            aims.SurfaceManip.meshMerge(
                lily_l, self.read_path(child,
                                         self.proto_scale * lproto['trans']))
        lily_up_l, lily_w = self.extrude(lily_l, 1.)
        lily_bk = self.tesselate(lily_l)
        lily_up = self.tesselate(lily_up_l)
        aims.SurfaceManip.invertSurfacePolygons(lily_w)
        lily_w.updateNormals()
        aims.SurfaceManip.invertSurfacePolygons(lily_bk)
        lily_bk.updateNormals()
        aims.SurfaceManip.meshMerge(lily_w, lily_bk)
        aims.SurfaceManip.meshMerge(lily_w, lily_up)
        vert = np.asarray(lily_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        bbmax = aims.Point3df(np.max(vert, axis=0))
        center = (bbmin + bbmax) / 2
        vert -= center
        lily_w.vertex().assign(vert)
        q = aims.Quaternion()
        q.fromAxis([1., 0., 0.], -np.pi / 2)
        tr = aims.AffineTransformation3d(q)
        aims.SurfaceManip.meshTransform(lily_w, tr)
        vert = np.asarray(lily_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        vert += [0., 0., 1.5 - bbmin[2]]
        lily_w.vertex().assign(vert)
        return lily_w


    def make_large_sign_model(self, xml):
        cm = CataMapTo2DMap()
        protos = cm.find_protos(xml)
        if not protos:
            return
        lproto = protos['label'].get('grande_plaque')
        if lproto is None:
            print('No proto for grande_plaque')
            return
        self.main_group = 'grande_plaque'
        lily_l = aims.AimsTimeSurface_2()
        todo = list(lproto['element'])
        while todo:
            child = todo.pop(0)
            if child.tag.endswith('}g'):
                todo += list(child)
                continue
            if child.tag.endswith('}text'):
                continue
            aims.SurfaceManip.meshMerge(
                lily_l, self.read_path(child,
                                         self.proto_scale * lproto['trans']))
        lily_up_l, lily_w = self.extrude(lily_l, 1.)
        lily_bk = self.tesselate(lily_l)
        lily_up = self.tesselate(lily_up_l)
        aims.SurfaceManip.invertSurfacePolygons(lily_w)
        lily_w.updateNormals()
        aims.SurfaceManip.invertSurfacePolygons(lily_bk)
        lily_bk.updateNormals()
        aims.SurfaceManip.meshMerge(lily_w, lily_bk)
        aims.SurfaceManip.meshMerge(lily_w, lily_up)
        vert = np.asarray(lily_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        bbmax = aims.Point3df(np.max(vert, axis=0))
        center = (bbmin + bbmax) / 2
        vert -= center
        lily_w.vertex().assign(vert)
        q = aims.Quaternion()
        q.fromAxis([1., 0., 0.], -np.pi / 2)
        tr = aims.AffineTransformation3d(q)
        aims.SurfaceManip.meshTransform(lily_w, tr)
        vert = np.asarray(lily_w.vertex())
        bbmin = aims.Point3df(np.min(vert, axis=0))
        vert += [0., 0., 1.5 - bbmin[2]]
        lily_w.vertex().assign(vert)
        return lily_w


    def make_stair_symbol_model(self):
        return self.make_spiral_stair([0, 0], 1., 0., 1.5)


    def make_sounds_marker_model(self):
        mesh = aims.SurfaceGenerator.icosphere((0, 0, 2.5), 0.5, 80)
        cone = aims.SurfaceGenerator.cone((0, 0, 2.5), (1.3, 0., 2.7), 0.5, 12,
                                          False, True)
        aims.SurfaceManip.meshMerge(mesh, cone)
        mesh.header()['material'] = {'diffuse': [.8, 0.6, 0., 1.]}
        return mesh


    def make_photos_marker_model(self):
        mesh = aims.SurfaceGenerator.icosphere((0, 0, 2.5), 0.5, 80)
        cone = aims.SurfaceGenerator.cone((0, 0, 1.), (0, 0, 2.5), 0.15, 6,
                                          False, True)
        aims.SurfaceManip.meshMerge(mesh, cone)
        mesh.header()['material'] = {'diffuse': [1., 0., 0., 1.]}
        return mesh


    def save_mesh_dict(self, meshes, dirname, mesh_format='.mesh',
                       mesh_wf_format='.mesh', json_filename=None,
                       map2d_filename=None):
        # filter out wells definitions
        def mod_key(key, item):
            if isinstance(item, aims.AimsTimeSurface_3):
                if not key.endswith('_tri'):
                    key += '_tri'
            if isinstance(item, aims.AimsTimeSurface_2):
                if not key.endswith('_line'):
                    key += '_line'
            return key

        mdict = dict([(mod_key(k, v), v) for k, v in meshes.items()
                      if not k.endswith('_wells')])
        summary = super(CataSvgToMesh, self).save_mesh_dict(
            mdict, dirname,  mesh_format=mesh_format,
            mesh_wf_format=mesh_wf_format)

        # output JSON dict
        json_obj = collections.OrderedDict()

        # date / version
        p = os.path.dirname(os.path.realpath(__file__))
        sys.path.insert(0, p)
        try:
            import build_version
            imp.reload(build_version)
            # increment build version
            build_version.build_version += 1
            # save modified build version
            ver_file = build_version.__file__
            if ver_file.endswith('.pyc'):
                ver_file = ver_file[:-1]  # get a .py
            try:
                print('rewrite version file:', ver_file)
                open(ver_file, 'w').write(
                    'build_version = %d\n' % build_version.build_version)
            except IOError as e:
                print(e)
                pass  # oh OK I can't write there.
        finally:
            del sys.path[0]
        json_obj['version'] = build_version.build_version
        title = getattr(self, 'title', None)
        if title:
            json_obj['title'] = title

        d = datetime.date.today()
        json_obj['date'] = '%04d-%02d-%02d' % d.timetuple()[:3]
        if map2d_filename:
            json_obj['map'] = map2d_filename


        # build 3D layers:
        # 0: main_corridors
        # 1: unreachable
        # 2: text
        # 3: parcels
        # 4: oss_off
        # 5: tech
        # 6: limestone
        # 7: legend

        categories = [
            "Couloirs",
            "Inaccessible",
            "Textes",
            "Parcelles",
            "Ossuaire officiel",
            "Galeries Tech.",
            "Remblai",
            "Calcaire",
            "Légende",
            "Surface",
        ]
        json_obj['categories'] = categories
        def_categories = [
        ]
        json_obj['default_categories'] = def_categories
        used_layers = set()

        # print('summary:', summary, '\n')
        if 'meshes' in summary:
            jmeshes = []
            pmeshes = []
            for filename, mesh in six.iteritems(summary['meshes']):
                filename = os.path.basename(filename)
                group = mesh
                # print('mesh:', mesh)
                if group.endswith('_tri'):
                    group = group[:-4]
                elif group.endswith('_line'):
                    group = group[:-5]
                props = self.group_properties.get(group)
                if not props:
                    print('no props for mesh:', group, filename)
                if '.' in filename:  # remove extension
                    filename = '.'.join(filename.split('.')[:-1])
                layer = 0
                if 'profondeur' in filename or 'bord' in filename:
                    continue  # skip
                if props and props.category:
                    if props.category not in categories:
                        categories.append(props.category)
                    layer = categories.index(props.category)
                else:
                    # old way, specific
                    if (props and props.level == 'tech') \
                            or '_tech_' in filename \
                            or 'techniques' in filename \
                            or 'gtech' in filename or 'ebauches' in filename \
                            or 'metro' in filename:
                        layer = 5
                    elif (props and props.arrow) \
                            or filename.startswith('plaques ') \
                            or u' flèches' in filename \
                            or filename.startswith('etiage_'):
                        layer = 2
                    elif 'parcelles' in filename:
                        layer = 3
                    elif 'oss off' in filename:
                        layer = 4
                    elif (props and props.inaccessible) \
                            or filename.startswith('anciennes ') \
                            or 'anciennes galeries' in filename \
                            or filename.startswith('aqueduc') \
                            or filename.startswith('ex-') \
                            or ' inaccessibles' in filename:
                        layer = 1
                    elif filename.startswith('remblai'):
                        layer = 6
                    elif filename.startswith('calcaire'):
                        layer = 7
                    elif u'légende' in filename \
                            or 'grandes plaques' in filename:
                        layer = 8
                    elif 'grille surface' in filename:
                        layer = 9
                # print('mesh:', layer, ':', filename, props)
                size = os.stat(os.path.join(dirname,
                                            filename + '.obj')).st_size
                # hash
                md5 = hashlib.md5(open(os.path.join(dirname,
                                                    filename + '.obj'),
                                       'rb').read()).hexdigest()
                if 'private' in filename or (props and props.private):
                    pmeshes.append([layer, filename, size, md5])
                else:
                    jmeshes.append([layer, filename, size, md5])

                used_layers.add(layer)

            json_obj['meshes'] = sorted(jmeshes)
            json_obj['meshes_private'] = sorted(pmeshes)

        new_nums = {l: i for i, l in enumerate(used_layers)}
        categories = [c for i, c in enumerate(categories) if i in used_layers]
        # re-number all items
        for item in jmeshes:
            item[0] = new_nums[item[0]]
        for item in pmeshes:
            item[0] = new_nums[item[0]]

        json_obj['categories'] = categories
        if 'Couloirs' in categories:
            def_categories.append('Couloirs')
        if 'Ossuaire officiel' in categories:
            def_categories.append('Ossuaire officiel')

        # texts
        # TODO: separate them in different layers (hidden...)
        if 'text_fnames' in summary:
            json_obj['text_fnames'] \
                = sorted([os.path.basename(f)
                          for f in summary['text_fnames'].keys()
                          if 'private' not in f])
            json_obj['text_fnames_private'] \
                = sorted([os.path.basename(f)
                          for f in summary['text_fnames'].keys()
                          if 'private' in f])
            texts = []
            json_obj['texts'] = texts
            for fname in json_obj['text_fnames']:
                size = os.stat(os.path.join(dirname, fname)).st_size
                # hash
                md5 = hashlib.md5(open(os.path.join(dirname, fname),
                                       'rb').read()).hexdigest()
                texts.append([0, fname, size, md5])
            texts = []
            json_obj['texts_private'] = texts
            for fname in json_obj['text_fnames_private']:
                size = os.stat(os.path.join(dirname, fname)).st_size
                # hash
                md5 = hashlib.md5(open(os.path.join(dirname, fname),
                                       'rb').read()).hexdigest()
                texts.append([0, fname, size, md5])

        # sounds
        if self.sounds:
            json_obj['sounds'] = self.sounds
        if self.sounds_private:
            json_obj['sounds_private'] = self.sounds_private

        # photos
        if self.photos:
            json_obj['photos'] = self.photos
        if self.photos_private:
            json_obj['photos_private'] = self.photos_private

        if json_filename is not None:
            if six.PY3:
                json.dump(json_obj, open(json_filename, 'w'), indent=4,
                        sort_keys=False, ensure_ascii=False)
            else:
                json.dump(json_obj, open(json_filename, 'w'), indent=4,
                        sort_keys=False, ensure_ascii=False, encoding='utf-8')

        return json_obj



class CataMapTo2DMap(svg_to_mesh.SvgToMesh):
    '''
    Process XML tree to build modified 2D maps
    '''

    proto_scale = np.array([[0.5, 0,   0],
                            [0,   0.5, 0],
                            [0,   0,   1]])

    def __init__(self, concat_mesh='bygroup'):
        super(CataMapTo2DMap, self).__init__(concat_mesh)

    def find_protos(self, xml):
        root = xml.getroot()
        trans = np.matrix(np.eye(3))

        trans2 = root.get('transform')
        if trans2 is not None:
            transm = self.get_transform(trans2)
            if trans is None:
                trans = transm
            else:
                trans = trans * transm

        symbols = [x for x in root
                   if x.get(
                      '{http://www.inkscape.org/namespaces/inkscape}label')
                      == u'légende'
                      or x.get('legend') in ('1', 'True', 'true', 'TRUE')]
        if symbols:
            symbols = symbols[0]
        else:
            return
        trans2 = symbols.get('transform')
        if trans2 is not None:
            transm = self.get_transform(trans2)
            if trans is None:
                trans = transm
            else:
                trans = trans * transm
        trans = self.proto_scale * trans

        labels = {}
        ids = {}
        #rep_child = ['PSh', 'sans', 'PS sans', 'PSh sans', 'PS', 'P ossements',
                      #u'échelle', u'\xc3\xa9chelle', 'colim', 'PE', ]
        rep_child = []
        repl_map = {'id': ids, 'label': labels}
        for child in symbols:
            eid = child.get('id')
            ptype = None
            if eid and eid.endswith('_proto'):
                ptype = eid[:-6]
                plabel = 'id'
                pmap = ids
                # exception case: if label is the same without _proto
                if child.get('label') == ptype:
                    plabel = 'label'
                    pmap = labels
            else:
                label = child.get('label')
                if label and label.endswith('_proto'):
                    ptype = label[:-6]
                    plabel = 'label'
                    pmap = labels
            if ptype:
                element = copy.deepcopy(child)
                element.set(plabel, ptype)
                item = {'element': element}
                bbox = self.boundingbox(child, trans)
                item['boundingbox'] = bbox
                item['center'] = ((bbox[0][0] + bbox[1][0]) / 2,
                                  (bbox[0][1] + bbox[1][1]) / 2)
                item['trans'] = trans
                replace_children = child.get('replace_children')
                if replace_children:
                    if replace_children in ('1', 'True', 'true', 'TRUE'):
                        replace_children = True
                    else:
                        replace_children = False
                elif ptype in rep_child:
                    replace_children = True
                if replace_children:
                    item['children'] = True
                pmap[ptype] = item

        return repl_map


    def transform_inf_level(self, xml):
        todo = [xml.getroot()]

        while todo:
            element = todo.pop(0)
            map_trans = element.get('map_transform')
            if map_trans is not None:
                trans = element.get('transform')
                if trans is None:
                    trans = map_trans
                else:
                    trans = map_trans + ' ' + trans
                element.set('transform', trans)

            added = element[:]
            todo = added + todo

    def shadow1(self, filter_id):
        f = ET.Element('{http://www.w3.org/2000/svg}filter')
        f.set('{http://www.inkscape.org/namespaces/inkscape}label',
              'Shadow')
        f.set('style', 'color-interpolation-filters:sRGB;')
        f.set('id', filter_id)

        f = ET.Element('{http://www.w3.org/2000/svg}filter')
        f.set('{http://www.inkscape.org/namespaces/inkscape}label',
              'Drop Shadow')
        f.set('style', 'color-interpolation-filters:sRGB;')
        f.set('id', 'filter14930')

        c = ET.Element('{http://www.w3.org/2000/svg}feFlood')
        c.set('result', 'flood')
        c.set('id', 'feFlood14920')
        c.set('flood-opacity', '0.498039')
        c.set('flood-color', 'rgb(0,0,0)')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'out')
        c.set('id', 'feComposite14922')
        c.set('result', 'composite1')
        c.set('in2', 'SourceGraphic')
        c.set('in', 'flood')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feGaussianBlur')
        c.set('id', 'feGaussianBlur14924')
        c.set('stdDeviation', '0.3')
        c.set('result', 'blur')
        c.set('in', 'composite1')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feOffset')
        c.set('id', 'feOffset14926')
        c.set('result', 'offset')
        c.set('dx', '0.3')
        c.set('dy', '-0.3')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'atop')
        c.set('id', 'feComposite14928')
        c.set('result', 'fbSourceGraphic')
        c.set('in2', 'SourceGraphic')
        c.set('in', 'offset')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feColorMatrix')
        c.set('id', 'feColorMatrix14932')
        c.set('values', '0 0 0 -1 0 0 0 0 -1 0 0 0 0 -1 0 0 0 0 1 0')
        c.set('result', 'fbSourceGraphicAlpha')
        c.set('in', 'fbSourceGraphic')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feFlood')
        c.set('result', 'flood')
        c.set('flood-color', 'rgb(0,0,0)')
        c.set('in', 'fbSourceGraphic')
        c.set('id', 'feFlood14934')
        c.set('flood-opacity', '0.498039')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'in')
        c.set('result', 'composite1')
        c.set('id', 'feComposite14936')
        c.set('in2', 'fbSourceGraphic')
        c.set('in', 'flood')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feGaussianBlur')
        c.set('result', 'blur')
        c.set('stdDeviation', '0.4')
        c.set('id', 'feGaussianBlur14938')
        c.set('in', 'composite1')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feOffset')
        c.set('result', 'offset')
        c.set('id', 'feOffset14940')
        c.set('dx', '-0.4')
        c.set('dy', '0.4')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'over')
        c.set('result', 'composite2')
        c.set('id', 'feComposite14942')
        c.set('in2', 'offset')
        c.set('in', 'fbSourceGraphic')
        f.append(c)

        return f

    def shadow2(self, filter_id):
        f = ET.Element('{http://www.w3.org/2000/svg}filter')
        f.set('{http://www.inkscape.org/namespaces/inkscape}label',
              'Shadow')
        f.set('style', 'color-interpolation-filters:sRGB;')
        f.set('id', filter_id)

        c = ET.Element('{http://www.w3.org/2000/svg}feFlood')
        c.set('result', 'flood')
        c.set('id', 'feFlood14920')
        c.set('flood-opacity', '0.7')
        c.set('flood-color', 'rgb(128,128,128)')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'in')
        c.set('id', 'feComposite14922')
        c.set('result', 'composite1')
        c.set('in2', 'SourceGraphic')
        c.set('in', 'flood')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feGaussianBlur')
        c.set('id', 'feGaussianBlur14924')
        c.set('stdDeviation', '0.3')
        c.set('result', 'blur')
        c.set('in', 'composite1')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feOffset')
        c.set('id', 'feOffset14926')
        c.set('result', 'offset')
        c.set('dx', '0.3')
        c.set('dy', '-0.3')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'over')
        c.set('id', 'feComposite14928')
        c.set('result', 'fbSourceGraphic')
        c.set('in2', 'SourceGraphic')
        c.set('in', 'offset')
        f.append(c)

        return f

    def halo1(self, filter_id, scale):
        f = ET.Element('{http://www.w3.org/2000/svg}filter')
        f.set('{http://www.inkscape.org/namespaces/inkscape}label',
              'Shadow')
        f.set('style', 'color-interpolation-filters:sRGB;')
        f.set('id', filter_id)

        c = ET.Element('{http://www.w3.org/2000/svg}feMorphology')
        c.set('result', 'dilate1')
        c.set('id', 'feMorphology44406')
        c.set('radius', '%f' % (0.25 / scale))
        c.set('operator', 'dilate')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feFlood')
        c.set('result', 'flood')
        c.set('id', 'feFlood14920')
        c.set('flood-opacity', '0.6')
        c.set('flood-color', 'rgb(135,128,128)')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'in')
        c.set('id', 'feComposite14922')
        c.set('result', 'composite1')
        c.set('in2', 'dilate1')
        c.set('in', 'flood')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feGaussianBlur')
        c.set('id', 'feGaussianBlur14924')
        c.set('stdDeviation', '%f' % (0.2 / scale))
        c.set('result', 'blur')
        c.set('in', 'composite1')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feFlood')
        c.set('result', 'flood2')
        c.set('id', 'feFlood14921')
        c.set('flood-opacity', '1.')
        c.set('flood-color', 'rgb(0,0,0)')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'in')
        c.set('id', 'feComposite14929')
        c.set('result', 'composite2')
        c.set('in', 'flood2')
        c.set('in2', 'SourceGraphic')
        f.append(c)
        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'over')
        c.set('id', 'feComposite14930')
        c.set('result', 'composite3')
        c.set('in2', 'blur')
        c.set('in', 'composite2')
        f.append(c)

        c = ET.Element('{http://www.w3.org/2000/svg}feComposite')
        c.set('operator', 'over')
        c.set('id', 'feComposite14928')
        c.set('result', 'fbSourceGraphic')
        c.set('in', 'SourceGraphic')
        c.set('in2', 'compisite3')
        f.append(c)

        return f


    def make_shadow_filter(self, xml, scale=1.):
        if not hasattr(self, 'shadow_filters'):
            self.shadow_filters = {}

        scale = round(scale * 10)

        f = self.shadow_filters.get(scale)
        if f:
            return f

        f = self.halo1('filter14930_%d' % scale, scale / 10)

        defs = [l for l in xml.getroot()
                if l.tag == '{http://www.w3.org/2000/svg}defs'][0]
        defs.append(f)
        return f


    def add_shadow(self, layer, filter):
        child = layer
        if True:
        #for child in layer:
            style = child.get('style')
            if style is None:
                style = ' '
            else:
                style += '; '
            style += 'filter:url(#%s)' % filter
            child.set('style', style)


    def add_shadows(self, xml):
        if inkscape_version()[:2] == [1, 1]:
            # inkscape 1.1 has a problem with filters, it is extemely slow
            # and consumes memory. Rendering with inkscape 1.0 is 3 minutes for
            # a 360dpi map, and 185 minutes with inkscape 1.1
            return

        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if not (label in self.removed_labels \
                    or label.startswith('profondeurs') \
                    or label.startswith('background_bitm')):
                style = self.get_style(layer)
                style['display'] = 'inline'
                self.set_style(layer, style)
                shadow = layer.get('shadow')
                if shadow is not None and shadow not in ('0', 'false', 'False', 'FALSE'):
                    shadow = True
                else:
                    shadow = False
                if shadow or label in (
                        'galeries inaccessibles inf',
                        'anciennes galeries inf',
                        'galeries inf',
                        'galeries inf private',
                        'anciennes galeries big',
                        'galeries inaccessibles', 'galeries big PARIS',
                        'galeries',
                        'galeries private',
                        'galeries big 2',
                        'galeries big sud',
                        'galeries techniques',
                        'galeries inf private'):
                    trans = self.get_transform(layer.get('transform'))
                    scale = (trans[0,0] + trans[1,1]) / 2.
                    shadow = self.make_shadow_filter(xml, scale).get('id')
                    self.add_shadow(layer, shadow)


    def remove_shadows(self, xml):
        defs = [l for l in xml.getroot()
                if l.tag == '{http://www.w3.org/2000/svg}defs'][0]
        if defs[-1].tag == '{http://www.w3.org/2000/svg}filter':
            del defs[-1]


    @staticmethod
    def roman(number):
        onum = ''
        r = number % 1000
        c = int(r / 100)
        syms = (('M', '?'), ('C', 'D'), ('X', 'L'), ('I', 'V'))
        div = 1000
        r = number
        for i in range(len(syms)):
            c = int(r / div)
            if c == 9:
                onum += syms[i][0] + syms[i - 1][0]
            elif c >= 5:
                onum += syms[i][1] + syms[i][0] * (c - 5)
            elif c == 4:
                onum += syms[i][0] + syms[i][1]
            else:
                onum += syms[i][0] * c
            r = r % div
            div = int(div / 10)
        return onum


    @staticmethod
    def formatted_date(date):
        months = (u'', u'Janvier', u'Février', u'Mars', u'Avril', u'Mai',
                  u'Juin', u'Juillet', u'Août', u'Septembre', u'Octobre',
                  u'Novembre', u'Décembre')
        return '%d %s %s' % (date.day, months[date.month],
                             CataMapTo2DMap.roman(date.year))


    @staticmethod
    def in_region(pt, region, bbox, verbose=False):
        x = pt[0]
        y = pt[1]
        # bbox is used first to quickly discard points
        if bbox is not None and (x < bbox[0][0] or x > bbox[1][0]
                                 or y < bbox[0][1] or y > bbox[1][1]):
            return False
        if region is None:
            return True
        # then check clip region polygon more thoroughfully
        if verbose:
            print('in_region check polygon:', pt, bbox)
        lines = region.polygon()
        vert = region.vertex()
        left_pts = 0
        for l in lines:
            # intersects with horizontal line on pt
            intersect = ((vert[l[0]][1] - y) * (vert[l[1]][1] - y) <= 0)
            if not intersect:
                continue
            # intersect abscissa
            v = vert[l[1]] - vert[l[0]]
            h = (y - vert[l[0]][1]) / v[1]
            xi = vert[l[0]][0] + h * v[0]
            if xi == x:
                # just on border: in
                if verbose:
                    print('__in__')
                return True
            elif xi < x:
                left_pts += 1
        # odd nb of intersections on the left (and right): in
        # even: out
        if verbose:
            print('__', (left_pts & 1 == 1), '__', left_pts)
        return (left_pts & 1 == 1)


    @staticmethod
    def box_in_region(box, region, bbox, verbose=False):
        ''' check if a box is totally inside a region, or totally outside, or
        intersecting

        Warning: if 4 corners are inside, the test says inside, whereas it is not always true for a non-convex clip polygon

        Returns
        -------
        1: inside
        0: intersecting
        -1: outside
        '''
        pts = [(box[0][0], box[0][1]),
               (box[0][0], box[1][1]),
               (box[1][0], box[0][1]),
               (box[1][0], box[1][1])]
        nin = sum([int(CataMapTo2DMap.in_region(pt, region, bbox))
                   for pt in pts])
        if verbose:
            print('box_in_region:', box, bbox, nin)
        if nin == 0:
            return -1
        elif nin == 4:
            return 1
        else:
            return 0


    def clip_and_scale(self, layer, target_layer, trans, region, region_bbox,
                       src_trans=None, with_copy=False, verbose=False):
        if verbose:
            print('clip_and_scale:', layer.tag, layer.get('id'), 'into:',
                  target_layer.get('id'))
        if not with_copy:
            target_layer = layer
        trans2 = layer.get('transform')
        if trans2 is not None:
            trans2 = self.get_transform(trans2)
            if src_trans is None:
                src_trans = trans2
            else:
                src_trans = src_trans * trans2
        to_remove = []
        copied = []
        #if layer.get('id') == 'layer31':
            #verbose = True
        for element in layer:
            if with_copy:
                element = copy.deepcopy(element)
                target_layer.append(element)
                copied.append(element)
            bbox = self.boundingbox(element, src_trans)
            #print('bbox:', bbox)
            if bbox != [None, None]:
                in_out = self.box_in_region(bbox, region, region_bbox,
                                            verbose=verbose)
                if in_out <= 0:
                    #print('out:', element.tag, element.get('id'))
                    #to_remove.append(element)
                #elif in_out == 0:
                    # intesect
                    if verbose:
                        print('intersect:', element.tag, element.get('id'))
                    if element.tag.endswith('}g'):
                        # group: look inside
                        trans2 = element.get('transform')
                        if trans2 is not None:
                            trans2 = self.get_transform(trans2)
                            if src_trans is not None:
                                trans2 = src_trans * trans2
                        else:
                            trans2 = src_trans
                        self.clip_and_scale(element, element, trans, region,
                                            region_bbox, src_trans,
                                            verbose=verbose)
                    else:
                        # real object intersect: reject
                        to_remove.append(element)
                elif verbose:
                    print('** in **:', element.tag, element.get('id'))
            else:
                # text ? or other object with x, y attributes
                x = element.get('x')
                y = element.get('y')
                if x is None or y is None:
                    # no: something else: skip
                    to_remove.append(element)
                    continue
                x = float(x)
                y = float(y)
                trans2 = element.get('transform')
                if trans2 is None:
                    trans2 = src_trans
                else:
                    trans2 = self.get_transform(trans2)
                    if src_trans is not None:
                        trans2 = src_trans * trans2
                if trans2 is not None:
                    p = trans2 * np.expand_dims([x, y, 1.], 1)
                    x, y = p[0, 0], p[1, 0]
                #print('tag:', element.tag, x, y)
                if not self.in_region((x, y), region, region_bbox,
                                      verbose=verbose):
                    #print('remove from:', target_layer, target_layer.get('id'))
                    to_remove.append(element)
                elif verbose:
                    print('** in **:', element.tag, element.get('id'))
        for element in to_remove:
            target_layer.remove(element)
        if trans is not None:
            init_tr = layer.get('transform')
            if init_tr is not None:
                init_tr = self.get_transform(init_tr)
                trans = trans * init_tr
            for element in copied:
                trans2 = element.get('transform')
                if trans2 is not None:
                    trans2 = trans * self.get_transform(trans2)
                else:
                    trans2 = trans
                element.set('transform', self.to_transform(trans2))


    def enlarge_region(self, src_xml, xml, region, keep_private=True):
        layer_label = u'masque %s' % region
        target_layer_label = u'agrandissement %s' % region
        mask_layer = [
            x for x in src_xml.getroot()
            if x.get('{http://www.inkscape.org/namespaces/inkscape}label')
                == layer_label]
        if mask_layer:
            mask_layer = mask_layer[0]
        else:
            return  # this region doesn't exist in the map
        target_layer = [
            x for x in xml.getroot()
            if x.get('{http://www.inkscape.org/namespaces/inkscape}label')
                == target_layer_label][0]
        target_trans = self.get_transform(target_layer.get('transform'))
        target_rect = target_layer[0]
        rect = self.boundingbox(target_rect, target_trans)
        #rect = [float(target_rect.get('x')),
                #float(target_rect.get('y')),
                #float(target_rect.get('width')),
                #float(target_rect.get('height'))]
        #rect[2] += rect[0]
        #rect[3] += rect[1]
        #print('target rect:', rect)
        # calculate transform
        trans = self.get_transform(mask_layer.get('transform'))
        in_rect = self.boundingbox(mask_layer[0], trans)
        #print('in_rect:', in_rect)
        transl = [rect[0][0] - in_rect[0][0], rect[1][1] - in_rect[1][1]]
        #print('transl:', transl)
        enl_tr = np.matrix(np.eye(3))
        scl1 = (rect[1][0] - rect[0][0]) / (in_rect[1][0] - in_rect[0][0])
        scl2 = (rect[1][1] - rect[0][1]) / (in_rect[1][1] - in_rect[0][1])
        #print('scales:', scl1, scl2)
        scl = min((scl1, scl2))
        enl_tr[0, 0] = scl
        enl_tr[1, 1] = scl
        #enl_tr[:2, 2] = np.expand_dims(transl[:2], 1) * scl
        enl_tr[:2, 2] \
            = (np.expand_dims([rect[0][0], rect[1][1], 1.], 1)
               - enl_tr * np.expand_dims([in_rect[0][0],
                                          in_rect[1][1], 1.], 1))[:2,]
        # get back into target layer coords
        enl_tr = np.linalg.inv(target_trans) * enl_tr
        #print('enlarge_region:', region)
        #print('rect:', rect)
        #print('in_rect:', in_rect)
        #print('enl_tr:', enl_tr)
        #print('target_trans:', target_trans)

        # replace rect by actual data
        target_layer.remove(target_rect)
        #if region == 'vdg':
            ## special case VDG: take specific corridors
            #corridors_layer = [
                #x for x in xml.getroot()
                #if x.get('{http://www.inkscape.org/namespaces/inkscape}label')
                    #== 'galeries big PARIS'][0]
            #tr = self.get_transform(corridors_layer.get('transform'))
            #group = [x for x in corridors_layer if x.tag.endswith('}g')][0]
            #tr *= self.get_transform(group.get('transform'))
            #g2 = [x for x in group if x.get('id') == 'Z + VdG'][0]
            ## tr *= tr.get_transform(g2.get('transform'))
            #new_g = copy.deepcopy(g2)
            ##print('current tr:', tr)
            ##print('final tr:', enl_tr * tr)
            #new_g.set('transform', self.to_transform(enl_tr * tr))
            #target_layer.append(new_g)

        clip_region = self.read_path(mask_layer[0], trans)

        for layer in xml.getroot():
            if not layer.tag.endswith('}g'):
                continue
            style = layer.get('style')
            if style is not None and 'display:none' in style:
                continue
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None \
                    or label in ('parcelles', ) \
                    or label.startswith('masque ') \
                    or label.startswith('agrandissement ') \
                    or label.startswith('bord '):
                continue
            self.clip_and_scale(layer, target_layer, enl_tr, clip_region,
                                in_rect, None, with_copy=True)
        #print('in_rect:', in_rect)
        #print(np.asarray(clip_region.vertex()))


    def replace_filter_element(self, xml):
        #if not self.keep_private and xml.get('level') in ('tech', ):
        if not self.keep_private:
            if xml.get('level') in ('tech', ):
                return None
        return xml


    def do_remove_layers(self, xml):
        to_remove = []
        labels = []
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label in self.removed_labels \
                    or layer.get('hidden') in ('true', '1', 1, 'True'):
                to_remove.append(layer)
                labels.append(label)
        print('removing layers:', labels)
        for layer in to_remove:
            xml.getroot().remove(layer)

    def remove_selected_layers(self, xml):
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue

            non_visibility = layer.get('non_visibility')
            if non_visibility:
                if non_visibility.strip().startswith('['):
                    non_visibility = json.loads(non_visibility)
                else:
                    non_visibility = [non_visibility]
                if self.map_name in non_visibility:
                    self.removed_labels.add(label)
                    continue

            visibility = layer.get('visibility')
            if visibility is None:
                continue
            elif visibility.strip().startswith('['):
                visibility = json.loads(visibility)
            else:
                if visibility == 'private':  # old style
                    # exception, here 'private' is not a map type name but a
                    # variant (used in private, igc_private maps etc). It is
                    # filtered by remove_private(), and it is better to specify
                    # the tag private: true.
                    continue
                visibility = [visibility]
            if self.map_name not in visibility:
                self.removed_labels.add(label)

    def remove_wip(self, xml):
        self.removed_labels.update(
            ('a_verifier', 'indications_big_2010', 'planches',
             'calcaire 2010',
             'work done calc', 'galeries techniques despe',
             u'à vérifier', ))
        self.do_remove_layers(xml)


    def remove_south(self, xml):
        self.removed_labels.update(
            ('galeries_big_sud',))
        self.do_remove_layers(xml)


    def remove_background(self, xml):
        self.removed_labels.update(('couleur_fond', 'couleur_fond sud',))
        self.do_remove_layers(xml)


    def remove_private(self, xml):
        priv_labels = ['inscriptions', 'inscriptions conso',
                        'inscriptions inaccessibles',
                        u'inscriptions flèches',
                        u'inscriptions flèches inaccessibles',
                        u'inscriptions conso flèches',
                        u'maçonneries private', 'private', 'calcaire 2010',
                        'work done calc']
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if ItemProperties.is_true(layer.get('private')) \
                    or layer.get('visibility') == 'private' \
                    or label in priv_labels \
                    or label.endswith(' private') \
                    or 'tech' in label:
                self.removed_labels.add(label)
        self.keep_private = False
        self.remove_wip(xml)

        for layer in xml.getroot():
            print('filter private in', layer.get('{http://www.inkscape.org/namespaces/inkscape}label'))
            todo = [(layer, element) for element in layer]
            print('todo:', len(todo))
            while todo:
                parent, element = todo.pop(0)
                if element.get('visibility') == 'private' \
                        or ItemProperties.is_true(element.get('private')):
                    print('remove:', element)
                    parent.remove(element)
                else:
                    todo += [(element, item) for item in element]
        
        
    def remove_gtech(self, xml):
        self.removed_labels.update(('ebauches', 'galeries techniques',
                                    'PS gtech', 'PSh gtech', 'PSh vers gtech',
                                    'symboles gtech', 'eau gtech',
                                    'raccords gtech 2D',
                                    'metro',
                                    u'curiosités flèches GTech',
                                    'curiosités GTech',
                                    u'échelle gtech',
                                    u'plaques de puits GTech',
                                    u'échelle vers gtech',
                                    u'plaques de puits GTech',
                                    'annotations metro',
        ))
        self.do_remove_layers(xml)


    def remove_calcaire(self, xml):
        self.removed_labels.update(('calcaire 2010', 'calcaire ciel ouvert', 
        'calcaire masse2', 'calcaire masse', 'calcaire med',
        'calcaire sup', 'calcaire inf', 'calcaire vdg',
        ))
        self.do_remove_layers(xml)

    def remove_igc(self, xml):
        self.removed_labels.update(('planches', 'planches fond', 'planches IGC',
        ))
        self.do_remove_layers(xml)

    def remove_non_aqueduc(self, xml):
        self.removed_labels.update(('légende', 'grandes plaques',
        ))
        self.do_remove_layers(xml)

    def remove_non_printable1(self, xml):
        self.removed_labels.update(
            ['masque bg', 'masques v1', u'd\xe9coupage',
             'chatieres old', 'photos',
             #'bord_sud', 'galeries big sud',
             u'légende_alt', 'sons', 'altitude', 'lambert93',
             'bord'])
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label.startswith('profondeurs') \
                    or label.startswith('background_bitm'):
                self.removed_labels.add(label)
        self.do_remove_layers(xml)


    def remove_non_printable1_main(self, xml):
        self.removed_labels.update(
            ['masque bg', 'masques v1', u'd\xe9coupage',
             'chatieres old', 'photos',
             'bord_sud', 'galeries big sud',
             u'légende_alt', 'sons', 'altitude', 'lambert93',])
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label.startswith('profondeurs') \
                    or label.startswith('background_bitm'):
                self.removed_labels.add(label)
        self.do_remove_layers(xml)


    def remove_non_printable1_pub(self, xml):
        self.removed_labels.update(
            ['masque bg', 'masques v1', u'd\xe9coupage',
             'chatieres old', 'photos',
             'bord_sud', 'bord', # 'galeries big sud',
             u'légende_alt', 'sons', 'altitude', 'lambert93',])
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label.startswith('profondeurs') \
                    or label.startswith('background_bitm'):
                self.removed_labels.add(label)
        self.do_remove_layers(xml)


    def remove_non_printable2(self, xml):
        self.removed_labels.update(
            ['galeries agrandissements',
             'masque vdg', u'masque cimetière',
             'masque plage'])
        self.do_remove_layers(xml)


    def remove_non_printable_igc_private(self, xml):
        self.removed_labels.update(
            ['masque bg', 'masques v1', u'd\xe9coupage',
             'chatieres old', 'photos',
             'bord',
             #'bord_sud', 'galeries big sud',
             u'légende_alt', 'sons', 'altitude', 'lambert93'])
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label.startswith('profondeurs') \
                    or label.startswith('background_bitm'):
                self.removed_labels.add(label)
        self.do_remove_layers(xml)


    def remove_limestone(self, xml):
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label.startswith('calcaire') or 'masses' in label:
                self.removed_labels.add(label)
        self.do_remove_layers(xml)


    def remove_zooms(self, xml):
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            if label.startswith('agrandissement'):
                self.removed_labels.add(label)
        self.do_remove_layers(xml)


    def remove_other(self, xml, *labels):
        self.removed_labels.update(labels)
        self.do_remove_layers(xml)


    def replace_symbols(self, xml):
        protos = self.find_protos(self.xml)
        self.replace_elements(xml, protos)


    def zoom_areas(self, xml):
        for region in ('vdg', u'cimetière', 'plage'):
            self.enlarge_region(self.xml, xml, region,
                                keep_private=self.keep_private)


    def set_date(self, xml):
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if (label and label.startswith(u'légende')) \
                    or layer.get('legend') in ('1', 'true', 'True', 'TRUE'):
                for child in layer:
                    if child.get('date') is not None:
                        # set date in appropriate field
                        d = datetime.date.today()
                        child[0].text = u'\xe9dition du %s' \
                          % self.formatted_date(d)


    def show_all(self, xml):
        for layer in xml.getroot():
            layer.set('style', 'display:inline')


    def recolor(self, xml, colorset='igc'):
        colorsets = {
            #'igc': {
                ##'galeries': {'bg': '#5dd400ff'},
                ##'galeries big sud': {'bg': '#5dd400ff'},
                ##'galeries private': {'bg': '#5dd400ff'},
                ##'galeries inf': {'bg': '#076552ff'},
                ##'galeries inf private': {'bg': '#076552ff'},
                ##'galeries techniques': {'bg': '#5c99d976',
                                        ##'fg': '#4f5eaaff'},
                ##'plaques de puits': {'bg': '#424242ff'},
                ##'plaques de puits inaccessibles': {'bg': '#424242ff'},
                ##'plaques de puits GTech': {'bg': '#424242ff'},
                ##'annotations': {'bg': '#424242ff'},
                ##'annotations metro': {'bg': '#424242ff'},
                ##'zones': {'bg': '#424242ff'},
                ##'rues sans plaques': {'bg': '#424242ff'},
                ##'rues inf': {'bg': '#3a3c68ff'},
                ##u'curiosités inf': {'bg': '#8c620dff'},
                ##u'curiosités vdg': {'bg': '#5b601fff'},
                ##u'curiosités vdg private': {'bg': '#5b601fff'},
                ##u'curiosités': {'bg': '#5b601fff'},
            #},
            #'bator': {
                ##'galeries': {'bg': '#ff9e00ff'},
                ##'galeries big sud': {'bg': '#ff9e00ff'},
                ##'galeries private': {'bg': '#ff9e00ff'},
                ##'galeries techniques': {'bg': '#ece84976',
                                        ##'fg': '#aa9f4fff'},
                ##'metro': {'bg': '#9bc06e64',
                          ##'fg': '#94be55ff'},
            #},
            #'black': {
                ##'couleur_fond': {'bg': '#000000ff'},
                ##'couleur_fond sud': {'bg': '#000000ff'},
                ##'galeries': {'bg': '#0f50ffff',
                             ##'fg': '#ffffffff',
                             ##'stroke-width': '0.2'},
                ##'galeries big sud': {'bg': '#0f50ffff',
                                     ##'fg': '#ffffffff'},
                ##'galeries private': {'bg': '#0f50ffff',
                                     ##'fg': '#ffffffff'},
                ##'galeries inf': {'bg': '#9abde7ff',
                                 ##'fg': '#ffffffff'},
                ##'galeries inf private': {'bg': '#9abde7ff',
                                         ##'fg': '#ffffffff'},
                ##'calcaire 2010': {'bg': '#50505000',
                                  ##'fg': '#60606000'},
                ##'calcaire ciel ouvert': {'bg': '#50505020',
                                         ##'fg': '#60606000'},
                ##'calcaire masse2': {'bg': '#000000ff',
                                    ##'fg': '#60606000'},
                ##'calcaire masse': {'bg': '#000000ff',
                                   ##'fg': '#60606000'},
                ##'calcaire med': {'bg': '#50505000',
                                 ##'fg': '#60606000'},
                ##'calcaire sup': {'bg': '#50505000',
                                 ##'fg': '#60606000'},
                ##'calcaire inf': {'bg': '#50505000',
                                 ##'fg': '#60606000'},
                ##'agrandissements fond': {'bg': '#01202bff',
                                 ##'fg': '#88b0caff'},
                ##'parcelles': {'fg': '#bee0e65d'},
                ##'salles v1': {'bg': '#c5c5c5ff'},
            #},
        }
        #for k, v in six.iteritems(colorsets):
            #print(k, v)
            #v['galeries big sud'] = v['galeries']
        colors = colorsets.setdefault(colorset, {})
        legend_layer = None
        for layer in xml.getroot():
            props = ItemProperties()
            props.fill_properties(layer)
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            print('recolor', label)

            todo = [(x, [props]) for x in layer]
            while todo:
                item, parents = todo.pop()
                props = ItemProperties()
                props.fill_properties(item, parents)
                if len(item) != 0:
                    todo += [(x, parents + [props]) for x in item]

                corridor_colors = CataSvgToMesh.get_alt_color_s(
                    props, colorset, conv=False)
                if not corridor_colors:
                    corridor_colors = colors.get(label)
                if not corridor_colors:
                    # print('skip recolor', label)
                    continue
                if label == u'légende':
                    legend_layer = layer
                # allow legend to match labels found in map
                # however all items with this label will be affected...
                #if label not in colors:
                    #colors[label] = corridor_colors
                bg = corridor_colors.get('bg')
                op = 1.
                fill_op = 1.
                if bg and len(bg) >= 7:
                    fill_op = float(eval('0x%s' % bg[-2:])) / 255.
                    bg = bg[:-2]
                fg = corridor_colors.get('fg')
                if fg and len(fg) >= 7:
                    op = float(eval('0x%s' % fg[-2:])) / 255.
                    fg = fg[:-2]

                style = self.get_style(item)
                if style:
                    if bg and 'fill' in style:
                        style['fill'] = bg
                    style['fill-opacity'] = str(fill_op)
                    if fg and 'stroke' in style:
                        style['stroke'] = fg
                    style['stroke-opacity'] = str(op)
                    self.set_style(item, style)
                    # allow to replace other style elements
                    for k, style_item in corridor_colors.items():
                        if k not in ('fg', 'bg'):
                            style[k] = style_item

        # recolor legend items
        if legend_layer:
            todo = legend_layer[:]
            while todo:
                item = todo.pop(0)
                if len(item) != 0:
                    todo += item[:]
                label = item.get('label')
                if not label:
                    continue
                corridor_colors = colors.get(label)
                if not corridor_colors:
                    continue
                style = self.get_style(item)
                if style:
                    bg = corridor_colors.get('bg')
                    fg = corridor_colors.get('fg')
                    op = 1.
                    fill_op = 1.
                    if bg and len(bg) >= 7:
                        fill_op = float(eval('0x%s' % bg[-2:])) / 255.
                        bg = bg[:-2]
                    if fg and len(fg) >= 7:
                        op = float(eval('0x%s' % fg[-2:])) / 255.
                        fg = fg[:-2]
                    if bg:
                        style['fill'] = bg
                        style['fill-opacity'] = str(fill_op)
                    if fg:
                        style['stroke'] = fg
                        style['stroke-opacity'] = str(op)
                    self.set_style(item, style)

    def list_colorsets(self, xml):
        colorsets = set()
        todo = [xml.getroot()]
        while todo:
            item = todo.pop()
            alt_col = item.get('alt_colors')
            if alt_col:
                try:
                    alt_col = json.loads(alt_col)
                except:
                    raise
                colorsets.update(alt_col.keys())
            label_alt_col = item.get('label_alt_colors')
            if label_alt_col:
                try:
                    label_alt_col = json.loads(label_alt_col)
                except:
                    raise
                for c in label_alt_col.values():
                    colorsets.update(c.keys())

            todo += item[:]

        print('available colorsets:')
        for col in sorted(colorsets):
            print('    %s' % col)
        print()
        return colorsets


    def split_layers(self, xml, style='default'):
        layer_setups = {
            'default': [
                ['a_verifier',
                 'bord_sud',
                 'indications_big_2010',
                 'salles vdg',
                 'salles vdg private',
                 'salles v1',
                 'salles inf',
                 'private',
                 'zones',
                 u'curiosités vdg private',
                 u'curiosités vdg',
                 u'curiosités private',
                 u'curiosités',
                 u'curiosités inf',
                 'historiques',
                 'rues vdg',
                 'rues email',
                 'rues v1 private',
                 'rues v1',
                 'rues inf petit',
                 'rues inf',
                 'rues sans plaques',
                 'annotations vdg',
                 'annotations',
                 'plaques de puits',
                 u'curiosités flèches dessus',
                 u'rues flèches dessus',
                 u'salles vdg flèches',
                 u'salles v1 flèches',
                 u'salles flèches private',
                 u'curiosités flèches private',
                 u'curiosités flèches',
                 u'historiques flèches',
                 u'rues v1 flèches private',
                 u'rues v1 flèches',
                ],
                ['inscriptions vdg',
                 'inscriptions conso',
                 'inscriptions',
                 u'plaques rues volées',
                 'symboles gtech',
                 'PSh gtech',
                 'PSh vers gtech',
                 u'échelle vers gtech',
                 u'échelle vers gtech private',
                 'eau gtech',
                 'ebauches',
                 'raccords gtech 2D',
                 'galeries techniques',
                 'galeries techniques despe',
                 'metro',
                 u'inscriptions flèches',
                 u'inscriptions conso flèches',
                ],
                ['symboles private',
                 'symboles',
                 'plaques rues',
                 'raccords plan 2D',
                 'sol-ciel',
                 'PSh',
                 'PS',
                 'PE',
                 'P ossements',
                 'escaliers',
                 'escaliers private',
                 'escaliers inaccessibles',
                 'escaliers anciennes galeries big',
                 'PS sans',
                 'PSh sans',
                 u'échelle',
                 'eau',
                 u'maçonneries',
                 u'maçonneries private',
                 'cuves',
                 'galeries private',
                 'galeries',
                 'galeries big sud',
                 'galeries inaccessibles',
                 'remblai epais',
                 'remblai leger',
                 'remblai epais inaccessibles',
                 'remblai leger inaccessibles',
                 'remblai epais inaccessibles inf',
                 'remblai leger inaccessibles inf',
                 'hagues',
                 'hagues effondrees',
                 'anciennes galeries big',
                 'cuves inf',
                 'symboles inf',
                 'galeries inf',
                 'anciennes galeries inf',
                 'galeries inaccessibles inf',
                 'chatieres private',
                 'chatieres v3',
                ],
                [
                 u'légende_alt',
                 u'légende',
                 u'découpage',
                 'profondeurs gtech',
                 'profondeurs galeries',
                 'profondeurs seine',
                 'profondeurs esc',
                 'profondeurs galeries_inf',
                 'profondeurs metro',
                 'masque vdg',
                 u'masque cimetière',
                 'masque plage',
                 'agrandissement vdg',
                 'agrandissement cimetière',
                 'agrandissement plage',
                 'agrandissement fond',
                 'calcaire 2010',
                 'calcaire limites',
                 'calcaire masse',
                 'calcaire masse2',
                 'calcaire ciel ouvert',
                 'calcaire sup',
                 'calcaire med',
                 'calcaire inf',
                 'calcaire vdg',
                 'parcelles',
                 'altitude',
                 'couleur_fond1',
                 'couleur_fond',
                 'couleur_fond sud',
                 'planches',
                 'planches fond',
                 'planches IGC',
                ],
            ]
        }
        common = set(['bord'])
        layers = layer_setups[style]
        maps = []
        root = xml.getroot()
        for i in range(len(layers)):
            mr = ET.Element(root.tag)
            m = ET.ElementTree(mr)
            for k, v in root.items():
                mr.set(k, v)
            maps.append(m)

        layer_num = 0
        for layer in root:
            to_all = False
            if layer.tag != '{http://www.w3.org/2000/svg}g':
                # common to all
                to_all = True
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            layer.set('layer_num', str(layer_num))
            layer_num += 1
            if label in common:
                to_all = True
            if to_all:
                for m in maps:
                    m.getroot().append(copy.deepcopy(layer))
                continue
            for i, lnames in enumerate(layers):
                if label in lnames:
                    maps[i].getroot().append(copy.deepcopy(layer))
                    break
            else:
                maps[-1].getroot().append(copy.deepcopy(layer))

        return maps


    def join_layers(self, xml_dummy, filename):
        pattern = filename.replace('.svg', '_%d.svg')

        ## clear xml
        #to_remove = []
        #labels = []
        #for layer in xml.getroot():
            #if layer.tag == '{http://www.w3.org/2000/svg}g':
                #to_remove.append(layer)
        #for layer in to_remove:
            #xml.getroot().remove(layer)

        i = 0

        while os.path.exists(pattern % i):
            filename = pattern % i
            print('adding', filename)
            mapi = self.read_xml(filename)
            i += 1
            if i == 1:
                xml = mapi
                self.xml = xml
                continue
            for layer in mapi.getroot():
                if layer.tag != '{http://www.w3.org/2000/svg}g':
                    continue
                layer_num = int(layer.get('layer_num'))
                # look where to insert it
                for j, xlayer in enumerate(xml.getroot()):
                    if xlayer.tag != '{http://www.w3.org/2000/svg}g':
                        continue
                    xlayer_num = int(xlayer.get('layer_num'))
                    if xlayer_num == layer_num:
                        # already here, do nothing
                        j = -1
                        break
                    elif xlayer_num > layer_num:
                        break
                if j >= 0:
                    xml.getroot().insert(j, layer)

        # now remove layer_num
        for layer in xml.getroot():
            if layer.get('layer_num'):
                del layer.attrib['layer_num']


    def layer_opacity(self, xml, label, opacity):
        print('set layer opacity:', label, opacity)
        for layer in xml.getroot():
            if layer.tag != '{http://www.w3.org/2000/svg}g':
                continue
            if layer.get(
                    '{http://www.inkscape.org/namespaces/inkscape}label') \
                        == label:
                print('found it.')
                style = self.get_style(layer)
                style['opacity'] = opacity
                self.set_style(layer, style)
                print('style:', layer.get('style'))
                break

    def find_clip_rect(self, xml, rect_def):
        for layer in xml.getroot():
            if layer.tag != '{http://www.w3.org/2000/svg}g':
                continue
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label == rect_def:
                return layer[0].get('id')
            for child in layer:
                if child.get('id') == rect_def \
                        or child.get('label') == rect_def:
                    return child.get('id')

    def ensure_clip_rect(self, out_xml, rect_id, in_xml):
        ''' if rect_id is not in out_xml, then take it from in_xml and copy it
        in a new layer un out_xml.
        '''
        if self.find_clip_rect(out_xml, rect_id):
            return  # OK
        elem = self.find_element(in_xml, rect_id)
        if not elem:
            raise ValueError('element not found: %s' % dims_or_rect)
        rect, trans = elem
        layer = ET.Element('{http://www.w3.org/2000/svg}g')
        out_xml.getroot().insert(0, layer)
        layer.set('{http://www.inkscape.org/namespaces/inkscape}label',
                  'clip_border')
        layer.set('{http://www.inkscape.org/namespaces/inkscape}groupmode',
                  'layer')
        layer.set('style', 'display:none')
        layer.set('id', 'clip_border')
        layer.append(copy.deepcopy(rect))
        layer[0].set('id', rect.get('id'))  # copy same id
        if trans is not None:
            self.set_transform(layer, trans)

    def build_2d_map(self, xml, keep_private=True, wip=False,
                     filters=[], map_name=None):
        all_filters = {
            'remove_private': self.remove_private,
            'remove_non_printable1': self.remove_non_printable1,
            'remove_non_printable2': self.remove_non_printable2,
            'remove_non_printable1_pub': self.remove_non_printable1_pub,
            'remove_non_printable1_main': self.remove_non_printable1_main,
            'remove_non_printable_igc_private':
                self.remove_non_printable_igc_private,
            'remove_non_printable': ['remove_non_printable1',
                                     'remove_non_printable2'],
            'remove_wip': self.remove_wip,
            'remove_south': self.remove_south,
            'remove_background': self.remove_background,
            'remove_limestone': self.remove_limestone,
            'remove_gtech': self.remove_gtech,
            'remove_non_aqueduc': self.remove_non_aqueduc,
            'remove_calcaire': self.remove_calcaire,
            'remove_igc': self.remove_igc,
            'remove_other': self.remove_other,
            'add_shadow': self.add_shadows,
            'shift_inf_level': self.transform_inf_level,
            'replace_symbols': self.replace_symbols,
            'recolor': self.recolor,
            'zooms': self.zoom_areas,
            'date': self.set_date,
            'show_all': self.show_all,
            'split_layers': self.split_layers,
            'join_layers': self.join_layers,
            'layer_opacity': self.layer_opacity,
            'remove_zooms': self.remove_zooms,
            'printable_map': ['remove_non_printable1', 'show_all',
                              #'add_shadow',
                              'shift_inf_level', 'replace_symbols', 'date',
                              'zooms', 'remove_non_printable2', 'remove_igc',
                              'layer_opacity=["XIII masses", "0.31"]'],
            'poster_map': ['remove_non_printable1_main', 'show_all',
                           #'add_shadow',
                           'shift_inf_level', 'replace_symbols', 'date',
                           'zooms', 'remove_non_printable2', 'remove_igc',
                           'layer_opacity=["XIII masses", "0.31"]'],
            'printable_map_public': ['remove_non_printable1_pub', 'show_all',
                              #'add_shadow',
                              'shift_inf_level', 'replace_symbols', 'date',
                              'zooms', 'remove_non_printable2', 'remove_igc',
                              'layer_opacity=["XIII masses", "0.31"]'],
            #'igc': ['remove_private', 'remove_non_printable',
                    #'remove_background', 'remove_limestone', 'remove_zooms',
                    #'remove_other=["raccords plan 2D", "parcelles", '
                                  #'"raccords gtech 2D"]',
                    #'show_all', 'add_shadow', 'date', 'recolor="igc"'],
            'igc': ['remove_private', 'remove_non_printable1_pub',
                    'remove_non_printable2',
                    'remove_background', 'remove_limestone', 'remove_zooms',
                    'remove_other=["raccords plan 2D", "parcelles", '
                                  '"raccords gtech 2D"]',
                    'show_all', 'add_shadow', 'date', 'recolor="igc"',
                    'layer_opacity=["planches fond", "0.44"]',
                    'layer_opacity=["planches IGC", "0.44"]'],
            'igc_private': ['remove_wip', 'remove_non_printable_igc_private',
                    'remove_non_printable2',
                    'remove_background', 'remove_limestone', 'remove_zooms',
                    'remove_other=["raccords plan 2D", "parcelles", '
                                  '"raccords gtech 2D"]',
                    'show_all', 'add_shadow', 'date', 'recolor="igc"',
                    'layer_opacity=["planches fond", "0.44"]',
                    'layer_opacity=["planches IGC", "0.44"]'],
            'aqueduc': ['remove_non_printable1', 'show_all',
                              #'add_shadow',
                               'shift_inf_level', 'replace_symbols', 'date',                         
                              'remove_background', 'remove_wip', 
                              'remove_other=["raccords plan 2D", "parcelles", '
                                  '"raccords gtech 2D"]',
                              'replace_symbols', 'date', 'remove_zooms', 
                              'remove_non_printable2', 'remove_igc', 
                              'remove_calcaire', 'remove_non_aqueduc',
                              'layer_opacity=["XIII masses", "0.31"]'],                    
        }

        map_2d = copy.deepcopy(xml)
        self.xml = map_2d
        self.removed_labels = set()
        self.keep_private = True
        self.keep_transformed_properties = set(('level', 'map_transform'))
        self.map_name = map_name

        self.remove_selected_layers(map_2d)

        results = []
        done = set()
        filters = list(filters)
        while filters:
            filter = filters.pop(0)
            value = []
            if isinstance(filter, str):
                filt_val = filter.split('=')
                if len(filt_val) > 1:
                    filter = filt_val[0]
                    value = eval(filt_val[1])
                    if not isinstance(value, list):
                        value = [value]
                done.add(filter)
                filt_def = all_filters[filter]
            if not isinstance(filt_def, list):
                done.add(filt_def)
                print('apply filter:', filter, value)
                result = filt_def(map_2d, *value)
                results.append(result)
            else:
                filters += filt_def

        self.xml.result = results
        print('build_2d_map done.')
        return self.xml


_inksape_ubuntu16 = None

def get_inkscape_ub16():
    global _inksape_ubuntu16

    if _inksape_ubuntu16 is not None:
        return _inksape_ubuntu16

    inkscape_ub16 = ['inkscape']
    if os.path.exists('/etc/lsb-release'):
        with open('/etc/lsb-release') as f:
            info = f.readlines()
        info = dict([x.strip().split('=') for x in info])
        release = info.get('DISTRIB_RELEASE')
        if not release or release == '16.04':
            return inkscape_ub16
        pwd = os.getcwd()
        if pwd.startswith(os.path.realpath(os.environ.get('HOME'))):
            pwd = pwd.replace(os.path.realpath(os.environ.get('HOME')),
                              os.environ.get('HOME'))
        casa_distro = distutils.spawn.find_executable('casa_distro')
        if not casa_distro:
            return inkscape_ub16
        dist = subprocess.check_output(['casa_distro', 'list'])
        dist = [x for x in dist.split('\n') if not x.startswith('  ')]
        dist = [{x.split('=')[0]:x.split('=')[1] for x in d.split()}
                for d in dist]
        dist = [d for d in dist if d.get('system') == 'ubuntu-16.04']
        for d in dist:
            cmd = ['casa_distro', 'run'] \
                + ['%s=%s' % (k, v) for k, v in d.items()]
            try:
                subprocess.check_call(cmd + ['inkscape', '--help'])
                inkscape_ub16 = cmd + ['cwd=%s' % pwd, 'inkscape']
                break
            except:
                pass
    return inkscape_ub16


_inkscape_version = {}

def inkscape_version(inkscape_exe='inkscape'):
    global _inkscape_version

    if not isinstance(inkscape_exe, (tuple, list)):
        inkscape_exe = [inkscape_exe]

    ver = _inkscape_version.get(tuple(inkscape_exe))
    if ver:
        return ver

    over = subprocess.check_output(inkscape_exe + ['--version']).decode()
    print('over:', over)
    ver = [int(x) for x in over.strip().split()[1].split('-')[0].split('.')]
    _inkscape_version[tuple(inkscape_exe)] = ver
    return ver


def export_pdf(in_file, out_file=None):
    inkscape_exe = ['inkscape']
    iver = inkscape_version()
    if iver[0] < 1:
        if iver[1] >= 92:
            # 0.92 has a but in pdf export
            inkscape_exe = get_inkscape_ub16()
        iver = inkscape_version(inkscape_exe)
    print('pdf export exe:', inkscape_exe, iver)
    if iver[0] >= 1:
        # 1.x commandline options have competely changed
        cmd = inkscape_exe + [
             '--export-pdf-version', '1.5', '--export-area-page',
             '--export-type', 'pdf']
        if out_file:
            cmd += '-o', out_file
        subprocess.check_call(cmd + [in_file])
    else:
        if not out_file:
            out_file = in_file.replace('.svg', '.pdf')
        subprocess.check_call(
            inkscape_exe + ['-z',
             '--export-pdf-version', '1.5', '--export-area-page',
             '--export-pdf', out_file, in_file])

def export_png(in_file, resolution=180, rect_id=None, out_file=None,
               ignore_errors=False):
    inkscape_exe = ['inkscape']
    iver = inkscape_version()
    #if iver[0] == 1:
        ## 1.0 has a bug and crashes during png save
        ## (both actually for large images)
        #inkscape_exe = get_inkscape_ub16()
        #iver = inkscape_version(inkscape_exe)
    print('png export exe:', inkscape_exe, ', version:', iver)
    if not out_file:
        out_file = in_file.replace('.svg', '.png')
    if ignore_errors:
        call = subprocess.call
    else:
        call = subprocess.check_call
    if iver[0] >= 1:
        # 1.x commandline options have competely changed
        cmd = inkscape_exe + [
             '--export-type', 'png', '--export-dpi', str(resolution),
             '-o', out_file]
        if rect_id:
             cmd += ['--export-id', rect_id]
        call(cmd + [in_file])
    else:
        cmd = inkscape_exe + ['-z',
             '--export-dpi', str(resolution),
             '--export-png', out_file]
        if rect_id:
             cmd += ['--export-id', rect_id]
        call(cmd + [in_file])

def convert_to_format(png_file, format='jpg', remove=True, max_pixels=None):
    outfile = png_file.replace('.png', '.%s' % format)
    if PIL:
        # use Pillow PIL module
        if not max_pixels:
            max_pixels = 30000 * 30000  # large enough
        PIL.Image.MAX_IMAGE_PIXELS = max_pixels
        try:
            with PIL.Image.open(png_file) as im:
                if format == 'jpg':
                    # convert to RGB with alpha and white background
                    front = np.array(im)  # copy because the image in read only
                    for i in range(3):
                        alpha = front[:, :, 3] / 255.
                        front[:, :, i] = (
                            255 * (1. - alpha)
                            + front[:, :, i] * alpha).astype(np.uint8)
                    front[:,:,3] = 255

                    im = PIL.Image.fromarray(front, 'RGBA')
                    im = im.convert(mode='RGB')

                save_options={}
                if format == 'tif':
                    # save_options['compression'] = 'tiff_lzw'
                    save_options['compression'] = 'jpeg'
                else:
                    save_options['quality'] = 95
                try:
                    im.save(outfile, **save_options)
                except:
                    if format == 'tif':
                        # we smetimes run into the error:
                        # JPEGSetupEncode: RowsPerStrip must be multiple of 8
                        # for JPEG.
                        # I don't know how to handle it for now, so then switch
                        # to LZW compression (files will be much larger)
                        save_options['compression'] = 'tiff_lzw'
                        im.save(outfile, **save_options)
                    else:
                        raise
        except OSError:
            print("cannot convert", infile)
    else:
        # use ImageMagick convert tool
        subprocess.check_call(
            ['convert', '-quality', '98', '-background', 'white', '-flatten',
            '-alpha', 'on',
              png_file, outfile])
    if remove:
        os.unlink(png_file)


def build_2d_map(xml_et, out_filename, map_name, filters, clip_rect,
                 dpi, shadows=True, do_pdf=False, do_jpg=True, georef=None):
    svg2d = CataMapTo2DMap()
    map2d = svg2d.build_2d_map(xml_et, filters=filters, map_name=map_name)
    clip_rect_name = clip_rect
    clip_rect = svg2d.find_clip_rect(xml_et, clip_rect)
    yscale = 1.
    if clip_rect:
        svg2d.ensure_clip_rect(map2d, clip_rect, xml_et)
        svg2d.clip_page(map2d, clip_rect)
        # TODO: remove hard-coded clip here
        if georef and clip_rect_name != 'nord_sud_clip':
            # not the same clipping as the georefed one
            cr = svg2d.find_element(xml_et, clip_rect)
            crref = svg2d.find_clip_rect(xml_et, 'nord_sud_clip')
            crref = svg2d.find_element(xml_et, crref)
            if cr and crref:
                yscale = float(cr[0].get('height')) \
                    / float(crref[0].get('height'))
                print('use yscale:', yscale)

    map2d.write(out_filename.replace('.svg', '_%s_flat.svg' % map_name))
    if shadows:
        svg2d.add_shadows(map2d)
    map2d.write(out_filename.replace('.svg', '_%s.svg' % map_name))

    # build bitmap and pdf versions
    # private
    export_png(out_filename.replace('.svg', '_%s.svg' % map_name),
               dpi, clip_rect)
    if do_pdf:
        export_pdf(out_filename.replace('.svg', '_%s_flat.svg' % map_name))
    os.unlink(out_filename.replace('.svg', '_%s_flat.svg' % map_name))
    if do_jpg or georef:
        if georef:
            format = 'tif'
        else:
            format = 'jpg'
        print('convert to', format.upper())
        convert_to_format(out_filename.replace('.svg', '_%s.png' % map_name),
                          format=format)
    if georef:
        try:
            from . import gdalcopyproj
        except ImportError:
            print('gdal module is not installed - georeferencing data will '
                  'not be copied')
            return
        tiff_file = out_filename.replace('.svg', '_%s.tif' % map_name)
        gdalcopyproj.copy_geo_projection(georef, tiff_file, scale_y=yscale)
        print('geolocalization info copied.')


def scale_georef_points_file(in_filename, out_filename, scale_factor_x,
                             scale_factor_y=None):
    ''' Rescale source positions in a QGis .points file in order to adapt
    to a different resolution
    '''
    if scale_factor_y is None:
        scale_factor_y = scale_factor_x
    with open(filename) as f:
        reader = csv.reader(f)
        lines = []
        for row in reader:
            lines.append(row)

    # scale columns 2 and 3 (sourceX,sourceY)
    for row in lines[2:]:
        row[2] = str(float(row[2]) * scale_factor_x)
        row[3] = str(float(row[3]) * scale_factor_y)

    with open(out_filename, 'w') as f:
        # 1st line is not parsed correctly, write it by hand
        print(','.join(lines[0]), file=f)
        writer = csv.writer(f)
        for row in lines[1:]:
            writer.writerow(row)


def main():

    time_start = time.time()
    do_2d = False
    do_3d = False
    do_igc = False
    do_igc_private = False
    do_split = False
    do_join = False
    do_recolor = False
    out_dirname = 'meshes_obj'
    maps_dpi = {
        'default': '180',
        'public': '360',
        'private': '360',
        'private_wip': '180',
        'poster': '360',
        'igc': '180',
        'igc_private': '300',
    }
    all_maps = 'public,private,wip,poster,igc,igc_private','aqueduc','No_Gtech'

    class MultilineFormatter(argparse.HelpFormatter):
        def _fill_text(self, text, width, indent):
            text = text.replace('\n\n* ', '|n |n * ')
            text = text.replace('\n* ', '|n * ')
            text = text.replace('\n\n', '|n |n ')
            text = self._whitespace_matcher.sub(' ', text).strip()
            paragraphs = text.split('|n')
            multiline_text = ''
            for paragraph in paragraphs:
                formatted_paragraph = _textwrap.fill(paragraph, width, initial_indent=indent, subsequent_indent=indent) + '\n\n'
                multiline_text = multiline_text + formatted_paragraph
            return multiline_text

    parser = ArgumentParser(
        prog='catamap',
        description='''Catacombs maps using SVG source map with codes inside it.

The program allows to produce:

* 2D "readable" maps with symbolsmain changed to larger ones, second level shifted to avoid superimposition of corridors, enlarged zooms, shadowing etc.

* 3D maps to be used in a 3D visualization program, a webGL server, or the CataZoom app.
''',
        formatter_class=MultilineFormatter)
    parser.add_argument(
        '--2d', action='store_true', dest='do_2d',
        help='Build 2D maps (several maps). the maps list is given via the '
        '--maps option. If the latter is not specified, do all.')
    parser.add_argument(
        '-m', '--maps', dest='do_2d_maps',
        help='specify which 2d maps should be built, ex: '
        '"public,private,igc". Values are in ("public", "private", "wip", '
        '"poster", "igc", "igc_private", "aqueduc", "No_GTech", "igcportail", '
        '"igcportail_txt"). Default: all if --2d is used. If '
        'this option is specified, --2d is implied (thus is not needed)')
    parser.add_argument(
        '--3d', action='store_true', dest='do_3d',
        help='Build 3D map meshes in the "%s/" directory' % out_dirname)
    parser.add_argument(
        '--color',
        help='recolor the maps using a color model. Available models are '
        '(currently): igc, bator, black (igc is used automatically in the '
        '--igc options). The list of available colorsets for a SVG map can be '
        'obtained using the option --list-colorsets.')
    parser.add_argument(
        '--list-colorsets', action='store_true',
        help='list available colorsets in this map')
    parser.add_argument(
        '--split', action='store_true',
        help='split the SVG file into 4 smaller ones, each containing a '
        'subset of the layers')
    parser.add_argument(
        '--dpi', # nargs='+',
        help='output JPEG images resolution. May be global (for all outputs): '
        '"360", or scoped to a single map: "igc:360". Several --dpi options '
        'may specify resolutions for several output maps: '
        '"--dpi 200,igc:360,private:280"')
    parser.add_argument(
        '--clip',
        help='clip using this rectangle ID in the inkscape SVG')
    parser.add_argument(
        '--no-pdf', action='store_true', default=None,
        help='do not generate PDF versions of the map')
    parser.add_argument(
        '--pdf', action='store_true', default=None,
        help='do generate PDF versions of the map')
    parser.add_argument(
        '--join', action='store_true',
        help='reverse the --split operation: concatenate layers from several '
        'files')
    parser.add_argument(
        '--output_filename',
        help='base filename for output 2D maps. The filename will be suffixed '
        'according to maps types (_imprimable, _imprimable_private, etc) '
        '(default: same as input file). Be careful that some maps are using '
        'files linked in the same input directory, and will not work if the '
        'output is in a different directory.')
    parser.add_argument(
        'input_file',
        help='input SVG Inkscape file')
    parser.add_argument(
        'output_3d_dir', nargs='?', default=out_dirname,
        help='output 3D meshes directory (default: %(default)s)')
    parser.add_argument(
        '-g', '--georef',
        help='Copy GeoTIFF information from the given source file to a .tif '
        'export')

    options = parser.parse_args()

    do_2d = options.do_2d
    do_2d_maps = options.do_2d_maps
    if do_2d_maps:
        do_2d = True
    elif do_2d:
        do_2d_maps = all_maps

    do_3d = options.do_3d
    do_split = options.split
    do_join = options.join
    do_pdf = None
    do_list_colorsets = options.list_colorsets
    if options.no_pdf is not None:
        do_pdf = not options.no_pdf
    elif options.pdf is not None:
        do_pdf = options.pdf
    out_filename = options.output_filename
    colorset = None
    if options.color:
        do_recolor = True
        colorset = options.color
    if options.dpi:
        dpi = options.dpi.split(',')
        maps_dpi2 = {}
        for item in dpi:
            dpi_spec = item.split(':')
            scope = 'default'
            resol = dpi_spec[-1]
            if len(dpi_spec) >= 2:
                scope = dpi_spec[0]
            maps_dpi2[scope] = resol
        if 'default' in maps_dpi2:
            # "default" overrides all builtin settings
            maps_dpi = maps_dpi2
        else:
            # otherwise we just update
            maps_dpi.update(maps_dpi2)
        # print('resolutions:', maps_dpi)

    clip_rect = options.clip

    # print(options)

    svg_filename = options.input_file
    out_dirname = options.output_3d_dir
    if not out_filename:
        out_filename = options.input_file
    if not out_filename.endswith('.svg'):
        out_filename += '.svg'

    if do_3d:
        svg_mesh = CataSvgToMesh()
    else:
        svg_mesh = CataMapTo2DMap()
    #svg_mesh.debug = True

    georef = options.georef

    if colorset:
        svg_mesh.colorset = colorset

    if do_3d or do_2d or do_split or do_recolor or do_list_colorsets:
        print('reading SVG...')
        xml_et = svg_mesh.read_xml(svg_filename)

    if do_list_colorsets:
        svg_mesh.list_colorsets(xml_et)

    if do_3d:
        print('extracting meshes...')
        meshes = svg_mesh.read_paths(xml_et)
        svg_mesh.postprocess(meshes)

        print('saving meshes...')
        summary = svg_mesh.save_mesh_dict(
            meshes, out_dirname, ('.obj', 'WAVEFRONT'),
            ('.obj', 'WAVEFRONT'),
            'map_objects.json',
            out_filename.replace('.svg', '_imprimable_private.jpg'))

    if do_2d:
        do_2d_maps = set(do_2d_maps.split(','))
        print('build 2D maps:', do_2d_maps)

        col_filter = []
        if do_recolor:
            col_filter = ['recolor="%s"' % colorset]

        maps_def = {
            'private': {
                'name': 'imprimable_private',
                'filters': ['remove_wip', 'printable_map'] + col_filter,
                'clip_rect': 'nord_sud_clip',
                'shadows': True,
                'do_pdf': True,
            },
            'poster': {
                'name': 'poster_private',
                'filters': ['remove_wip', 'poster_map'] + col_filter,
                'clip_rect': 'grs_clip',
                'shadows': True,
                'do_pdf': False,
            },
            'wip': {
                'name': 'imprimable_private_wip',
                'filters': ['printable_map'] + col_filter,
                'clip_rect': 'nord_sud_clip',
                'shadows': True,
                'do_pdf': False,
            },
            'public': {
                'name': 'imprimable',
                'filters': ['remove_private', 'remove_gtech',
                            'printable_map_public'] + col_filter,
                'clip_rect': 'grs_clip',
                'shadows': True,
                'do_pdf': True,
            },
            'igc': {
                'name': 'igc',
                'filters': ['igc'],
                'clip_rect': 'grs_clip',
                'shadows': True,
                'do_pdf': False,
            },
            'igc_private': {
                'name': 'igc_private',
                'filters': ['igc_private'],
                'clip_rect': 'nord_sud_clip',
                'shadows': True,
                'do_pdf': False,
            },
            'igcportail': {
                'name': 'igcportail',
                'filters': ['igc_private'],
                'clip_rect': 'nord_sud_clip',
                'shadows': True,
                'do_pdf': False,
                'do_jpg': False,
            },
            'igcportail_txt': {
                'name': 'igcportail_txt',
                'filters': ['igc_private'],
                'clip_rect': 'nord_sud_clip',
                'shadows': False,
                'do_pdf': False,
                'do_jpg': False,
            },
            'aqueduc': {
                'name': 'aqueduc',
                'filters': ['aqueduc'] + col_filter,
                'clip_rect': 'aqueduc_clip',
                'shadows': True,
                'do_pdf': True,
            },
            'No_GTech': {
                'name': 'No_GTech',
                'filters': ['remove_wip', 'printable_map','remove_gtech']
                    + col_filter,
                'clip_rect': 'nord_sud_clip',
                'shadows': True,
                'do_pdf': True,
           },
        }

        for map_type in do_2d_maps:
            map_def = dict(maps_def[map_type])
            if clip_rect:
                map_def['clip_rect'] = clip_rect
            if do_pdf is not None:
                map_def['do_pdf'] = do_pdf
            print('clip:', map_def['clip_rect'])
            georef_yscale = 1.
            if georef:
                # don't write jpg, we will use tiff
                map_def['do_jpg'] = False
            build_2d_map(
                xml_et,
                out_filename,
                map_name=map_def['name'],
                filters=map_def['filters'],
                clip_rect=map_def['clip_rect'],
                dpi=maps_dpi.get('private', maps_dpi['default']),
                shadows=map_def['shadows'],
                do_pdf=map_def['do_pdf'],
                do_jpg=map_def.get('do_jpg', True),
                georef=georef)

    if do_split:
        svg2d = CataMapTo2DMap()
        map2d_split = svg2d.build_2d_map(
            xml_et, filters=['split_layers="default"'])
        for i, m in enumerate(map2d_split.result[-1]):
            m.write(out_filename.replace('.svg', '_%d.svg' % i))

    if do_join:
        svg2d = CataMapTo2DMap()
        map2d_join = svg2d.build_2d_map(
            None, filters=['join_layers="%s"' % out_filename])
        map2d_join.write(out_filename.replace('.svg', '_joined.svg'))

    time_len = time.time() - time_start
    print('execution time: %d:%05.2f min:sec.'
          % (int(time_len / 60.), time_len - int(time_len / 60.) * 60))

if __name__ == '__main__':
    main()
