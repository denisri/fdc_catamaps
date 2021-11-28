import xml.etree.cElementTree as ET
import sys


def diff_element(el1, el2, verbose_depth=0, verbose_depth_max=1):
    diff_d = {}
    ch1 = set([child.get('id') for child in el1])
    ch2 = set([child.get('id') for child in el2])
    if el1.items() != el2.items() or ch1 != ch2:
        diff_d['id1'] = el1.get('id')
        diff_d['id2'] = el1.get('id')
    only_1 = ch1.difference(ch2)
    if only_1:
        diff_d['only_in_1'] = only_1
    only_2 = ch2.difference(ch1)
    if only_2:
        diff_d['only_in_2'] = only_2

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


svg1 = sys.argv[1]
svg2 = sys.argv[2]

print('read', svg1, '...')
xml1 = ET.parse(svg1)
print('read', svg2, '...')
xml2 = ET.parse(svg2)

print('compare...')
diff_d = diff_element(xml1.getroot(), xml2.getroot())

print('diff:')
print(diff_d)

