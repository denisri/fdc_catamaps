#!/usr/bin/env python

import argparse
import sys
import json
import os
import os.path as osp
import yaml


parser = argparse.ArgumentParser(
    'checks unused photos in photos directories listed in a map_objects.json '
    'file')

parser.add_argument('-i', '--input', default='map_objects.json',
                    help='input map_objects.json file')
parser.add_argument('-o', '--output', help='output file, default="-": stdout')

options = parser.parse_args()

out = options.output
if out in (None, '', '-'):
    out_f = sys.stdout
else:
    out_f = open(out, 'w')

try:
    with open(options.input) as f:
        map_objects = json.load(f)

    dirset = {}
    missing = set()
    dups = []
    unused = []
    markers = map_objects.get('markers', {})
    for mtype, mset in markers.items():
        for pitem in mset:
            photos = pitem[1]
            for photo in photos:
                if isinstance(photo, list):
                    photo = photo[0]
                if not osp.exists(photo):
                    missing.add(photo)
                dir, pname = osp.split(photo)
                pset = dirset.setdefault(dir, set())
                if pname in pset:
                    dups.append(photo)
                else:
                    pset.add(pname)
    print(dirset.keys())
    dups = sorted(dups)
    for d, pset in dirset.items():
        for fname in os.listdir(d):
            if fname.startswith('.') or fname in ('photo_errors.txt',
                                                  'Readme.md'):
                continue
            if fname not in pset:
                unused.append(osp.join(d, fname))
    unused = sorted(unused)
    missing = sorted(missing)

    report = {
        'used_but_not_present': missing,
        'duplicated': dups,
        'unused': unused
    }

    yaml.dump(report, out_f)

finally:
    if out_f is not sys.stdout:
        out_f.close()
