#!/usr/bin/env python

from soma import aims
import os
import math

out_dir = 'compass'

sphere = aims.SurfaceGenerator.icosphere([0, 0, 0], 10., 320)
sphere.header()['material'] = {'diffuse': [0.8, 0.8, 1., 0.5]}
north = aims.SurfaceGenerator.cone([0, -10., 0], [0, 0, 0], 2., 12, False, True)
north.header()['material'] = {'diffuse': [1., 0.2, 0.2, 1.]}
south = aims.SurfaceGenerator.cone([0, 9., 0], [0, 0, 0], 1.3, 12, False, True)
south.header()['material'] = {'diffuse': [0.5, 0.7, 1., 1.]}
east = aims.SurfaceGenerator.cone([9., 0, 0], [0, 0, 0], 1.3, 12, False, True)
east.header()['material'] = {'diffuse': [0.5, 0.7, 1., 1.]}
west = aims.SurfaceGenerator.cone([-9., 0, 0], [0, 0, 0], 1.3, 12, False, True)
west.header()['material'] = {'diffuse': [0.5, 0.7, 1., 1.]}
up = aims.SurfaceGenerator.cone([0, 0, 9.], [0, 0, 0], 0.5, 12, False, True)
up.header()['material'] = {'diffuse': [0., 0.5, 1., 1.]}
down = aims.SurfaceGenerator.cone([0, 0, -9.], [0, 0, 0], 0.5, 12, False, True)
down.header()['material'] = {'diffuse': [0., 1., .3, 1.]}
ne = aims.SurfaceGenerator.cone([4., -4., 0], [0, 0, 0], 1.3, 12, False, True)
ne.header()['material'] = {'diffuse': [0.8, 0.8, 0.8, 1.]}
nw = aims.SurfaceGenerator.cone([-4., -4., 0], [0, 0, 0], 1.3, 12, False, True)
nw.header()['material'] = {'diffuse': [0.8, 0.8, 0.8, 1.]}
sw = aims.SurfaceGenerator.cone([-4., 4., 0], [0, 0, 0], 1.3, 12, False, True)
sw.header()['material'] = {'diffuse': [0.8, 0.8, 0.8, 1.]}
se = aims.SurfaceGenerator.cone([4., 4., 0], [0, 0, 0], 1.3, 12, False, True)
se.header()['material'] = {'diffuse': [0.8, 0.8, 0.8, 1.]}
sew = south
aims.SurfaceManip.meshMerge(sew, east)
aims.SurfaceManip.meshMerge(sew, west)
semi = ne
aims.SurfaceManip.meshMerge(semi, nw)
aims.SurfaceManip.meshMerge(semi, sw)
aims.SurfaceManip.meshMerge(semi, se)

# belt

belt = aims.AimsTimeSurface()
vert = []
poly = []
r = 10.
br = 0.5
eps = math.pi * 0.002
wbelt = aims.AimsTimeSurface()
for i in range(8):
    angle = math.pi / 4 * i
    step = math.pi / 16
    for j in range(2):
        a1 = angle + j * step - eps
        a2 = angle + (j + 1) * step + eps
        a3 = a1 + math.pi / 8
        a4 = a2 + math.pi / 8
        tube = aims.SurfaceGenerator.cylinder(
            [r * math.cos(a1), r * math.sin(a1), 0],
            [r * math.cos(a2), r * math.sin(a2), 0], br, br, 8, False, True)
        aims.SurfaceManip.meshMerge(belt, tube)
        tube = aims.SurfaceGenerator.cylinder(
            [r * math.cos(a3), r * math.sin(a3), 0],
            [r * math.cos(a4), r * math.sin(a4), 0], br, br, 8, False, True)
        aims.SurfaceManip.meshMerge(wbelt, tube)
        #vert.append([r * math.cos(a), r * math.sin(a), -0.5])
        #vert.append([r * math.cos(a), r * math.sin(a), 0.5])
        #if j != 0:
            #nv = len(vert)
            #poly += [(nv - 4, nv - 2, nv - 3), (nv - 3, nv - 2, nv - 1)]
#belt.vertex().assign(vert)
#belt.polygon().assign(poly)
belt.header()['material'] = {'diffuse': [0.2, 0.2, 0.2, 1.]}
wbelt.header()['material'] = {'diffuse': [0.6, 0.6, 1., 1.]}

if not os.path.exists(out_dir):
    os.mkdir(out_dir)
aims.write(sphere, os.path.join(out_dir, 'sphere.obj'), format='WAVEFRONT')
aims.write(north, os.path.join(out_dir, 'north.obj'), format='WAVEFRONT')
aims.write(sew, os.path.join(out_dir, 'sew.obj'), format='WAVEFRONT')
aims.write(semi, os.path.join(out_dir, 'semi.obj'), format='WAVEFRONT')
aims.write(up, os.path.join(out_dir, 'up.obj'), format='WAVEFRONT')
aims.write(down, os.path.join(out_dir, 'down.obj'), format='WAVEFRONT')
aims.write(belt, os.path.join(out_dir, 'belt.obj'), format='WAVEFRONT')
aims.write(wbelt, os.path.join(out_dir, 'wbelt.obj'), format='WAVEFRONT')

