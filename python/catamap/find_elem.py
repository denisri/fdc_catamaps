import xml.etree.cElementTree as ET
import json
import argparse


parser = argparse.ArgumentParser(
    description='find elements in a SVG file, tell where they are in the '
    'XML tree')
parser.add_argument('svg', help='.svg file to parse')
parser.add_argument(
    'props', nargs='+',
    help='properties to find. JSON dict, keys are XML properties, '
    'values are matched. special keys "tag" and "text" are for the element '
    'tag and text. Several properties dicts may be given. In that cases, the '
    'searched items tree must match all the properties dicts in their path: '
    'this allows to select branches where to look for the items.\n'
    'ex: \'{"id": "layer35"}\' \'{"text": "10"}\' will look for elements with '
    'the text "10" located inside a subtree which id is "layer35".')
opts = parser.parse_args()


svg_f = opts.svg
props = [json.loads(x) for x in opts.props]

svg = ET.parse(svg_f)

todo = [[[svg.getroot()], 0]]
found = []
while todo:
    path, depth = todo.pop()
    elem = path[-1]
    etag = elem.tag
    xfound = True
    for k, v in props[depth].items():
        if k == 'tag':
            tag = elem.tag
            if '{' in v:
                if v != tag:
                    xfound = False
                    break
            else:
                xt = tag.rsplit('}', 1)[-1]
                if xt != v:
                    xfound = False
                    break
        elif k == 'text':
            if elem.text != v:
                xfound = False
                break
        else:
            xval = elem.get(k)
            if xval != v:
                xfound = False
                break
    if xfound:
        if depth == len(props) - 1:
            found.append(path)
        else:
            depth += 1
    todo += [[path + [x], depth] for x in elem]

print('found:', len(found), '\n')
# print(found)
for i, path in enumerate(found):
    print('match', i, ':')
    for j, item in enumerate(path[:-1]):
        tag = item.tag.rsplit('}', 1)[-1]
        print(f'{"    " * j}tag: {tag}')
        print(f'{"    " * j}id: {item.get("id")}')
    j = len(path) - 1
    item = path[-1]
    print(f'{"    " * j}tag: {item.tag.rsplit("}}", 1)[-1]}')
    for k in sorted(item.keys()):
        v = item.get(k)
        print(f'{"    " * j}{k}: {v}')
    print(f'{"    " * j}text: {item.text}')
