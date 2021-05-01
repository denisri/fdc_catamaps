#!/usr/bin/env python
# coding: UTF-8

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

'''
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

    export PYTHONPATH="~/fdc_catamaps/python:$PYTHONPATH"

  (it can be set in a ``.bash_profile`` or ``.bashrc`` init file)

* get or make the source SVG file with codes inside, for instance ``plan_14_fdc_2021_04_29.svg``

* go to the directory containing it
* run the module ``catamap`` as a program::

    python -m catamap --2d plan_14_fdc_2021_04_29.svg

It should work using either python2 or python3.
The 2D maps options will produce files with suffixes in the current directory:
modified .svg files, .pdf and .jpg files.

The 3D maps options will produce meshes in a subdirectory.

Comandline options (may be used together):

-h, --help:
    get short help and quit
--2d:
    produce 2D maps
--igc:
    produce 2D maps with IGC maps underneath. Zooms, 2nd level shifts, and
    symbols replacements are not applied.
--igc_private:
    same as --igc but produce a private map (private layers are not removed)
--color:
    recolor the maps using a color model. Available models are (currently):
    igc, bator, black (igc is used automatically in the --igc options)
--3d:
    produce 3D meshes in a subdirectory (default: ``meshes_obj``)
--split:
    split the SVG file into 4 smaller ones, each containing a subset of the
    layers
--join:
    reverse the --split operation: concatenate layers from several files

'''

# import bdalti module
my_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, my_dir)
try:
    from .altitude import bdalti
except ImportError:
    print('could not import bdalti module.')
finally:
    del sys.path[0]


