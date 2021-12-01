#!/usr/bin/env python

'''

BDAlti maps module
==================

Convertion tools for BDAlti maps (https://geoservices.ign.fr/documentation/diffusion/telechargement-donnees-libres.html#bd-alti) and their use in :mod:`catamap`.

API
---
'''

from __future__ import print_function

import numpy as np
import os
import glob
try:
    from soma import aims
except ImportError:
    # allow toi generate docs without aims
    aims = None
import json
import math

osp = os.path


def get_map_image(xi, yi, meta_map, base):
    '''
    get image at coords xi, yi in the map table. Lazy load and cache it.
    '''
    # print(xi, yi)
    metadata = meta_map['table'][yi][xi]
    if metadata is None:
        return None
    image = metadata.get('image')
    if not image:
        fname = osp.join(base, 'raw_images', metadata['file'])
        print('load altitude map:', fname)
        image = aims.read(fname)
        metadata['image'] = image
    return image


def get_z(x, y, meta_map, base, background_z=-99999.00):
    '''
    get the altitude from (x, y) coords in Lambert93 coords
    '''
    xpos = meta_map['xllcorners']
    x0 = x - xpos[0]
    cs = meta_map['cellsize']
    xi = int(x0 / cs)
    if xi < 0 or xi >= len(xpos):
        return background_z
    x1 = x0 / cs - xi

    ypos = meta_map['yllcorners']
    y0 = y - ypos[0]
    # cs = meta_map['cellsize']
    yi = int(y0 / cs)
    if yi < 0 or yi >= len(ypos):
        return background_z
    y1 = y0 / cs - yi

    image = get_map_image(xi, yi, meta_map, base)
    if image is None:
        return background_z

    x2 = int(x1 * image.getSizeX())
    y2 = int(y1 * image.getSizeY())
    # print('  ->', x2, y2)
    z = image.at(x2, image.getSizeY() - y2 - 1)
    if z == image.header()['NODATA_value']:
        z = background_z

    return z


def convert_raw_map(fname, out_fname):
    '''
    convert one raw map from bdalti (.asc) to .ima format
    '''
    with open(fname) as f:
        lines = f.readlines()

    types = {
        'ncols': int,
        'cellsize': float,
        'xllcorner': float,
        'yllcorner': float,
        'NODATA_value': float,
    }

    metadata = {}
    for l in lines[:6]:
        item = l.strip().split()
        k = item[0]
        metadata[k] = types.get(k, str)(item[1])

    # print(metadata)
    image = aims.Volume((int(metadata['ncols']), int(metadata['nrows'])),
                        dtype='float')
    array = np.asarray(image)
    for i, l in enumerate(lines[6:]):
        array[:, i, 0, 0] = [float(x) for x in l.strip().split()]

    image.header().update(metadata)
    aims.write(image, out_fname)


def convert_raw_maps(fnames, out_fnames):
    '''
    convert all raw data files from bdalti (.asc) to .ima format

    fnames:
        input files pattern (used with glob.glob())
    out_fnames:
        output files pattern, should contain a "%s" pattern
    '''
    for fname in glob.glob(fnames):
        bname = osp.basename(fname)
        out_fname = out_fnames % bname.split('.')[0]
        convert_raw_map(fname, out_fname)


def build_meta_table(ima_fnames):
    '''
    build the metadata table from converted .ima files

    ima_fnames: pattern with a "%s", same as out_fnames in convert_raw_maps()
    '''
    meta_keys = ['cellsize', 'xllcorner', 'yllcorner']
    pos_table = []
    for fname in glob.glob(ima_fnames % '*'):
        print(fname)
        f = aims.Finder()
        if f.check(fname):
            header = f.header()
            metadata = {k: float(header[k]) for k in meta_keys}
            metadata['file'] = osp.basename(fname)
            pos_table.append(metadata)

    print(pos_table)

    xpos = sorted(set([p['xllcorner'] for p in pos_table]))
    ypos = sorted(set([p['yllcorner'] for p in pos_table]))

    meta_table = [[None for x in range(len(xpos))] for y in range(len(ypos))]

    for metadata in pos_table:
        meta_table[ypos.index(metadata['yllcorner'])] \
            [xpos.index(metadata['xllcorner'])] = metadata

    meta_map = {'table': meta_table,
                'xllcorners': xpos,
                'yllcorners': ypos,
                'cellsize': xpos[1] - xpos[0]}

    return meta_map


# ----

if __name__ == '__main__':

    base = '/volatile/home/denis/catacombes/plans/14/plan_14_2017/altitude/BDALTIV2_2-0_75M_ASC_LAMB93-IGN69_FRANCE_2020-04-28/BDALTIV2'
    fnames = osp.join(base, '1_DONNEES_LIVRAISON_2020-05-00201/BDALTIV2_MNT_75M_ASC_LAMB93_IGN69_FRANCE/*.asc')
    out_fnames = osp.join(base, 'raw_images/%s.ima')
    out_map = osp.join(base, 'map.json')

    # ---

    #convert_raw_maps(fnames, out_fnames)

    # ---

    #meta_map = build_meta_table(out_fnames)

    #with open(out_map, 'w') as f:
        #json.dump(meta_map, f)

    # ----

    with open(out_map) as f:
        meta_map = json.load(f)

    coords = [(648076.25, 6858784.37),
              (651831.92, 6857938.91),
              (652528.99, 6861468.52)]
    ztest = [58.24, 59.8, 26.97]

    for c, zt in zip(coords, ztest):
        z = get_z(c[0], c[1], meta_map, base)
        print(c, ', z:', z, ', expected:', zt, '(D=%f)' % (z - zt))

