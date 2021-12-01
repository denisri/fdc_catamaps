#!/usr/bin/env python
# coding: UTF-8

'''
diff_svg module
===============

Print differences between two SVG maps.

Uses the yaml module (``pip install pyyaml``).

The output is a hierarchical dictionary of differences between the two maps. Differences in tags (properties) and children are recorded. Item keys are their "id" property, which should be unique in the files, and are displayed hierarchically.

Used as a program, the output is in YAML format (mostly human readable)

To use it, try::

    python -m catamap.diff_svg --h

It will print the command doc and parameters.

diff_svg module API
-------------------
'''

import xml.etree.cElementTree as ET
import sys
import yaml
import argparse

size_limit = 1000


def diff_element(el1, el2, verbose_depth=0, verbose_depth_max=1):

    '''
    Compare two SVG XML trees, record differences in both properties and
    children in a readable dictionary.
    '''

    diff_d = {}
    ch1 = set([child.get('id') for child in el1])
    ch2 = set([child.get('id') for child in el2])

    # properties (tags)9536d8a6740e0ae758e20faad947a7ca14500354
    if el1.items() != el2.items():
        keys1 = set(el1.keys())
        keys2 = set(el2.keys())
        only_k1 = keys1.difference(keys2)
        only_k2 = keys1.difference(keys2)
        inter_k = keys1.intersection(keys2)
        props = {}
        if only_k1:
            props['only_in_1'] = sorted(only_k1)
        if only_k2:
            props['only_in_2'] = sorted(only_k2)
        dval = {}
        for prop in inter_k:
            v1 = el1.get(prop)
            if len(v1) > size_limit:
                v1 = '<value too large, size: %d>' % len(v1)
            v2 = el2.get(prop)
            if len(v2) > size_limit:
                v2 = '<value too large, size: %d>' % len(v2)
            if v1 != v2:
                dval[prop] = {'in_1': v1, 'in_2': v2}
        if dval:
            props['differing_values'] = dval
        if props:
            diff_d['id'] = el1.get('id')
            diff_d['props_diffs'] = props

    # children
    if ch1 != ch2:
        diff_d['id'] = el1.get('id')

    only_1 = ch1.difference(ch2)
    if only_1:
        diff_d['only_in_1'] = sorted(only_1)
    only_2 = ch2.difference(ch1)
    if only_2:
        diff_d['only_in_2'] = sorted(only_2)

    inters = ch1.intersection(ch2)
    ch_diffs = {}
    if verbose_depth <= verbose_depth_max and diff_d:
        print('element', el1.get('id'), 'differs')
    for ch in inters:
        ch1 = [item for item in el1 if item.get('id') == ch][0]
        ch2 = [item for item in el2 if item.get('id') == ch][0]
        ch_diff = diff_element(ch1, ch2, verbose_depth + 1, verbose_depth_max)
        if ch_diff:
            ch_diffs[ch] = ch_diff
            if verbose_depth <= verbose_depth_max:
                print('child element', ch, 'differs')
    if ch_diffs:
        diff_d['children_diff'] = ch_diffs

    return diff_d


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='diff_svg',
        description='Print differences between two SVG maps.')
    parser.add_argument('-i', '--svg1', help='1st SVG file to be compared')
    parser.add_argument('-j', '--svg2', help='2nd SVG file to be compared')
    parser.add_argument(
        '-o', '--output', help='output YAML file (default: use stdout)')
    parser.add_argument('other', nargs='*')
    options = parser.parse_args()

    svg1 = options.svg1
    svg2 = options.svg2
    out = options.output
    other = options.other
    if svg1 is None and other:
        svg1 = other.pop(0)
    if svg2 is None and other:
        svg2 = other.pop(0)
    if out is None and other:
        out = other.pop(0)
    if other:
        print('unrecognized arguments:', other, file=sys.stderr, end='\n\n')
        parser.parse_args([sys.argv[0], '-h'])
        sys.exit(1)

    print('read', svg1, '...')
    xml1 = ET.parse(svg1)
    print('read', svg2, '...')
    xml2 = ET.parse(svg2)

    print('compare...')
    diff_d = diff_element(xml1.getroot(), xml2.getroot())

    print('diff:')
    if out:
        with open(out, 'w') as f:
            print(yaml.dump(diff_d), file=f)
    else:
        print(yaml.dump(diff_d), file=f)

