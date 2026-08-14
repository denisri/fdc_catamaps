#!/usr/bin/env python

import argparse
import PIL
from PIL import Image
import math
import os
import os.path as osp


default_nscales = 3
default_subdivisions = 16
default_downscale = 4


def main():
    parser = argparse.ArgumentParser(
        prog='build_multiscale_map',
        description='Build multi-scale tiles from a 2D map')
    parser.add_argument('-i', '--input', help='2D map image to be tiled')
    parser.add_argument(
        '-o', '--output',
        help='output main directory. Sub-dirs will be created there for scale '
        'levels')
    parser.add_argument(
        '-n', '--num-scales', default=default_nscales, type=int,
        help=f'number of scales (default={default_nscales}')
    parser.add_argument(
        '-b', '--basename',
        help='output images base name. Default: same as input')
    parser.add_argument(
        '-e', '--extension',
        help='output format extension. default: same as input')
    parser.add_argument(
        '-s', '--subdivide', type=int, default=default_subdivisions,
        help='number of subdivisions (on each dimension), '
        f'default: {default_subdivisions}')
    parser.add_argument(
        '-d', '--downscale', type=int, default=default_downscale,
        help='image downscale factor at each scale level, '
        f'default: {default_downscale}')
    options = parser.parse_args()

    input_image = options.input
    output_dir = options.output
    nscales = options.num_scales
    out_ext = options.extension
    out_basename = options.basename
    scale_div = options.subdivide
    downscale = options.downscale

    if osp.isdir(input_image):
        input_images = [osp.join(input_image, x)
                        for x in os.listdir(input_image)]
    else:
        input_images = [input_image]

    Image.MAX_IMAGE_PIXELS = 50000 * 50000

    for input_image in input_images:
        print('reading full image map', input_image)
        if out_basename is None:
            out_bname = osp.basename(input_image)
        else:
            out_bname = out_basename
        for scale in range(nscales):
            os.makedirs(osp.join(output_dir, f'{scale:02d}'), exist_ok=True)
        basename, ext = osp.basename(out_bname).rsplit('.', 1)
        if out_ext is not None:
            ext = out_ext
        try:
            with Image.open(input_image) as im:
                print('w:', im.width, ', h:', im.height)
                psize = (int(math.ceil(im.width / scale_div)),
                         int(math.ceil(im.height / scale_div)))
                print('patch size:', psize)
                for y in range(scale_div):
                    for x in range(scale_div):
                        print(x, y)
                        subim = im.crop((x * psize[0], y * psize[1],
                                        (x + 1) * psize[0] - 1,
                                        (y + 1) * psize[1] - 1))
                        for scale in range(nscales):
                            if scale != 0:
                                rsp = subim.resize(
                                    (int(subim.width / downscale),
                                    int(subim.height / downscale)))
                                subim = rsp
                                del rsp
                            lvl = nscales - scale - 1
                            print('level:', lvl, ':', subim.width,
                                  subim.height)
                            fname = osp.join(
                                output_dir, f'{lvl:02d}',
                                f'{basename}_{x:02d}_{y:02d}.{ext}')
                            subim.save(fname)
        except PIL.UnidentifiedImageError:
            print('skipping wrong image', input_image)

if __name__ == '__main__':
    main()
