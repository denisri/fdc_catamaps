#!/usr/bin/env python

import xml.etree.cElementTree as ET

svg_filename = 'altitude/raw/assemblage.svg'
out_filaname = svg_filename.replace('/raw/', '/real/')

xml = ET.parse(svg_filename)

root = xml.getroot()
layer = [l for l in root if l.tag.endswith('}g')][0]
props = ['{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}absref', 'sodipodi:absref']
todo = list(layer[:])
while todo:
    item = todo.pop(0)
    if item.tag.endswith('}g'):
        todo += item[:]
        continue
    if item.tag.endswith('image'):
        for prop in props:
            fname = item.get(prop)
            if fname is not None:
                nname = fname.replace('/raw/', '/real/')
                item.set(prop, nname)

xml.write(out_filaname)

