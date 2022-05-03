#!/usr/bin/env python

import json
import os
import os.path as osp
import sys
import json
import argparse


def get_missing_media(obj_map):

    with open(obj_map) as f:
      objects = json.load(f)

    all_missing = {}

    for section in ('photos', 'photos_private', 'sounds', 'sounds_private'):
        s_obj = objects.get(section)
        if s_obj is None:
            continue
        missing = []
        for items in s_obj:
            for item in items[1]:
                if not os.path.exists(item):
                    missing.append((item, items[0]))
        if missing:
            all_missing[section] = missing

    return all_missing


def print_missing_media(obj_map):

    all_missing = get_missing_media(obj_map)
    for section, missing in all_missing.items():
        print('missing in section:', section, ':')
        for item in missing:
            print(item[0], item[1])


if __name__ == '__main__':
    obj_map = 'map_objects.json'

    parser = argparse.ArgumentParser(
        prog='catamap.missing_media',
        description='Get and print missing "media" files (generally photos, '
        'videos, sounds) referenced in a 3D processed SVG map file. '
        'The program analyses the resulting "map_objects.json" file (see the '
        '"catamap" program doc) and prints media files which are used there '
        'but not present on disk in the media directories (photos/, '
        'sounds/...)')
    parser.add_argument(
        'obj_map', nargs='?', default=obj_map,
        help='map_objects.json file produced by the 3D generation of the '
        '"catamap" program (which must be run before) (default: %s)' % obj_map)

    options = parser.parse_args()
    obj_map = options.obj_map

    print_missing_media(obj_map)

