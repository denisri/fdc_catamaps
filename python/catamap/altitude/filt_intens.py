#!/usr/bin/env python

from __future__ import print_function

from soma import aims
import numpy as np
import glob
import os
import json


def get_scale(img, divisions=21, x_shift=-5):
    y = [img.getSize()[1] * ((float(i) + 0.5) / divisions)
         for i in range(divisions)]
    x = x_shift
    if x < 0:
        x = img.getSize()[0] + x_shift
    scl_map = []
    for i, py in enumerate(y):
        rgb = img.at(x, py)
        scl_map.append(rgb)
    return list(reversed(scl_map))


def scale_image(img):
    if isinstance(img.at(0), aims.AimsHSV):
        return scale_image_hsv(img)
    else:
        return scale_image_rgb(img)


def scale_image_rgb(img):
    for y in range(img.getSize()[1]):
        for x in range(img.getSize()[0]):
            rgb = img.at(x, y)
            intens = np.sqrt(rgb[0]*rgb[0] + rgb[1]*rgb[1] + rgb[2]*rgb[2])
            if intens == 0:
                img.setValue([0, 0, 0], x, y)
            else:
                scl = float( 128. / intens )
                img.setValue(aims.AimsRGB(int(rgb[0] * scl),
                                          int(rgb[1] * scl),
                                          int(rgb[2] * scl)), x, y)


def scale_image_hsv(img):
    for y in range(img.getSize()[1]):
        for x in range(img.getSize()[0]):
            hsv = aims.AimsHSV(img.at(x, y))
            #if hsv[1] < 10 or hsv[0] > 200:
            hsv[2] = 255
            if hsv[0] > 200:
                hsv[0] = 0
            if hsv[1] < 10:
                hsv[0] = 0
            if hsv[0] > 10:
                hsv[1] = 255
            else:
                scl = float(hsv[0]) / 10.
                hsv[1] = int(round((100. + hsv[1] * 155. / 255.) * (1. - scl) + 255. * scl))
            img.setValue(hsv, x, y)


def get_float_altitude(img, src_scl, dst_scl):
    def interpolate(rgb, src_scl, dst_scl):
        rgb = np.asarray(rgb).astype(float)
        #if rgb[1] < 10 or rgb[0] > 200:
        #if rgb[0] > 200:
            #rgb[0] = 0.
        #rgb[0] *= 2.
        #rgb[1] = 255.
        #rgb[2] = 255.
        dist = np.sum((dst_scl - rgb) ** 2, axis=1)
        #dist = ((dst_scl - rgb) ** 2)[:, 0]
        #print('dist:', dist)
        dmin = np.argmin(dist)
        if dmin == 0:
            ind = [dmin, dmin + 1]
        elif dmin == dst_scl.shape[0] - 1:
            ind = [dmin - 1, dmin]
        else:
            if dist[dmin - 1] < dist[dmin + 1]:
                ind = [dmin - 1, dmin]
            else:
                ind = [dmin, dmin + 1]
        # project
        axis = dst_scl[ind[1]] - dst_scl[ind[0]]
        d2 = np.sum(axis ** 2)
        if d2 == 0:
            return src_scl[-1]
        else:
            x = (rgb - dst_scl[ind[0]]).dot(axis) / d2
        if x < 0:
            x = 0.
        elif x > 1:
            x = 1.
        return src_scl[ind[0]] + (src_scl[ind[1]] - src_scl[ind[0]]) * x

    dst_scl = np.asarray(scl_map).astype(float)
    #dst_scl[:, 0] *= 2.
    #dst_scl[:, 1] = 255.
    new_img = aims.Volume(img.getSize(), dtype='FLOAT')
    new_img.header()['voxel_size'] = img.header()['voxel_size']
    for y in range(img.getSize()[1]):
        for x in range(img.getSize()[0]):
            rgb = img.at(x, y)
            alt = interpolate(rgb, src_scl, dst_scl)
            new_img.setValue(alt, x, y)
    return new_img


images = sorted(glob.glob('altitude/raw/*.jpg'))
if not os.path.exists('altitude/intens'):
    os.mkdir('altitude/intens')
if not os.path.exists('altitude/real'):
    os.mkdir('altitude/real')

scales = {}
scl_min = 1000
scl_max = -10

print('read scales')
for image in images:
    src_scl = image.replace('.jpg', '.json')
    if os.path.exists(src_scl):
        scale = json.load(open(src_scl))['altitudes']
        scales[image] = scale
        m = min(scale)
        if m < scl_min:
            scl_min = m
        m = max(scale)
        if m > scl_max:
            scl_max = m

print('global min/max:', scl_min, '/', scl_max)
glob_scale = {'scale_min': scl_min, 'scale_max': scl_max}
json.dump(glob_scale, open('altitude/real/global.json', 'w'))

for image in images:
    print('read:', image)
    img_rgb = aims.read(image)
    ## scale in RGB space
    #scale_image(img_rgb)
    out_img = image.replace('/raw/', '/intens/')
    #print('write:', out_img)
    #aims.write(img_rgb, out_img)
    # re-scale in HSV space
    c = aims.Converter_Volume_RGB_Volume_HSV()
    img = c(img_rgb)
    scale_image(img)

    # go back to RGB
    #c = aims.Converter_Volume_HSV_Volume_RGB()
    #img = c(img)

    out_img = out_img.replace('.jpg', '.ima')
    print('write:', out_img)
    aims.write(img, out_img)
    scl_map = get_scale(img)
    json_d = {'scale_map': [list(x) for x in scl_map]}
    out_img_json = out_img.replace('.ima', '.json')
    json.dump(json_d, open(out_img_json, 'w'))

    scale = scales.get(image)
    if scale is not None:
        print('build real alt')
        #c = aims.Converter_Volume_HSV_Volume_RGB()
        flt_alt = get_float_altitude(img, scale, scl_map)
        out_flt_alt_file = image.replace('/raw/', '/real/').replace(
            '.jpg', '.ima')
        print('write:', out_flt_alt_file)
        aims.write(flt_alt, out_flt_alt_file)
        # write as jpeg
        flt_alt = (flt_alt - scl_min) * 255.49 / (scl_max - scl_min)
        c = aims.Converter_Volume_FLOAT_Volume_U16()
        u16_alt = c(flt_alt)
        out_u16_alt_file = out_flt_alt_file.replace('.ima', '.jpg')
        print('write:', out_u16_alt_file)
        aims.write(u16_alt, out_u16_alt_file, format='JPG')