class CataSvgToMesh(svg_to_mesh.SvgToMesh):
    # TODO
    # read/use text size, color, centering, [orientation]
    ## wells from lower level to surface
    # basins, water wells

    limestone = ('calcaire 2010', 'calcaire ciel ouvert',
                 'calcaire masse2', 'calcaire masse', 'calcaire med',
                 'calcaire sup', 'calcaire vdg', )
    limestone_filar = ('calcaire limites', )
    limestone_inf = ('calcaire inf', 'calcaire_inf')
    corridors_sup = (
        'galeries',
        'galeries big sud',
        'galeries private',
        'piliers a bras',
        'inaccessible',
        'maconneries',
        u'maçonneries',
        'maconneries private',
        u'maçonneries private',
        u'maçonneries inaccessibles',
        u'maçonneries anciennes galeries big',
        'hagues',
        'hagues effondrees',
        'galeries agrandissements',
        'cuves',
        'oss off',
        'anciennes galeries big',
        'aqueduc',
        'galeries inaccessibles',
        'remblai epais',
        'remblai leger',
        'remblai epais inaccessibles',
        'remblai leger inaccessibles',
        'mur',
        'mur_ouvert',
        'mur private',
        'mur_ouvert private',
        'bassin',
        'bassin private',
        'bassin_recouvert',
        'rose',
        'rose private',
        'repetiteur',
        'eau',
        'ebauches',
        'grille',
        'porte', 'porte_ouverte') + limestone
    corridors_inf = (
        'galeries_inf',
        'galeries private_inf',
        'piliers_inf',
        'piliers a bras_inf',
        'maconneries_inf',
        'maconneries private_inf',
        u'maçonneries inf',
        u'maçonneries inf inaccessibles',
        'cuves_inf',
        'cuves private_inf',
        'oss off_inf',
        'galeries inaccessibles_inf',
        'remblai epais inaccessibles_inf',
        'remblai leger inaccessibles_inf',
        'eau_inf',
        'anciennes galeries_inf',
        'mur_inf',
        'mur_ouvert_inf',
        'mur private_inf',
        'mur_ouvert private_inf') + limestone_inf
    surf = ()
    corridors_esc = ('esc', 'esc_tri', 'porte_esc', 'esc_tech',
                     'escaliers inaccessibles',
                     'escaliers anciennes galeries big',)
    corridors_gtech = ('galeries techniques', 'galeries techniques despe',
                       'eau gtech_tech', 'ebauches_tech', 'grille_tech',
                       'passage_tech', 'porte_tech', 'grille-porte_tech',
                       'bassin_tech', 'repetiteur_tech', 'mur_tech',)
    corridors_metro = ('metro', )
    street_signs = ('plaques rues', u'plaques rues volées',
                    'plaques rues inaccessibles', 'plaques rues private')
    street_signs_inf = ('plaques rues_inf', )
    symbols = ('symboles', 'symboles_inf', 'symboles private',
               'symboles private_inf', 'symboles inaccessibles', 'marches',
               'marhes_inf', 'marches private')
    symbols_tech = ('symboles_tech', 'symboles gtech_tech',
                    'stair_symbol_tech', 'symboles gtech', 'marches_tech', )
    corridors = (corridors_sup, corridors_inf, surf, corridors_esc,
                 corridors_gtech, corridors_metro)
    corridors_ceil = ('maconneries', 'maconneries_inf',
                      'maconneries private', 'maconneries private_inf',
                      'piliers a bras',
                      'piliers a bras_inf',
                      'piliers a bras private',
                      'piliers a bras private_inf',
                      'piliers_inf', 'cuves', 'cuves_inf', 'cuves private_inf',
                      'mur', 'mur_ouvert', 'mur private', 'mur_ouvertprivate',
                      'mur_inf', 'mur_ouvert_inf', 'mur private_inf',
                      'mur_ouvert private_inf',
                      'mur_tech',
                      'repetiteur',
                      'rose',
                      'rose private',
                      'bassin', 'bassin private', 'bassin_recouvert',
                      'bassin_tech',
                      'eau', 'eau_inf', 'eau gtech_tech',
                      'passage_tech', 'grille_tech', 'porte_tech',
                      'grille-porte_tech',
                      'haghes', 'hagues effondrees'
                      'repetiteur_tech') + limestone + limestone_inf
    upper_arrow_groups = (u'salles v1 flèches', 'salles v1 fleches',
                          u'salles v1 flèches inaccessibles',
                          u'salles flèches private', u'salles vdg flèches',
                          u'rues v1 flèches', 'rues v1 fleches',
                          u'rues v1 flèches private', u'rues flèches dessus',
                          u'rues v1 flèches inaccessibles',
                          u'curiosités flèches', 'curiosites fleches',
                          u'curiosités flèches inaccessibles',
                          u'historiques flèches',
                          u'plaques de puits flèches',
                          u'plaques de puits flèches inaccessibles',
                          u'curiosités flèches private',
                          u'curiosités flèches dessus',
                          u'inscriptions flèches',
                          u'inscriptions flèches inaccessibles',
                          u'inscriptions conso flèches')
    inf_arrow_groups = (u'salles v1 flèches_inf', 'salles v1 fleches_inf',
                        u'rues v1 flèches_inf', 'rues v1 fleches_inf',
                        u'curiosités flèches_inf',
                        u'curiosités flèches private_inf',
                        u'inscriptions flèches_inf',
                        u'inscriptions conso flèches_inf')
    tech_arrow_groups = (u'salles v1 flèches_tech', 'salles v1 fleches_tech',
                        u'rues v1 flèches_tech', 'rues v1 fleches_tech',
                        u'curiosités flèches_tech', 'curiosites fleches_tech',
                        u'plaques de puits GTech flèches',
                        u'curiosités flèches GTech',
                        u'curiosités flèches private_tech')
    surf_arrow_groups = (u'salles v1 flèches_surf', 'salles v1 fleches_surf',
                        u'rues v1 flèches_surf', 'rues v1 fleches_surf',
                        u'curiosités flèches_surf', 'curiosites fleches_surf',
                        u'curiosités flèches private_surf')
    esc_arrow_groups = (u'curiosités flèches_esc', )
    arrow_groups = upper_arrow_groups + inf_arrow_groups + tech_arrow_groups \
        + surf_arrow_groups + esc_arrow_groups
    depth_map_names = (
        'profondeurs galeries',
        'profondeurs galeries_inf',
        'profondeurs esc',
        'profondeurs gtech',
        'profondeurs surf',
        'profondeurs pe',
        'profondeurs metro',
    )
    wells_ids = (u'échelle vers gtech', u'échelle vers gtech private',
                 u'\xe9chelle vers gtech', 'PSh gtech', 'PSh vers gtech',
                 'PE', 'PE inaccessibles', 'PE anciennes galeries big',
                 'PS', 'PS inaccessibles', 'PS anciennes galeries big',
                 'PSh', 'PSh inaccessibles', 'PSh anciennes galeries big',
                 'P ossements', 'P ossements inaccessibles',
                 'P ossements anciennes galeries big',
                 'echelle', u'échelle', u'échelle anciennes galeries big',
                 u'échelle inaccessibles',
                 u'\xe9chelle anciennes galeries big'
                 u'\xe9chelle inaccessible'
                 u'\xe9chelle', 'sans', 'PS sans', 'PSh_inf', 'PS_inf',
                 'PSh sans', 'PSh sans inaccessibles',
                 'PE_inf', 'PS_sq_tech', 'PS gtech', u'échelle gtech')
    hidden_layers = ('indications_big_2010', 'a_verifier', 'bord', 'bord_sud',
                     u'légende_alt', u'découpage', 'raccords plan 2D',
                     'raccords gtech 2D',
                     'masque vdg', u'masque cimetière', 'masque plage',
                     'agrandissement vdg', u'agrandissement cimetière',
                     'agrandissement plage', 'agrandissements fond',
                     'couleur_fond', 'couleur_fond sud',
                     'planches', 'planches fond', 'calcaire sup',
                     'calcaire limites', 'calcaire masse', 'calcaire masse2')
    sound_layers = ('sons', )

    proto_scale = np.array([[0.5, 0,   0],
                            [0,   0.5, 0],
                            [0,   0,   1]])

    def __init__(self, concat_mesh='list_bygroup', skull_mesh=None,
                 headless=True):
        super(CataSvgToMesh, self).__init__(concat_mesh)
        self.arrows = []
        self.depth_maps = []
        self.nrenders = 0
        self.z_scale = 0.5
        self.skull_mesh = skull_mesh
        self.water_scale_model = None
        self.stair_symbol_mesh = None
        self.fontis_mesh = None
        self.lily_mesh = None
        self.large_sign_mesh = None
        self.level = ''
        self.explicitly_show = ['parcelles', 'chatieres v3',
                                'chatieres v3_inf', 'chatieres private',
                                u'injecté', 'bas'] \
            + list(self.corridors_sup) \
            + list(self.corridors_inf) + list(self.corridors_gtech)
        self.sounds = []

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
                raise RuntimeError('anatomist is ont available. It is needed '
                                   'for CataSvgToMesh to work.')

    def filter_element(self, xml_element, style=None):

        def remove_word(label, word):
            if label == word:
                return ''
            if label.endswith(' %s' % word) or label.endswith('_%s' % word):
                return label[:-len(word) - 1]
            for pattern in (' %s ', ' %s_', '_%s ', '_%s_'):
                p = pattern % word
                if p in label:
                    index = label.find(p)
                    sep = p[-1]
                    return label.replace(p, sep)
            return label

        if len(self.depth_maps) != 0:
            if xml_element.tag.endswith('g'):
                return (self.read_depth_group, self.clear_depth_group, False)
            elif xml_element.tag.endswith('path'):
                return (self.read_depth_arrow, None, False)
            elif xml_element.tag.endswith('text'):
                return (self.read_depth_text, None, True)
            elif xml_element.tag.endswith('rect'):
                return (self.read_depth_rect, None, True)
            else:
                print('unknown depth child:', xml_element)
                return (self.noop, None, True)

        label = xml_element.get(
            '{http://www.inkscape.org/namespaces/inkscape}label')
        if label is None:
            label = xml_element.get('label')
        # alt (new) level information
        level = xml_element.get('level')
        if 'sons' in (label, self.main_group):
            print('label:', label, ', level:', level, ', main_group:',
                  self.main_group)
        self.level = ''
        if level is not None:
            self.level = level
        hidden = False
        if self.main_group in self.hidden_layers \
                or (style is not None and style.get('display') == 'none' \
                    and xml_element.get(
                        '{http://www.inkscape.org/namespaces/inkscape}label') \
                        not in self.explicitly_show):
            hidden = True
        if label is not None:
            # depths are taken into account even when hidden (because they
            # are normally hidden in the svg file)
            if label.startswith('profondeurs'):
                self.main_group = label
                return (self.start_depth_rect, self.clean_depth, False)
            if label in self.sound_layers:
                print('SOUND:', xml_element.tag, xml_element)
                self.read_sounds(xml_element)
                hidden = True
            elif label == 'lambert93':
                print('LAMBERT93')
                self.read_lambert93(xml_element)
                hidden = True
            if hidden or label == 'couleur_fond':
                # hidden layers are not rendered
                return (self.noop, None, True)
            # find out some keywords separated by ' ' or '_'
            label_w = '_'.join(label.split()).split('_')
            if 'inf' in label_w:
                self.level = 'inf'
                label = remove_word(label, 'inf')
            if self.main_group and ' private' in self.main_group \
                    and not 'private' in label_w:
                self.main_group = label + ' private'
            elif label:
                self.main_group = label

            if label in self.arrow_groups:
                return (self.read_arrows, self.clean_arrows, False)
            elif label == 'colim':
                return (self.read_spiral_stair, None, True)
            elif label in self.wells_ids:
                return (self.read_wells, None, True)
            elif label == 'etiage':
                return (self.read_water_scale, None, True)
            elif label in ('fontis', 'fontis_inf', 'fontis private',
                           'fontis private_inf'):
                return (self.read_fontis, None, True)
            elif label in ('stair_symbol', ):
                return (self.read_stair_symbol, None, True)
            elif label == 'arche':
                return (self.read_arch, None, True)
            elif label == 'escaliers':
                self.main_group = 'esc'
            elif label == 'escaliers private':
                self.main_group = 'esc private'
            elif label in (u'maçonneries', ):
                self.main_group = 'maconneries'
            elif label in (u'maçonneries private', ):
                self.main_group = 'maconneries private'
            elif label.startswith('lys'):
                return (self.read_lily, None, True)
            elif label.startswith('grande_plaque'):
                return (self.read_large_sign, None, True)
        if hidden:
            # hidden layers are not rendered
            return (self.noop, None, True)
        eid = xml_element.get('id')
        #print('id:', eid)
        if eid is None:
            return None

        # find out some keywords separated by ' ' or '_' or '-'
        if '-' in eid:
            eid = eid[:eid.index('-')]
        eid_w = '_'.join(eid.split()).split('_')

        if 'inf' in eid_w:
            #print('** EID:', eid, 'repace main_group:', self.main_group)
            eid = remove_word(eid, 'inf')
            self.main_group = eid + '_inf'
            self.level = 'inf'
        elif self.main_group is None:
            self.main_group = eid

        level_suffix = ''
        if self.level:
            level_suffix = '_' + self.level
        if level_suffix and not self.main_group.endswith(level_suffix):
            self.main_group += '_' + self.level

        #if self.level:
            #print('main_group:', self.main_group)
            #print('label:', label, ', level:', self.level)

        if eid == 'PE' or eid.startswith('PE-'):
            self.main_group = 'PE' + level_suffix
            return (self.read_wells, None, True)
        elif eid == 'PS' or eid.startswith('PS-'):
            self.main_group = 'PS' + level_suffix
            return (self.read_wells, None, True)
        elif eid == 'PSh' or eid.startswith('PSh-'):
            self.main_group = 'PSh' + level_suffix
            return (self.read_wells, None, True)
        elif eid == 'sans' or eid.startswith('sans-'):
            self.main_group = 'sans' + level_suffix
            return (self.read_wells, None, True)
        elif eid == 'P ossements' or eid.startswith('P ossements-'):
            self.main_group = 'p ossements' + level_suffix
            return (self.read_wells, None, True)
        elif eid in (u'échelle', u'\xc3\xa9chelle') \
                or eid.startswith('échelle-') \
                or eid.startswith(u'\xc3\xa9chelle-'):
            self.main_group = 'echelle' + level_suffix
            return (self.read_wells, None, True)
        elif eid == 'esc' or eid.startswith('esc-'):
            self.main_group = 'esc' + level_suffix
        elif eid == 'Cuves' or eid.startswith('Cuves-'):
            self.main_group = 'cuves' + level_suffix
        elif eid.startswith(u'piliers \xc3\xa0 bras'):
            if self.main_group and self.main_group.endswith(' private'):
                self.main_group = 'piliers a bras private' + level_suffix
            else:
                self.main_group = 'piliers a bras' + level_suffix
        elif eid.startswith(u'maçonneries private'):
            self.main_group = 'maconneries private' + level_suffix
        elif eid.startswith(u'maçonneries'):
            self.main_group = 'maconneries' + level_suffix
        elif eid == 'Oss Off' or eid.startswith('Oss Off-'):
            self.main_group = 'oss off' + level_suffix
        #elif eid == 'ex- galeries' or eid.startswith('ex- galeries-'):
            #self.main_group = 'ex- galeries'
        elif eid == 'Parcelle' or eid.startswith('Parcelle-'):
            self.main_group = 'parcelles' + level_suffix
        elif eid == 'ossuaire' or eid.startswith('ossuaire-'):
            self.main_group = 'ossuaire' + level_suffix
            if self.skull_mesh is None:
                return None
            else:
                return (self.read_bones, None, True)
        return None


    def noop(self, xml_path, trans, style=None):
        return None


    def read_path(self, xml_path, trans, style=None):
        if self.main_group is None:
            print('path with no group:', xml_path, list(xml_path.items()))
        if self.level != '':
            # FIXME this is not good, not clean...
            if not self.main_group.endswith('_' + self.level):
                self.main_group += '_' + self.level
        mesh = super(CataSvgToMesh, self).read_path(xml_path, trans, style)
        if len(self.arrows) != 0 and self.arrows[-1]:
            #print('arrow')
            if self.level == '' and self.main_group.endswith('_inf'):
                self.main_group = self.main_group[:-4]
            vert = mesh.vertex()
            nv = len(vert)
            for i in six.moves.xrange(nv):
                vert[i][2] = (4. - i * 3. / (nv - 1)) * self.z_scale
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
        return super(CataSvgToMesh, self).read_paths(xml)


    def text_description(self, xml_item, trans=None, style=None, text=''):
        # add level information in text objects
        desc = super(CataSvgToMesh, self).text_description(
            xml_item, trans=trans, style=style, text=text)
        if self.level:
            props = desc.get('properties', {})
            props['level'] = self.level
            desc['properties'] = props
        return desc


    def read_arrows(self, child_xml, trans, style=None):
        self.arrows.append(True)


    def clean_arrows(self):
        self.arrows.pop()


    def read_wells(self, wells_xml, trans, style=None):
        #print('read_wells.')
        wells = None
        trans0 = trans
        for child in wells_xml:
            trans = trans0
            trans2 = child.get('transform')
            if trans2 is not None:
                transm = self.get_transform(trans2)
                if trans is None:
                    trans = transm
                else:
                    trans = trans * transm
            while child is not None \
                    and (child.tag.endswith('}g') or child.tag == 'g'):
                if len(child) == 0:
                    child = None
                    break
                child = child[0]
                trans2 = child.get('transform')
                if trans2 is not None:
                    transm = self.get_transform(trans2)
                    if trans is None:
                        trans = transm
                    else:
                        trans = trans * transm
            if child is None:
                continue
            if child.tag.endswith('}path') or child.tag == 'path':
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
                if self.main_group in ('sans', 'PS sans', 'echelle'):
                    z = bmin[2] * self.z_scale
                    height = 7. * self.z_scale
                else:
                    z = bmin[2] * self.z_scale
                    height = 20. * self.z_scale
                #print('well group:', self.main_group, center)
                level = child.get('level')
                if level is None:
                    well_type = self.main_group + '_wells'
                else:
                    well_type = '%s_%s_wells' % (self.main_group, level)
                wells_spec = self.mesh_dict.setdefault(well_type, [])
                wells_spec.append((center, radius, z, height))
                #print('well_type:', well_type, len(wells_spec))
                #well = self.make_well(center, radius, z, height)
                #wells = self.mesh_dict.setdefault(self.main_group + '_tri',
                                                  #aims.AimsTimeSurface(3))
                #aims.SurfaceManip.meshMerge(wells, well)
                #wells.header()['material'] = well.header()['material']

    def read_spiral_stair(self, stair_xml, trans, style=None):
        #print('spiral stair')
        child = stair_xml[0]
        if child is None:
            return
        trans2 = child.get('transform')
        if trans2 is not None:
            transm = self.get_transform(trans2)
            if trans is None:
                trans = transm
            else:
                trans = trans * transm

        if child.tag.endswith('}path') or child.tag == 'path':
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
            if self.main_group in ('colim', 'colim private', 'colim_inf',
                                   'colim private_inf'):
                z = bmin[2] * self.z_scale
                height = 20. * self.z_scale
            else:
                z = bmin[2] * self.z_scale
                height = 7. * self.z_scale
            #print('well group:', self.main_group, center)
            wells_spec = self.mesh_dict.setdefault(
                self.main_group + '_wells', [])
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
        lily_mesh = aims.AimsTimeSurface(self.large_sign_mesh)
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
        arch_spec = self.mesh_dict.setdefault(self.main_group + '_wells', [])
        arch_spec.append((center, (radius, trans), 0., 3.))


    def read_water_scale(self, ws_xml, trans, style=None):
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


    def make_psh_well(self, center, radius, z, height):
        p1 = aims.Point3df(center[0], center[1], z)
        p2 = aims.Point3df(center[0], center[1], z + height)
        r0 = radius * 0.7
        well = aims.SurfaceGenerator.cylinder({
            'point1': p1, 'point2': p2, 'radius': r0, 'facets': 8,
            'smooth': True, 'closed': False})
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
        well.header()['material'] = {'diffuse': [0., 1., .6, 1.],
                                     'face_culling': 0}
        return well


    def make_ladder(self, center, radius, z, height):
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
        ladder.header()['material'] = {'diffuse': [1., 0., .6, 1.]}
        return ladder


    def make_spiral_stair(self, center, radius, z, height):
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
        well.header()['material'] = {'diffuse': [1., .6, 0., 1.],
                                     'face_culling': 0}
        return well


    def make_ps_well(self, center, radius, z, height, well_type):
        '''PS or PE (blue), P ossements (yellow)
        '''
        p1 = aims.Point3df(center[0], center[1], z)
        p2 = aims.Point3df(center[0], center[1], z + height)
        well = aims.SurfaceGenerator.cylinder({
            'point1': p1, 'point2': p2, 'radius': radius, 'facets': 8,
            'smooth': True, 'closed': False})
        if well_type.startswith('PE'):
            well.header()['material'] = {'diffuse': [0., 0.7, 1., 1.]}
        elif well_type == 'PS' or well_type.startswith('PS_') \
                or well_type.startswith('PS '):
            well.header()['material'] = {'diffuse': [1., 1., 1., 1.]}
        elif well_type.startswith('P ossements'):
            well.header()['material'] = {'diffuse': [1., 1., 0., 1.]}
        else:
            well.header()['material'] = {'diffuse': [0., 1., .6, 1.]}
        well.header()['material']['face_culling'] = 0
        return well


    def make_well(self, center, radius, z, height, well_type=None):
        if well_type is None:
            well_type = self.main_group
        if well_type == 'PS' or well_type.startswith('PS ') \
                or well_type.startswith('PS_'):
            return self.make_ps_well(center, radius, z, height, well_type)
        if well_type.startswith('PSh') or well_type.startswith('sans'):
            return self.make_psh_well(center, radius, z, height)
        elif well_type.startswith('echelle') \
                or well_type.startswith('échelle') \
                or well_type.startswith(u'\xe9chelle'):
            return self.make_ladder(center, radius, z, height)
        elif well_type.startswith('colim'):
            return self.make_spiral_stair(center, radius, z, height)
        elif well_type.startswith('arche'):
            return self.make_arch(center, radius, z, height)

        return self.make_ps_well(center, radius, z, height, well_type)


    def make_arch_square(self, center, radius_and_trans, z, height):
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

        rp = radius * 0.4
        radius = radius * scl
        hp = radius * 1.4
        wp = radius * 1.8
        rp2 = radius * 0.36
        c1 = aims.SurfaceGenerator.cube([0, 0, 0], rp, False)
        c2 = aims.AimsTimeSurface_3(c1)
        c3 = aims.SurfaceGenerator.cube([0, 0, 0], rp2, False)
        tmat = np.eye(4)
        tmat[2, 2] = 5.
        tmat[0, 3] = -wp
        tmat[2, 3] = radius
        tr = aims.AffineTransformation3d(tmat)
        aims.SurfaceManip.meshTransform(c1, tr)
        tmat[0, 3] = wp
        tr = aims.AffineTransformation3d(tmat)
        aims.SurfaceManip.meshTransform(c2, tr)
        tmat = np.eye(4)
        tmat[0, 0] = 4.
        tmat[2, 3] = radius + hp
        tr = aims.AffineTransformation3d(tmat)
        aims.SurfaceManip.meshTransform(c3, tr)
        aims.SurfaceManip.meshMerge(c1, c2)
        aims.SurfaceManip.meshMerge(c1, c3)
        tmat = np.eye(4)
        tmat[:3, 3] = center0
        tr = aims.AffineTransformation3d(tmat)
        aims.SurfaceManip.meshTransform(c1, tr)
        tmat = np.eye(4)
        tmat[:2, :2] = trans[:2, :2]
        tmat[:2, 3:] = trans[:2, 2:3]
        tmat[2, 3] = z
        tr = aims.AffineTransformation3d(tmat)
        aims.SurfaceManip.meshTransform(c1, tr)
        tmat2 = np.eye(4)
        tmat2[:3, 3] += center
        tr = aims.AffineTransformation3d(tmat2)
        aims.SurfaceManip.meshTransform(c1, tr)
        c1.header()['material'] = {'diffuse': [1., 1., 0.5, 1.]}
        return c1

    def make_arch(self, center, radius_and_trans, z, height):
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
        depth_mesh = self.mesh_dict.setdefault(self.main_group,
                                               aims.AimsTimeSurface_3())
        depth_mesh.header()['material'] = {'face_culling': 0,
                                           'diffuse': [0., 0.6, 0., 1.]}
        self.depth_maps.append(True)


    def clean_depth(self):
        self.depth_maps.pop()


    def read_depth_group(self, child_xml, trans, style=None):
        if hasattr(self, 'depth_group'):
            raise RuntimeError(
                'Nested depth group in main_group %s, element: %s, items: %s'
                % (self.main_group, repr(child_xml), repr(list(child_xml.items()))))
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
        if not self.main_group.startswith('profondeurs'):
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


    def read_sounds(self, xml, trans=None, style=None):
        print('READ SOUNDS')
        self.sounds = {}
        if trans is None:
            trans = np.matrix(np.eye(3))
        for xml_element in xml:
            if xml_element.tag.split('}')[-1] != 'g':
                raise ValueError('sound layer element is not a group:',
                                 xml_element)
            level = 0
            text = None
            pos = None
            level_t = xml_element.get('level')
            trans2 = xml_element.get('transform')
            trans_el = np.matrix(np.eye(3))
            if trans2 is not None:
                transm = self.get_transform(trans2)
                if trans is None:
                    trans_el = transm
                else:
                    trans_el = trans * transm
            if level_t is not None:
                if level_t == 'inf':
                    level = 1
                elif level_t == 'tech':
                    level = 2
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
                                                                style)
                    if len(mesh.vertex()) != 0:
                        try:
                            pos = mesh.vertex()[-1][:2]
                        except:
                            print('failed sound arrow, vertices:')
                            print(np.array(mesh.vertex()))
            radius = xml.get('radius')
            if radius is not None:
                radius = float(radius)
            else:
                radius = 10.
            if text and pos:
                self.sounds.setdefault(text, []).append((pos + [level], radius))
                print('sound:', self.sounds[text])


    def read_lambert93(self, xml, trans=None):
        print('READ LAMBERT93')
        if trans is None:
            trans = np.matrix(np.eye(3))
        lambert_map = []
        for xml_element in xml:
            if xml_element.tag.split('}')[-1] != 'g':
                raise ValueError('lambert93 element is not a group:',
                                 xml_element)
            level = 0
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


    def delaunay(self, mesh):
        points = np.array([[p[0], p[1]] for p in mesh.vertex()])
        tri = Delaunay(points)
        mesh.polygon().assign(tri.simplices)
        #mesh.header()['material']['face_culling'] = 0


    def build_depth_win(self, depth_mesh, size=(1000, 1000),
                        object_win_size=(8, 8)):
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


    def ground_altitude(self, pos):
        if hasattr(self, 'bdalti_map') and hasattr(self, 'lambert_coords'):
            return self.ground_altitude_bdalti(pos)
        else:
            return self.ground_altitude_topomap(pos)


    def ground_altitude_topomap(self, pos):
        if self.alt_bounds is None or self.ground_img is None:
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
        #print('ground_altitude_bdalti:', pos, x, y, z)
        return z


    def add_ground_alt(self, mesh):
        print('add_ground_alt on:', mesh)
        for v in mesh.vertex():
            v[2] += self.ground_altitude(v[:2])


    def build_depth_wins(self, meshes, size=(1000, 1000),
                         object_win_size=(8, 8)):
        self.depth_meshes = []
        self.depth_wins = []
        for ctype, depth_map in enumerate(self.depth_map_names):
            print('building depth map', ctype, depth_map)
            depth_mesh = meshes.get(depth_map)
            if depth_mesh is not None:
                win, amesh = self.build_depth_win(depth_mesh, size,
                                                  object_win_size)
                self.depth_meshes.append(amesh)
                self.depth_wins.append(win)
            else:
                self.depth_meshes.append(None)
                self.depth_wins.append(None)


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
            ok = view.positionFromCursor(pt[0], pt[1], pt)
            if ok:
                return pt[2]
        #print('get_depth: point not found:', pos, pt)
        return None


    def apply_depths(self, meshes):
        self.nrenders = 0

        corridors = self.corridors \
            + (self.street_signs + self.symbols
               + ('fontis', 'chatieres v3', 'chatieres private', 'bas',
                  u'injecté', 'ossuaire',
                  'stair_symbol', 'etiage_wall_tri', 'etiage_water_tri',
                  'etiage_line', 'lys', 'grande_plaque', )
               + self.limestone_filar, ) \
            + (('fontis_inf', 'fontis private_inf', 'chatieres v3_inf',
                'chatieres private_inf') + self.street_signs_inf,
               self.symbols_tech + ('chatieres private_tech', ), ) \
            + (('parcelles', 'grille surface'), )
        hshifts = (0., 0., 0., 0., 0., 1.5, 1.5, 2.5, 0., 0.)
        indiv_shifts = {'aqueduc': 10.,
                        'fontis': 2.5,
                        'lys': 5.,
                        'grande_plaque': 5.,
                        'chatieres v3': 0.5,
                        'chatieres private': 0.5,
                        self.street_signs_inf[0]: 1.5,
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
                        'rose private': 2.5,
                        'remblai leger': 0.8,
                        'remblai epais': 1.5,
                        'remblai leger_inf': 0.8,
                        'remblai epais_inf': 1.5,
                        'remblai leger inaccessibles': 0.8,
                        'remblai epais inaccessibles': 1.5,
                        'remblai leger inaccessibles_inf': 0.8,
                        'remblai epais inaccessibles_inf': 1.5,
                        }
        indiv_shifts.update({m: -2.
                             for m in self.limestone + self.limestone_filar
                                + self.limestone_inf})
        indiv_shifts['calcaire 2010'] = 0.  # this one as walls
        indiv_shifts['calcaire vdg'] = 0.  # this one as walls
        object_win_size = (2., 2.)
        self.build_depth_wins(meshes, (250, 250))
        depth_for_c = [0, 1, 4, 2, 3, 6, 0, 1, 3, 4]

        for ctype in range(len(corridors)):
            win = self.depth_wins[depth_for_c[ctype]]
            # print('ctype:', ctype, ', win:', win)
            debug = False
            if win is not None:
                view = win.view()
            else:
                view = None
            hshift = hshifts[ctype]

            for corridor in corridors[ctype]:
                mesh_l = meshes.get(corridor)
                not_ok = 0
                if mesh_l is not None:
                    print('processing corridor depth:', corridor)
                    failed = 0
                    done = 0
                    hshift_m = indiv_shifts.get(corridor, hshift) * self.z_scale
                    if not isinstance(mesh_l, list):
                        mesh_l = [mesh_l]
                    for mesh in mesh_l:
                        for v in mesh.vertex():
                            z = self.get_depth(v, view, object_win_size)
                            if z is not None:
                                v[2] += z + hshift_m
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
        level_names = {'': 0, 'sup': 0, 'inf': 1, 'tech': 3, 'surf': 4}
        text_zshift = 5.
        for mtype, mesh_items in six.iteritems(meshes):
            if mtype.endswith('_text'):
                for text_item in mesh_items['objects']:
                    position = text_item.get('properties', {}).get('position')
                    if position is not None:
                        level = text_item.get('properties', {}).get('level',
                                                                    '')
                        level_map = level_names.get(level, 0)
                        win = self.depth_wins[level_map]
                        if win is not None:
                            view = win.view()
                            hshift = (hshifts[level_map] + text_zshift) \
                                * self.z_scale
                            z = self.get_depth(position, view, object_win_size)
                            if z is not None and z + hshift > position[2]:
                                position[2] = z + hshift


        print('built depths in', self.nrenders, 'renderings')


    def apply_arrow_depth(self, mesh, arrow_type):
        if arrow_type in self.inf_arrow_groups:
            z_map = 1
            # text is related to upper level depth
            tz_map = 0
        elif arrow_type in self.tech_arrow_groups:
            z_map = 3
            # text is related to tech level depth
            tz_map = 3
        elif arrow_type in self.esc_arrow_groups:
            z_map = 2
            # text is related to stairs level depth
            tz_map = 0
        else:
            z_map = 0
            # text is related to upper level depth
            tz_map = 0
        hshifts = (0., 0., 0., 0., 0.)
        text_hshift = 4.
        text_z1 = 4. * self.z_scale
        text_z0 = text_z1
        text_win = self.depth_wins[tz_map]
        object_win_size = (8, 8)
        base = 1 * self.z_scale
        dz = text_z0 - base
        win = self.depth_wins[z_map]
        hshift = hshifts[z_map] * self.z_scale
        hshift1 = (hshifts[tz_map] + text_hshift) * self.z_scale
        if win is not None:
            view = win.view()
            for v in mesh.vertex():
                z = self.get_depth(v, view, object_win_size)
                if z is not None:
                    z += hshift
                    old_z = v[2]
                    text_z = text_z1
                    if text_win is not None:
                        text_view = text_win.view()
                        tz = self.get_depth(v, text_view, object_win_size)
                        if tz is not None and tz + hshift1 > text_z1:
                            tz += hshift1
                            text_z = tz
                    # old_z * s + d = new_z
                    # text_z0 * s + d = text_z
                    # base * s + d = z + base
                    # d = text_z - text_z0 * s = z + base * (1 - s)
                    # s * (text_z0 - base) = text_z - base - z
                    # s = (text_z - base - z) / (text_z0 - base)
                    # d = (text_z0 * z + base * (text_z0 - text_z)))
                    #     / (text_z0 - base)
                    s = (text_z - base - z) / dz
                    d = (text_z0 * z + base * (text_z0 - text_z)) / dz
                    v[2] = s * old_z + d
                else:
                    pass # warn ?


    def build_wells_with_depths(self, meshes):
        # levels:
        #     sup -> surf: PS, PSh, colim etc.
        #     inf -> sup:  sans, echelle, PS sans
        #     sup -> pe:   PE
        #     inf -> surf: PS_inf, PSh_inf...
        #     sup -> gtech
        #     gtech -> surf
        levels_list = ((0, 4), (1, 0), (0, 5), (1, 4), (0, 3), (3, 4))
        zdiff = (0., 0., -9., 0., 0., 0.)
        hdiff = (0., 1.5, -10., 0., 0., 0.)
        for dtype, wtypes in enumerate(
                (('PS_wells', 'PSh_wells', 'colim_wells',
                  'colim private_wells', 'P ossements_wells', 'arche_wells',
                  'PSh inaccessibles_wells',
                  'PSh anciennes galeries big_wells'),
                 ('sans_wells', 'PS sans_wells', 'echelle_wells',
                  u'échelle_wells',
                  u'\xe9chelle_wells',
                  u'échelle inaccessibles_wells',
                  u'échelle anciennes galeries big_wells',
                  'arche_inf_wells',
                  'PS sans inaccessibles_wells',
                  'PSh sans_wells', ),
                 ('PE_wells', 'PE inaccessibles_wells',
                  'PE anciennes galeries big_wells', ),
                 ('PS_inf_wells', 'PSh_inf_wells', 'colim_inf_wells',
                  'colim private_inf_wells', ),
                 (u'échelle vers gtech_wells',
                  u'échelle vers gtech private_wells',
                  u'\xe9chelle vers gtech_wells',
                  'PSh vers gtech_wells'),
                 ('PSh gtech_wells', 'PSh_tech_wells', 'PS gtech_wells',
                  'PS_sq_tech_wells', u'échelle gtech_wells', ))):
            views = [None, None, None, None, None, None]
            if hasattr(self, 'depth_wins'):
                for level in range(5):
                    if len(self.depth_wins) > level \
                            and self.depth_wins[level] is not None:
                        views[level] = self.depth_wins[level].view()

            levels = levels_list[dtype]
            zadd = zdiff[dtype] * self.z_scale
            hadd = hdiff[dtype] * self.z_scale

            for wtype in wtypes:
                specs = meshes.get(wtype)
                if specs is not None:
                    well_type = wtype[:-6]
                    wells = None
                    for ws in specs:
                        center, radius, z, height = ws
                        c3 = (center[0], center[1], 0.)
                        if views[levels[0]] is not None:
                            z0 = self.get_depth(c3, views[levels[0]])
                            if z0 is not None:
                                z = z0
                        if views[levels[1]] is not None:
                            z0 = self.get_depth(c3, views[levels[1]])
                            if z0 is not None:
                                height = z0 - z
                        elif levels[1] == 4: # surface with no map
                            z0 = self.ground_altitude(c3)
                            height = z0 - z
                        well = self.make_well(center, radius, z + zadd,
                                              height + hadd, well_type)
                        if wells is None:
                            wells = well
                        else:
                            aims.SurfaceManip.meshMerge(wells, well)
                    meshes[well_type + '_tri'] = wells


    def tesselate(self, mesh, flat=False):
        import anatomist.api as ana
        a = ana.Anatomist()
        a.setUserLevel(5)  # needed to use tesselation fusion
        if flat:
            # tessalate at constant Z, then set back Z after tesselation
            orig_pos = np.array(mesh.vertex())
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
        # use custom colors for some things
        mesh = meshes.get('parcelles')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [0.45, 0.7, 0.93, 0.5]}
        mesh = meshes.get('grille surface')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [0.9, 0.9, 0.9, 1.]}
        mesh = meshes.get('galeries big PARIS')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [1., 0.84, 0., 1.]}
        mesh = meshes.get('anciennes galeries big')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.8, 0.8, 0.8, 0.3]}
        mesh = meshes.get('ex- galeries_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.7, 0.7, 0.57, 0.3]}
        mesh = meshes.get('anciennes galeries_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.7, 0.7, 0.57, 0.3]}
        mesh = meshes.get('galeries_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.89, 0.45, 0.15, 1.]}
        mesh = meshes.get('galeries private_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.89, 0.45, 0.15, 1.]}
        mesh = meshes.get('cuves')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.3, 0.3, .5]}
        mesh = meshes.get('cuves_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.3, 0.3, .5]}
        mesh = meshes.get('cuves private_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.3, 0.3, .5]}
        mesh = meshes.get('aqueduc')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.65, 1., .3]}
        mesh = meshes.get('galeries techniques')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.13, 0.75, .13, 1.]}
        mesh = meshes.get('metro')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.13, 0.13, .75, 1.]}
        mesh = meshes.get('oss off')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.68, 0.48, .43, 1.]}
        mesh = meshes.get('oss off_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.27, .27, 1.]}
        mesh = meshes.get('galeries inaccessibles')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.68, 0.48, .43, 1.]}
        mesh = meshes.get('galeries inaccessibles_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.27, .27, 1.]}
        mesh = meshes.get('symboles')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, .74, .67, 1.]}
        mesh = meshes.get('symboles_tech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, .74, .67, 1.]}
        mesh = meshes.get('symboles gtech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, 0.74, .67, 1.]}
        mesh = meshes.get('symboles gtech_tech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, 0.74, .67, 1.]}
        mesh = meshes.get('symboles_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, 0.74, .67, 1.]}
        mesh = meshes.get('symboles private')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, 0.74, .67, 1.]}
        mesh = meshes.get('symboles private_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.43, 0.74, .67, 1.]}
        mesh = meshes.get('repetiteur')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.3, .3, .3, 1.]}
        mesh = meshes.get('repetiteur_tech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.3, .3, .3, 1.]}
        mesh = meshes.get('plaques rues')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.5, 0.2, 0., 1.]}
        mesh = meshes.get('plaques rues_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.5, 0.2, 0., 1.]}
        mesh = meshes.get(u'plaques rues volées')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.6, 0.5, 0.5, 1.]}
        mesh = meshes.get('bassin')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.73, .88, 1., .7]}
        mesh = meshes.get('bassin_recouvert')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [1., .88, .73, .7]}
        mesh = meshes.get('bassin_tech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.73, .88, 1., .7]}
        mesh = meshes.get('eau')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.92, 1., .5]}
        mesh = meshes.get('eau_inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.92, 1., .5]}
        mesh = meshes.get('eau gtech_tech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.4, 0.92, 1., .5]}
        mesh = meshes.get('calcaire sup')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.54, 0.47, .42, .4]}
        mesh = meshes.get('calcaire med')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.54, 0.46, .21, .4]}
        mesh = meshes.get('calcaire inf')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.55, 0.38, .27, .4]}
        mesh = meshes.get('calcaire ciel ouvert')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.57, 0.57, .42, .4]}
        mesh = meshes.get('calcaire 2010')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.95, 0.93, .85, .4]}
        mesh = meshes.get('grille-porte_tech')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.6, 0.3, .3, 1.]}
        mesh = meshes.get('porte_esc')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.6, 0.6, .3, 1.]}
        mesh = meshes.get('remblai epais')
        if mesh is not None and len(mesh) != 0:
            mesh[0].header()['material'] = {'diffuse': [.7, .7, .41, .4]}

        # lighen texts for black background
        tspec = meshes.get('salles v1_text')
        if tspec is not None:
            self.recolor_text_specs(tspec, [1., 1., 1., 1.])
        tspec = meshes.get('annotations_text')
        if tspec is not None:
            self.recolor_text_specs(tspec, [.8, .8, .8, 1.])
        tspec = meshes.get('rues sans plaques_text')
        if tspec is not None:
            self.recolor_text_specs(tspec, [.6, .6, .6, 1.])
        for rtype in ('rues v1_text', 'rues v1 private_text',
                      'rues inaccessibles_text'):
          #'rues vdg_text',
                      #'rues email_text',
                      #'rues inf_text', 'rues inf petit_text'):
            tspec = meshes.get(rtype)
            if tspec is not None:
                self.recolor_text_specs(tspec, [.8, .8, .8, 1.])

        # move arrows in order to follow text in 3D
        self.attach_arrows_to_text(meshes)

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
        for depths in self.depth_map_names:
            mesh = meshes.get(depths)
            if mesh is not None:
                self.add_ground_alt(mesh)
                self.delaunay(mesh)

        meshes['grille surface'] = self.build_ground_grid()

        # apply depths to corridors
        self.apply_depths(meshes)

        #for corridor, mesh in six.iteritems(meshes):
            #if corridor.endswith('_inf'):
                #self.change_level(mesh, -5.)

        # build wells with inf/sup depths
        self.build_wells_with_depths(meshes)

        # apply real depths to arrows
        for arrow in self.arrow_groups:
            mesh_l = meshes.get(arrow)
            if mesh_l:
                if not isinstance(mesh_l, list):
                    mesh_l = [mesh_l]
                for mesh in mesh_l:
                    self.apply_arrow_depth(mesh, arrow)
                    if 'material' not in mesh.header():
                        mesh.header()['material'] \
                            = {'diffuse': [1., 0.5, 0., 1.]}
                    mesh.header()['material']['line_width'] = 2.

        # extrude corridors walls
        heights = {'esc': 1., 'cuves': 1.5, 'cuves_inf': 1.5,
                   'plaques rues': 0.5, 'plaques rues_inf': 0.5,
                   u'plaques rues volées': 0.5,
                   'repetiteur': 1., 'repetiteur_tech': 1.,
                   'bassin': 0.3, 'bassin_tech': 0.3, 'bassin private': 0.3,
                   'bassin_recouvert': 0.3,
                   'eau': 0.2, 'eau_inf': 0.2, 'eau gtech_tech': 0.2,
                   'rose': 0.2, 'rose private': 0.2,
                   'remblai leger': 1.2,
                   'remblai epais': 0.5,
                   'remblai leger_inf': 1.2,
                   'remblai epais_inf': 0.5,
                   'remblai leger inaccessibles': 1.2,
                   'remblai epais inaccessibles': 0.5,
                   'remblai leger inaccessibles_inf': 1.2,
                   'remblai epais inaccessibles_inf': 0.5,
                   'hagues effondrees': 1.2,
                   }
        for corridor_t in self.corridors + (self.street_signs,
                                            self.street_signs_inf, ):
            for corridor in corridor_t:
                mesh_l = meshes.get(corridor)
                if mesh_l:
                    if not isinstance(mesh_l, list):
                        mesh_l = [mesh_l]
                    for mesh in mesh_l:
                        height = heights.get(corridor, 2.) * self.z_scale
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
                                    if c > 1.:
                                        c = 1.
                                    color[i] = c
                            else:
                                for i in range(3):
                                    c = color[i] - 0.4
                                    if c < 0.:
                                        c = 0.
                                    color[i] = c
                            ceil.header()['material']['diffuse'] = color
                        meshes.setdefault(corridor + '_wall', []).append(wall)
                        meshes.setdefault(corridor + '_ceil', []).append(ceil)

        # build floor or ceiling meshes using tesselated objects (anatomist)
        for corridor in self.corridors_ceil:
            mesh_l = meshes.get(corridor + '_ceil')
            if mesh_l:
                print('tesselate:', corridor + '_ceil')
                if not isinstance(mesh_l, list):
                    mesh_l = [mesh_l]
                for mesh in mesh_l:
                    tess_mesh = self.tesselate(mesh, flat=True)
                    if tess_mesh is not None:
                        #print('tesselation OK')
                        meshes.setdefault(corridor + '_ceil_tri',
                                          []).append(tess_mesh)
        for corridor_t in self.corridors:
            for corridor in corridor_t:
                if corridor not in self.corridors_ceil:
                    mesh_l = meshes.get(corridor)
                    if mesh_l:
                        print('tesselate:', corridor)
                        if not isinstance(mesh_l, list):
                            mesh_l = [mesh_l]
                        for mesh in mesh_l:
                            tess_mesh = self.tesselate(mesh, flat=True)
                            if tess_mesh is not None:
                                #print('tesselation OK')
                                meshes.setdefault(corridor + '_floor_tri',
                                                  []).append(tess_mesh)

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
        for layer in ('chatieres v3', 'chatieres v3_inf', 'chatieres private',
                      'chatieres private_inf', 'bas', u'injecté'):
            mesh = meshes.get(layer)
            if mesh is not None:
                cat_flap = self.make_cat_flap(
                    mesh, catflap_col.get(layer, [1., 0., 0., 0.8]))
                meshes['%s_0' % layer] = cat_flap[0]
                meshes['%s_1' % layer] = cat_flap[1]
                del meshes[layer]

        # sounds depth
        object_win_size = [8, 8]
        for sound, mpos in self.sounds.items():
            for pos, radius in mpos:
                dmap = pos[2]
                win = self.depth_wins[dmap]
                z = self.get_depth(pos, win.view(), object_win_size)  # + 10.
                pos[2] = z


    def attach_arrows_to_text(self, meshes, with_squares=False):
        # find text attached to each arrow
        for arrow in self.arrow_groups:
            mesh_l = meshes.get(arrow)
            if mesh_l:
                if not isinstance(mesh_l, list):
                    mesh_l = [mesh_l]
                for mesh in mesh_l:
                    text_o = self.find_text_for_arrow(meshes, mesh)
                    if text_o:
                        props = text_o['properties']
                        pos = props['position']
                        vert = mesh.vertex()
                        size = props['size']
                        vert2 = aims.vector_POINT3DF(vert)
                        decal = aims.Point3df(pos[0], pos[1], vert[0][2]) \
                            - vert[0]
                        #print('decal text', text_o['objects'][0]['properties']['text'], list(decal), 'to:', pos, ', size', size)
                        n = len(vert)
                        for i, v in enumerate(vert):
                            v += decal * float(n - i) / n
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
                     == 'bord_sud'][0]
        self.main_group = 'bord_sud'
        bounds = self.boundingbox(layer)
        print('ground grid bounds:', bounds)
        interval = 5.
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
        return mesh


    def make_skull_model(self, xml):
        cm = CataMapTo2DMap()
        protos = cm.find_protos(xml)
        skproto = protos['label'].get('ossuaire')
        if skproto is None:
            return
        self.main_group = 'ossuaire'
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
            "Couloirs",
            "Ossuaire officiel",
        ]
        json_obj['default_categories'] = def_categories
        # json_obj['code'] = 1664  # code for private things

        if 'meshes' in summary:
            jmeshes = []
            pmeshes = []
            for filename, mesh in six.iteritems(summary['meshes']):
                filename = os.path.basename(filename)
                if '.' in filename:  # remove extension
                    filename = '.'.join(filename.split('.')[:-1])
                layer = 0
                if 'profondeur' in filename or 'bord' in filename:
                    continue  # skip
                if '_tech_' in filename or 'techniques' in filename \
                        or 'gtech' in filename or 'ebauches' in filename \
                        or 'metro' in filename:
                    layer = 5
                elif filename.startswith('plaques ') \
                        or u' flèches' in filename \
                        or filename.startswith('etiage_'):
                    layer = 2
                elif 'parcelles' in filename:
                    layer = 3
                elif 'oss off' in filename:
                    layer = 4
                elif filename.startswith('anciennes ') \
                        or 'anciennes galeries' in filename \
                        or filename.startswith('aqueduc') \
                        or filename.startswith('ex-') \
                        or ' inaccessibles' in filename:
                    layer = 1
                elif filename.startswith('remblai'):
                    layer = 6
                elif filename.startswith('calcaire'):
                    layer = 7
                elif u'légende' in filename or 'grandes plaques' in filename:
                    layer = 8
                elif 'grille surface' in filename:
                    layer = 9
                size = os.stat(os.path.join(dirname, filename + '.obj')).st_size
                # hash
                md5 = hashlib.md5(open(os.path.join(dirname, filename + '.obj'),
                                       'rb').read()).hexdigest()
                if 'private' in filename:
                    pmeshes.append([layer, filename, size, md5])
                else:
                    jmeshes.append([layer, filename, size, md5])

            json_obj['meshes'] = sorted(jmeshes)
            json_obj['meshes_private'] = sorted(pmeshes)

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
            json_obj['sounds'] = [(os.path.join('sounds', s), self.sounds[s])
                                  for s in sorted(self.sounds.keys())]

        if json_filename is not None:
            if six.PY3:
                json.dump(json_obj, open(json_filename, 'w'), indent=4,
                        sort_keys=False, ensure_ascii=False)
            else:
                json.dump(json_obj, open(json_filename, 'w'), indent=4,
                        sort_keys=False, ensure_ascii=False, encoding='utf-8')

        return json_obj



