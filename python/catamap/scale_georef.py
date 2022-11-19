#!/usr/bin/env python
# coding: UTF-8

import argparse
from .map_to_meshes import scale_georef_points_file


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        prog='scale_georef',
        description='Apply scaling to a QGis .points file')
    parser.add_argument('-i', '--input', help='input .points file')
    parser.add_argument('-o', '--output',
                        help='output transformed .points file')
    parser.add_argument('-x', '--xscale', type=float, default=1.,
                        help='X scaling. Default: 1.')
    parser.add_argument('-y', '--yscale', type=float, default=None,
                        help='X scaling. Default: same as xscale')
    options = parser.parse_args()

    in_pts = options.input
    out_pts = options.output
    xscale = options.xscale
    yscale = options.yscale

    scale_georef_points_file(in_pts, out_pts, xscale, yscale)

