#!/usr/bin/env python
#******************************************************************************
#  $Id$
#
#  Name:     gdalcopyproj.py
#  Project:  GDAL Python Interface
#  Purpose:  Duplicate the geotransform and projection metadata from
#	     one raster dataset to another, which can be useful after
#	     performing image manipulations with other software that
#	     ignores or discards georeferencing metadata.
#  Author:   Schuyler Erle, schuyler@nocat.net
#
#******************************************************************************
#  Copyright (c) 2005, Frank Warmerdam
#
#  Permission is hereby granted, free of charge, to any person obtaining a
#  copy of this software and associated documentation files (the "Software"),
#  to deal in the Software without restriction, including without limitation
#  the rights to use, copy, modify, merge, publish, distribute, sublicense,
#  and/or sell copies of the Software, and to permit persons to whom the
#  Software is furnished to do so, subject to the following conditions:
#
#  The above copyright notice and this permission notice shall be included
#  in all copies or substantial portions of the Software.
#
#  THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
#  OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#  FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
#  THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#  LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
#  FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
#  DEALINGS IN THE SOFTWARE.
#******************************************************************************
#
# $Log$

from osgeo import gdal
import sys
import os.path
from argparse import ArgumentParser


def copy_geo_projection(input, output, scale_x=1., scale_y=None, align_x=False,
                        align_y=False):
    dataset = gdal.Open(input)
    if dataset is None:
        print('Unable to open', input, 'for reading')
        sys.exit(1)

    if scale_y is None:
        scale_y = scale_x

    projection   = dataset.GetProjection()
    geotransform = dataset.GetGeoTransform()

    if projection is None and geotransform is None:
        raise ValueError('No projection or geotransform found on file' + input)

    dataset2 = gdal.Open(output, gdal.GA_Update)

    if dataset2 is None:
        raise RuntimeError('Unable to open %s for writing' % output)

    # To know more about GeoTransforms, see https://gdal.org/tutorials/geotransforms_tut.html
    geotransform_new = list(dataset.GetGeoTransform())
    xscale = dataset.RasterXSize / dataset2.RasterXSize
    yscale = dataset.RasterYSize / dataset2.RasterYSize
    if align_x:
        yscale = xscale
    elif align_y:
        xscale = yscale
    # print('xscale:', xscale, ', yscale:', yscale)
    geotransform_new[1] = geotransform_new[1] * xscale * scale_x
    geotransform_new[5] = geotransform_new[5] * yscale * scale_y
    # 2nd and 6th value of GetGeoTransform() is X/Y projection unit per pixel
    # it should be changed if resolution (aka pixel / RasterSize) changed

    if geotransform is not None:
        dataset2.SetGeoTransform(tuple(geotransform_new))

    if projection is not None:
        dataset2.SetProjection(projection)

    # Read this Medium article to know more about this Python script!
    # https://medium.com/@devlog/copy-and-paste-georeference-data-using-gdal-44727f46b839


if __name__ == '__main__':

    parser = ArgumentParser(
        description='Copy GeoTIFF info from one .tif file to another')
    parser.add_argument('-x', '--xscale', type=float, default=1.,
                        help='scale for X coords')
    parser.add_argument('-y', '--yscale', type=float,
                        help='scale for Y coords (default=same as xscale)')
    parser.add_argument('--align_x', action='store_true',
                        help='calculate isotropic scaling between source and '
                        'destination, assuming the X field of view matches')
    parser.add_argument('--align_y', action='store_true',
                        help='calculate isotropic scaling between source and '
                        'destination, assuming the Y field of view matches')
    parser.add_argument('source', help='source .tif file with georef info')
    parser.add_argument('destination',
                        help='destination .tif file without georef info')
    options = parser.parse_args()

    if len(sys.argv) < 3:
        print("Usage: gdalcopyproj.py source_file dest_file")
        sys.exit(1)

    input = options.source
    output = options.destination
    scale_x = options.xscale
    scale_y = options.yscale
    align_x = options.align_x
    align_y = options.align_y
    if align_x and align_y:
        print('align_x and align_y are self-exclusive. Use either, not both.')
        sus.exit(1)

    copy_geo_projection(input, output, scale_x=scale_x, scale_y=scale_y,
                        align_x=align_x, align_y=align_y)