class CataMapTo2DMap(svg_to_mesh.SvgToMesh):

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
                      == u'légende'][0]
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
        rep_child = ['PE', 'PS', 'PSh', 'sans', 'PS sans',
                      u'échelle', u'\xc3\xa9chelle', 'P ossements', ]
        repl_map = {'id': ids, 'label': labels}
        for child in symbols:
            eid = child.get('id')
            if eid.endswith('_proto'):
                ptype = eid[:-6]
                element = copy.deepcopy(child)
                element.set('id', eid[:-6])
                item = {'element': element}
                bbox = self.boundingbox(child, trans)
                item['boundingbox'] = bbox
                item['center'] = ((bbox[0][0] + bbox[1][0]) / 2,
                                  (bbox[0][1] + bbox[1][1]) / 2)
                item['trans'] = trans
                if ptype in rep_child:
                    item['children'] = True
                    ids[ptype] = item
                else:
                    labels[ptype] = item
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

            added = element.getchildren()
            todo = added + todo


    def make_shadow_filter(self, xml):
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
        defs = [l for l in xml.getroot()
                if l.tag == '{http://www.w3.org/2000/svg}defs'][0]
        defs.append(f)
        return f


    def add_shadow(self, layer, filter):
        for child in layer:
            style = child.get('style')
            if style is None:
                style = ' '
            else:
                style += '; '
            style += 'filter:url(#%s)' % filter
            child.set('style', style)


    def add_shadows(self, xml):
        shadow = self.make_shadow_filter(xml).get('id')
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
                if label in ('galeries inaccessibles inf',
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
                             'galeries inf private', 'metro'):
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
            x for x in src_xml.getroot().getchildren()
            if x.get('{http://www.inkscape.org/namespaces/inkscape}label')
                == layer_label][0]
        target_layer = [
            x for x in xml.getroot().getchildren()
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
                #x for x in xml.getroot().getchildren()
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
            if label in self.removed_labels:
                to_remove.append(layer)
                labels.append(label)
        print('removing layers:', labels)
        for layer in to_remove:
            xml.getroot().remove(layer)


    def remove_wip(self, xml):
        self.removed_labels.update(
            ('a_verifier', 'indications_big_2010', 'planches',
             'calcaire 2010',
             'work done calc', 'galeries techniques despe'))
        self.do_remove_layers(xml)


    def remove_south(self, xml):
        self.removed_labels.update(
            ('galeries_big_sud',))
        self.do_remove_layers(xml)


    def remove_background(self, xml):
        self.removed_labels.update(('couleur_fond', 'couleur_fond sud',))
        self.do_remove_layers(xml)


    def remove_private(self, xml):
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            if label is None:
                continue
            priv_labels = ['inscriptions', 'inscriptions conso',
                           'inscriptions inaccessibles',
                           u'inscriptions flèches',
                           u'inscriptions flèches inaccessibles',
                           u'inscriptions conso flèches',
                           u'maçonneries private', 'private', ]
            if label in priv_labels or label.endswith(' private') \
                    or 'tech' in label \
                    or label in ('calcaire 2010', 'work done calc'):
                self.removed_labels.add(label)
        self.keep_private = False
        self.remove_wip(xml)

        for layer in xml.getroot():
            print('filter private in', layer.get('{http://www.inkscape.org/namespaces/inkscape}label'))
            todo = [(layer, element) for element in layer]
            print('todo:', len(todo))
            while todo:
                parent, element = todo.pop(0)
                if element.get('visibility') == 'private':
                    print('remove:', element)
                    parent.remove(element)
                else:
                    todo += [(element, item) for item in element]


    def remove_gtech(self, xml):
        self.removed_labels.update(('ebauches', 'galeries techniques',
                                    'PSh gtech', 'PSh vers gtech',
                                    'symboles gtech', 'eau gtech',
                                    'galeries private', 'chatieres private',
                                    'private', u'curiosités private',
                                    'symboles private', 'salles vdg private',
                                    u'salles flèches private',
                                    u'curiosités flèches private',
                                    u'rues v1 private',
                                    u'rues v1 flèches private',
                                    'raccords gtech 2D',
                                    'metro',
                                    u'curiosités flèches GTech',
                                    u'échelle gtech',
                                    u'plaques de puits GTech',
                                    u'échelle vers gtech',
                                    u'plaques de puits GTech',
                                    'annotations metro',
        ))
        self.do_remove_layers(xml)


    def remove_igc(self, xml):
        self.removed_labels.update(('planches', 'planches fond',
        ))
        self.do_remove_layers(xml)


    def remove_non_printable1(self, xml):
        self.removed_labels.update(
            ['masque bg', 'masques v1', u'd\xe9coupage',
             'chatieres old',
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
             'chatieres old',
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
             'chatieres old',
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


    def remove_non_printable2(self, xml):
        self.removed_labels.update(
            ['galeries agrandissements',
             'masque vdg', u'masque cimetière',
             'masque plage'])
        self.do_remove_layers(xml)


    def remove_non_printable_igc_private(self, xml):
        self.removed_labels.update(
            ['masque bg', 'masques v1', u'd\xe9coupage',
             'chatieres old',
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
            if label.startswith('calcaire'):
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
            if label == u'l\xe9gende':
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
            'igc': {
                'galeries': {'bg': '#5dd400ff'},
                'galeries big sud': {'bg': '#5dd400ff'},
                'galeries private': {'bg': '#5dd400ff'},
                'galeries inf': {'bg': '#076552ff'},
                'galeries inf private': {'bg': '#076552ff'},
                'galeries techniques': {'bg': '#5c99d976',
                                        'fg': '#4f5eaaff'},
                'plaques de puits': {'bg': '#424242ff'},
                'plaques de puits inaccessibles': {'bg': '#424242ff'},
                'plaques de puits GTech': {'bg': '#424242ff'},
                'annotations': {'bg': '#424242ff'},
                'annotations metro': {'bg': '#424242ff'},
                'zones': {'bg': '#424242ff'},
                'rues sans plaques': {'bg': '#424242ff'},
                'rues inf': {'bg': '#3a3c68ff'},
                u'curiosités inf': {'bg': '#8c620dff'},
                u'curiosités vdg': {'bg': '#5b601fff'},
                u'curiosités vdg private': {'bg': '#5b601fff'},
                u'curiosités': {'bg': '#5b601fff'},
            },
            'bator': {
                'galeries': {'bg': '#ff9e00ff'},
                'galeries big sud': {'bg': '#ff9e00ff'},
                'galeries private': {'bg': '#ff9e00ff'},
                'galeries techniques': {'bg': '#ece84976',
                                        'fg': '#aa9f4fff'},
                'metro': {'bg': '#9bc06e64',
                          'fg': '#94be55ff'},
            },
            'black': {
                'couleur_fond': {'bg': '#000000ff'},
                'couleur_fond sud': {'bg': '#000000ff'},
                'galeries': {'bg': '#0f50ffff',
                             'fg': '#ffffffff',
                             'stroke-width': '0.2'},
                'galeries big sud': {'bg': '#0f50ffff',
                                     'fg': '#ffffffff'},
                'galeries private': {'bg': '#0f50ffff',
                                     'fg': '#ffffffff'},
                'galeries inf': {'bg': '#9abde7ff',
                                 'fg': '#ffffffff'},
                'galeries inf private': {'bg': '#9abde7ff',
                                         'fg': '#ffffffff'},
                'calcaire 2010': {'bg': '#50505000',
                                  'fg': '#60606000'},
                'calcaire ciel ouvert': {'bg': '#50505000',
                                         'fg': '#60606000'},
                'calcaire masse2': {'bg': '#50505000',
                                    'fg': '#60606000'},
                'calcaire masse': {'bg': '#50505000',
                                   'fg': '#60606000'},
                'calcaire med': {'bg': '#50505000',
                                 'fg': '#60606000'},
                'calcaire sup': {'bg': '#50505000',
                                 'fg': '#60606000'},
                'calcaire inf': {'bg': '#50505000',
                                 'fg': '#60606000'},
                'agrandissements fond': {'bg': '#01202bff',
                                 'fg': '#88b0caff'},
                'parcelles': {'fg': '#bee0e65d'},
                'salles v1': {'bg': '#c5c5c5ff'},
            },
        }
        for k, v in six.iteritems(colorsets):
            print(k, v)
            v['galeries big sud'] = v['galeries']
        colors = colorsets[colorset]
        layers = {'galeries': 'sup',
                  'galeries big sud': 'sup',
                  'galeries inf': 'inf'}
        legend_layer = None
        for layer in xml.getroot():
            label = layer.get(
                '{http://www.inkscape.org/namespaces/inkscape}label')
            corridor_colors = colors.get(label)
            if not corridor_colors:
                if label == u'légende':
                    legend_layer = layer
                continue
            bg = corridor_colors.get('bg')
            op = 1.
            fill_op = 1.
            if bg and len(bg) >= 7:
                fill_op = float(eval('0x%s' % bg[-2:])) / 256.
                bg = bg[:-2]
            fg = corridor_colors.get('fg')
            if fg and len(fg) >= 7:
                op = float(eval('0x%s' % fg[-2:])) / 256.
                fg = fg[:-2]

            todo = layer[:]
            while todo:
                item = todo.pop()
                if len(item) != 0:
                    todo += item[:]
                style = self.get_style(item)
                if style:
                    if bg and 'fill' in style:
                        style['fill'] = bg
                    style['fill-opacity'] = str(fill_op)
                    if fg and 'stroke' in style:
                        style['stroke'] = fg
                    style['opacity'] = str(op)
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
                    if bg and 'fill' in style:
                        style['fill'] = bg
                    if fg and 'stroke' in style:
                        style['stroke'] = fg
                    self.set_style(item, style)


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


    def build_2d_map(self, xml, keep_private=True, wip=False,
                     filters=[]):
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
            'remove_zooms': self.remove_zooms,
            'remove_gtech': self.remove_gtech,
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
            'printable_map': ['remove_non_printable1', 'show_all',
                              #'add_shadow',
                              'shift_inf_level', 'replace_symbols', 'date',
                              'zooms', 'remove_non_printable2', 'remove_igc'],
            'poster_map': ['remove_non_printable1_main', 'show_all',
                           #'add_shadow',
                           'shift_inf_level', 'replace_symbols', 'date',
                           'zooms', 'remove_non_printable2', 'remove_igc'],
            'printable_map_public': ['remove_non_printable1_pub', 'show_all',
                              #'add_shadow',
                              'shift_inf_level', 'replace_symbols', 'date',
                              'zooms', 'remove_non_printable2', 'remove_igc'],
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
                    'layer_opacity=["planches fond", "0.44"]'],
            'igc_private': ['remove_wip', 'remove_non_printable_igc_private',
                    'remove_non_printable2',
                    'remove_background', 'remove_limestone', 'remove_zooms',
                    'remove_other=["raccords plan 2D", "parcelles", '
                                  '"raccords gtech 2D"]',
                    'show_all', 'add_shadow', 'date', 'recolor="igc"',
                    'layer_opacity=["planches fond", "0.44"]'],
        }

        map_2d = copy.deepcopy(xml)
        self.xml = map_2d
        self.removed_labels = set()
        self.keep_private = True
        self.keep_transformed_properties = set(('level', 'map_transform'))

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
    ver = [int(x) for x in over.strip().split()[1].split('.')]
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

def convert_to_jpg(png_file, remove=True):
    # warning: https://github.com/ImageMagick/ImageMagick/issues/396
    # ImageMagick cache (disk limit) size may be too small.
    # edit /etc/ImageMagick-6/policy.xml and change disk resource limit.
    #  <policy domain="resource" name="memory" value="12GiB"/>
    #  <policy domain="resource" name="map" value="20GiiB"/>
    #  <policy domain="resource" name="width" value="50KP"/>
    #  <policy domain="resource" name="height" value="50KP"/>
    #  <policy domain="resource" name="area" value="20GiB"/>
    #  <policy domain="resource" name="disk" value="80GiB"/>
    subprocess.check_call(
        ['convert', '-quality', '98', '-background', 'white', '-flatten',
         '-alpha', 'on',
          png_file, png_file.replace('.png', '.jpg')])
    if remove:
        os.unlink(png_file)


def main():

    do_2d = False
    do_3d = False
    do_igc = False
    do_igc_private = False
    do_split = False
    do_join = False
    do_recolor = False
    if '--2d' in sys.argv:
        do_2d = True
    if '--3d' in sys.argv:
        do_3d = True
    if '--igc' in sys.argv:
        do_igc = True
    if '--igc_private' in sys.argv:
        do_igc_private = True
    if '--split' in sys.argv:
        do_split = True
    if '--join' in sys.argv:
        do_join = True
    if '--color' in sys.argv:
        do_recolor = True
        i = sys.argv.index('--color')
        colorset = sys.argv[i + 1]
        del sys.argv[i]
        del sys.argv[i]
    if '-h' in sys.argv or '--help' in sys.argv:
        print('python -m catamap [--2d] [--3d] [--igc] [--split] '
              '[--join] [input_file.svg] [output_3d_dir]')
        sys.exit(1)

    #from anatomist import headless as ana
    #a = ana.HeadlessAnatomist()

    svg_filename = 'plan_14_fdc_2019_06_16.svg'
    out_dirname = 'meshes_obj'

    files = [x for x in sys.argv[1:] if not x.startswith('-')]
    if len(files) >= 1:
        svg_filename = files[0]
        if len(files) >= 2:
            out_dirname = files[1]
            if len(files) > 2:
                raise ValueError('unrecognized arguments')

    if do_3d:
        svg_mesh = CataSvgToMesh()
    else:
        svg_mesh = CataMapTo2DMap()
    #svg_mesh.debug = True

    if do_3d or do_2d or do_igc or do_igc_private or do_split or do_recolor:
        print('reading SVG...')
        xml_et = svg_mesh.read_xml(svg_filename)
    if do_3d:
        print('extracting meshes...')
        meshes = svg_mesh.read_paths(xml_et)
        svg_mesh.postprocess(meshes)

        print('saving meshes...')
        summary = svg_mesh.save_mesh_dict(
            meshes, out_dirname, ('.obj', 'WAVEFRONT'), ('.obj', 'WAVEFRONT'),
            'map_objects.json',
            svg_filename.replace('.svg', '_imprimable_private.jpg'))


    if do_2d or do_igc or do_igc_private or do_recolor or do_split or do_join:
        # -- 2D map
        svg2d = CataMapTo2DMap()
    if do_2d:
        # xml_et = svg2d.read_xml(svg_filename)
        col_filter = []
        if do_recolor:
            col_filter = ['recolor="%s"' % colorset]
        map2d = svg2d.build_2d_map(
            xml_et, filters=['remove_wip', 'printable_map'] + col_filter)
        svg2d.clip_page(map2d, 'rect15021-0')
        map2d.write(svg_filename.replace(
            '.svg', '_imprimable_private_flat.svg'))
        svg2d.add_shadows(map2d)
        map2d.write(svg_filename.replace('.svg', '_imprimable_private.svg'))
        # re-clip private map for poster (without south)
        map2d_poster = svg2d.build_2d_map(
            xml_et, filters=['remove_wip', 'poster_map'] + col_filter)
        svg2d.clip_page(map2d_poster, 'rect15021')
        map2d_poster.write(svg_filename.replace(
            '.svg', '_poster_private_flat.svg'))
        svg2d.add_shadows(map2d_poster)
        map2d_poster.write(svg_filename.replace('.svg',
                                                '_poster_private.svg'))
        # WIP
        map2d_wip = svg2d.build_2d_map(
            xml_et, filters=['printable_map'] + col_filter)
        svg2d.clip_page(map2d_wip, 'rect15021-0')
        map2d_wip.write(svg_filename.replace(
            '.svg', '_imprimable_private_wip_flat.svg'))
        svg2d.add_shadows(map2d_wip)
        map2d_wip.write(svg_filename.replace('.svg',
                                             '_imprimable_private_wip.svg'))
        map2d_pub = svg2d.build_2d_map(
            xml_et, filters=['remove_private', 'remove_gtech', 'printable_map_public'] + col_filter)
        svg2d.clip_page(map2d_pub, 'rect15021')
        map2d_pub.write(svg_filename.replace(
            '.svg', '_imprimable_flat.svg'))
        svg2d.add_shadows(map2d_pub)
        map2d_pub.write(svg_filename.replace('.svg', '_imprimable.svg'))

        # build bitmap and pdf versions
        # public
        export_png(svg_filename.replace('.svg', '_imprimable.svg'), 180,
                   'rect15021')
        export_pdf(svg_filename.replace('.svg', '_imprimable_flat.svg'))
        os.unlink(svg_filename.replace('.svg', '_imprimable_flat.svg'))

        convert_to_jpg(svg_filename.replace('.svg', '_imprimable.png'))

        # private
        export_png(svg_filename.replace('.svg', '_imprimable_private.svg'),
                   180, 'rect15021-0')
        export_pdf(svg_filename.replace('.svg',
                                        '_imprimable_private_flat.svg'))
        os.unlink(svg_filename.replace('.svg', '_imprimable_private_flat.svg'))
        convert_to_jpg(svg_filename.replace('.svg', '_imprimable_private.png'))

        # private poster
        export_png(svg_filename.replace('.svg', '_poster_private.svg'),
                   360, 'rect15021')
        #export_pdf(svg_filename.replace('.svg',
                                        #'_poster_private_flat.svg'))
        os.unlink(svg_filename.replace('.svg', '_poster_private_flat.svg'))
        # convert segfaults on this with the image at 360 dpi
        convert_to_jpg(svg_filename.replace('.svg', '_poster_private.png'))

        # private - WIP
        export_png(svg_filename.replace('.svg', '_imprimable_private_wip.svg'),
                   180, 'rect15021-0')
        export_pdf(svg_filename.replace('.svg',
                                        '_imprimable_private_wip_flat.svg'))
        os.unlink(svg_filename.replace('.svg',
                                       '_imprimable_private_wip_flat.svg'))
        convert_to_jpg(svg_filename.replace('.svg',
                                            '_imprimable_private_wip.png'))

    if do_igc:
        map2d_igc = svg2d.build_2d_map(
            xml_et, filters=['igc'])
        svg2d.clip_page(map2d_igc, 'rect15021')
        #svg2d.clip_page(map2d_igc, 'rect15021-0')
        svg2d.add_shadows(map2d_igc)
        map2d_igc.write(svg_filename.replace('.svg', '_igc.svg'))
        # build bitmap and pdf versions
        #export_png(svg_filename.replace('.svg', '_igc.svg'), 180,
                   #'rect15021-0', ignore_errors=True)
        export_png(svg_filename.replace('.svg', '_igc.svg'), 180,
                   'rect15021', ignore_errors=True)
        convert_to_jpg(svg_filename.replace('.svg', '_igc.png'))
        #export_pdf(svg_filename.replace('.svg', '_igc.svg'))

    if do_igc_private:
        map2d_igcp = svg2d.build_2d_map(
            xml_et, filters=['igc_private'])
        for layer in map2d_igcp.getroot():
            if layer.get(
                    '{http://www.inkscape.org/namespaces/inkscape}label') \
                        == 'planches fond':
                print('planches style:', layer.get('style'))
                break
        #svg2d.clip_page(map2d_igcp, 'rect15021')
        svg2d.clip_page(map2d_igcp, 'rect15021-0')
        svg2d.add_shadows(map2d_igcp)
        map2d_igcp.write(svg_filename.replace('.svg', '_igc_private.svg'))
        # build bitmap and pdf versions
        export_png(svg_filename.replace('.svg', '_igc_private.svg'), 300,
                   'rect15021-0', ignore_errors=True)
        #export_png(svg_filename.replace('.svg', '_igc_private.svg'), 300,
                   #'rect15021', ignore_errors=True)
        #export_png(svg_filename.replace('.svg', '_igc_private.svg'),
                   #300, 'bord_sud', ignore_errors=True,
                   #out_file=svg_filename.replace(
                      #'.svg', '_igc_sud_private.png'))
        convert_to_jpg(svg_filename.replace('.svg', '_igc_private.png'))
        #convert_to_jpg(svg_filename.replace('.svg', '_igc_sud_private.png'))
        #export_pdf(svg_filename.replace('.svg', '_igc.svg'))

    if do_split:
        map2d_split = svg2d.build_2d_map(
            xml_et, filters=['split_layers="default"'])
        for i, m in enumerate(map2d_split.result[-1]):
            m.write(svg_filename.replace('.svg', '_%d.svg' % i))

    if do_join:
        map2d_join = svg2d.build_2d_map(
            None, filters=['join_layers="%s"' % svg_filename])
        map2d_join.write(svg_filename.replace('.svg', '_joined.svg'))

if __name__ == '__main__':
    main()
