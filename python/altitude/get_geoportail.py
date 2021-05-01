#!/usr/bin/env python

import urllib2
import os

url = 'https://wxs.ign.fr/%(key)s/geoportail/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=%(layer)s&TILEMATRIXSET=PM&TILEMATRIX=%(level)s&TILECOL=%(col)s&TILEROW=%(row)s&STYLE=normal&FORMAT=image/jpeg'

init_level = 12
alt_level = 14
init_col = 2074
init_row = 1409
key = 'choisirgeoportail'
alt_layer = 'ELEVATION.SLOPES'
photo_layer = 'ORTHOIMAGERY.ORTHOPHOTOS'

photo_dir = 'geoportail/photo'
if not os.path.exists(photo_dir):
    os.makedirs(photo_dir)
alt_dir = 'geoportail/alt'
if not os.path.exists(alt_dir):
    os.makedirs(alt_dir)

width = 2**(alt_level - init_level)
heigth = 2**(alt_level - init_level)
print('n images:', width, 'x', heigth, '=', width*heigth)
level = alt_level
col0 = init_col * 2**(alt_level - init_level)
row0 = init_row * 2**(alt_level - init_level)

for row in range(heigth):
    r = row + row0
    for col in range(width):
        c = col + col0
        vars = {
            'key': key,
            'layer': alt_layer,
            'level': level,
            'row': r,
            'col': c,
        }
        print('get image', level, c, r)
        print('url:', url % vars)
        content = urllib2.urlopen(url % vars)
        print(type(content))
        filename = os.path.join(alt_dir, 'alt_%(col)s_%(row)s.jpg' % vars)
        with open(filename, 'wb') as f:
            f.write(content.read())


