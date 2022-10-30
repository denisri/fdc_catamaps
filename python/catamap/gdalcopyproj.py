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

def copy_geo_projection(input, output):
    dataset = gdal.Open( input )
    if dataset is None:
        print( 'Unable to open', input, 'for reading')
        sys.exit(1)

    projection   = dataset.GetProjection()
    geotransform = dataset.GetGeoTransform()

    if projection is None and geotransform is None:
        raise ValueError('No projection or geotransform found on file' + input)

    dataset2 = gdal.Open( output, gdal.GA_Update )

    if dataset2 is None:
        raise RuntimeError('Unable to open %s for writing' % output)

    # To know more about GeoTransforms, see https://gdal.org/tutorials/geotransforms_tut.html
    geotransform_new = list(dataset.GetGeoTransform())
    geotransform_new[1] = geotransform_new[1] * dataset.RasterXSize / dataset2.RasterXSize
    geotransform_new[5] = geotransform_new[5] * dataset.RasterYSize / dataset2.RasterYSize
    # 2nd and 6th value of GetGeoTransform() is X/Y projection unit per pixel
    # it should be changed if resolution (aka pixel / RasterSize) changed

    if geotransform is not None:
        dataset2.SetGeoTransform( tuple(geotransform_new) )

    if projection is not None:
        dataset2.SetProjection( projection )

    # Read this Medium article to know more about this Python script!
    # https://medium.com/@devlog/copy-and-paste-georeference-data-using-gdal-44727f46b839


if __name__ == '__main__':

    if len(sys.argv) < 3:
        print( "Usage: gdalcopyproj.py source_file dest_file")
        sys.exit(1)

    input = sys.argv[1]
    output = sys.argv[2]

    copy_geo_projection(input, output)

