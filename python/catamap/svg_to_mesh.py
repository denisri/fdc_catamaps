
'''
svg_to_mesh module
==================

This modules allows to read an Inkscape SVG file, parse its elements, and convert them to 3D meshes.

svg_to_mesh module API
----------------------
'''

import xml.etree.cElementTree as ET
try:
    from soma import aims, aimsalgo
    fake_aims = False
except ImportError:
    # aims is not available, use the fake light one (with reduced
    # functionalities)
    aims = None
    fake_aims = True
import numpy as np
import scipy.linalg
import os
import os.path as osp
import copy
import sys
import math
import json

'''
SVG parsing as mesh objects

requires:

* xml (ElementTree)
* numpy
* scipy
* optionally, soma.aims
* optionally, pyclipper

aims:

    The AIMS library is used to build and manpulate meshes.
    (https://github.com/brainvisa/aims-free)
    This lib is compiled (C++ + python bindings) thus is not completely
    straightforward to install.
    Alternately we have implemented basic replacements for vector and mesh
    classes. This allows to use the 2D part.
    The 3D part however needs more algorithmic things in Aims, and Anatomist
    to render depth maps.

pyclipper:
    Used to perform polygons clipping, which is now used in zoomed regions. If
    not installed the program will print a warning message, and clipped
    polygons will just disappear.
'''


if fake_aims:
    # implement an "aims-lite": basic Aims mesh structures mimicing part of
    # the Aims API transparently.
    # This allows to use the 2D part.
    # The 3D part however needs more algorithmic things in Aims

    print('The soma.aims (https://github.com/brainvisa/aims-free) library '
          'module is not available. We will process using a light ersatz, '
          'which allows to process things mainly in 2D. Other 3D parts need '
          'more algorithmic processing and require the "real" aims module to '
          'be present.')

    class aims:
        ''' Fake aims-lite module '''

        class vector:
            ''' Fixed size vector '''

            def __init__(self, dtype, shape):
                self._vec = np.zeros(shape, dtype=dtype)
                self._dim = 1
                if len(shape) >= 2:
                    self._dim = shape[1]

            def assign(self, vec):
                shape = (len(vec), self._dim)
                self._vec = np.zeros(shape, dtype=self._vec.dtype)
                self._vec[:] = np.asarray(vec).reshape(shape)

            def __getitem__(self, item):
                return self._vec.__getitem__(item)

            def __setitem__(self, item, value):
                return self._vec.__setitem__(item, value)

            def __len__(self):
                return len(self._vec)

            def __iadd__(self, vec):
                self._vec = np.vstack((self._vec, vec))

            def append(self, elem):
                self._vec = np.vstack((self._vec, [elem]))

            @property
            def np(self):
                return self._vec

        class _AimsTimeSurface:
            ''' Mesh structure '''

            def __init__(self, dim=3):
                self._vertex = aims.vector(dtype=np.float32, shape=(0, 3))
                self._polygon = aims.vector(dtype=np.uint32, shape=(0, dim))
                self._header = {}

            def vertex(self):
                return self._vertex

            def polygon(self):
                return self._polygon

            def header(self):
                return self._header

        class AimsTimeSurface_2(_AimsTimeSurface):
            ''' Segments mesh (2 points per polygon) '''

            def __init__(self):
                super(aims.AimsTimeSurface_2, self).__init__(2)

        class AimsTimeSurface_3(_AimsTimeSurface):
            ''' Triangles mesh (3 points per polygon) '''

            def __init__(self):
                super(aims.AimsTimeSurface_3, self).__init__(3)

        def AimsTimeSurface(dim=3):
            if dim == 3:
                return aims.AimsTimeSurface_3()
            elif dim == 2:
                return aims.AimsTimeSurface_2()
            return aims._AimsTimeSurface(dim)


class SvgToMesh:
    ''' Read SVG, transforms things into meshes
    '''

    def __init__(self, concat_mesh='bygroup'):
        '''
        Parameters
        ----------
        concat_mesh: str
            concatenation method between multiple paths in SVG file.
            'merge': merge all paths in a single mesh
            'time': use mesh timestep to store each path
            'list': return a list of meshes
            'bygroup' (default): return a dict of meshes, one for each main
                group, paths are concatenated inside each group
        '''
        self.concat_mesh = concat_mesh
        self.mesh = None
        self.mesh_list = []
        self.mesh_dict = {}
        self.debug = False
        self.id_count = 1
        # layers that should be taken into account even if hidden
        self.explicitly_show = []
        # in 2D transform mode (replace_elements), put back these properties
        # from the source to the transformed xml items
        self.keep_transformed_properties = set()
        self.tex_mapping_methods = {
            'xy': self.make_texcoord_xy,
            'geodesic_z': self.make_texcoord_geodesic_z,
        }
        self.enable_texturing = False
        self.priority_layers = ['metadata', 'defs']
        self.font_substitutions = {'LMSansUltraCond10': 'Univers LT Std'}

    @staticmethod
    def get_style(xml_elem):
        style = xml_elem.get('style')
        if not style:
            return None
        style = style.replace(';', '\n')
        style = style.split('\n')
        style = [x.strip() for x in style]
        style = dict([(y.strip() for y in x.split(':')) for x in style if x])
        return style

    @staticmethod
    def set_style(xml_elem, style):
        style_l = ['%s:%s' % (k, str(v)) for k, v in style.items()]
        style_str = ';'.join(style_l)
        if not style:
            return None
        xml_elem.set('style', style_str)

    @staticmethod
    def get_mesh_color(style):
        ''' Returns background_color (fill), foreground_color (borders)
        '''
        if not style:
            return None, None
        bg_color = style.get('fill')
        bg_opacity = style.get('fill-opacity')
        fg_color = style.get('stroke')
        fg_opacity = style.get('stroke-opacity')
        colors = []
        for color, opacity in ((bg_color, bg_opacity), (fg_color, fg_opacity)):
            if not color:
                colors.append(None)
                continue
            color_spec = color.split(' ')
            color = [c[1:] for c in color_spec if c[0] == '#']
            if color:
                c = color[0]
                n = int(math.ceil(len(c) / 3))
                if n < 1:
                    n = 1
                if opacity not in (None, 'none'):
                    opacity = float(opacity)
                else:
                    opacity = 1.
                color = (int('0x' + c[:n], 0) / 255.,
                         int('0x' + c[n:n*2], 0) / 255.,
                         int('0x' + c[n*2:n*3], 0) / 255.,
                         opacity)
                colors.append(color)
            else:
                colors.append(None)
        if colors[0] is None and colors[1] is not None:
            colors[0] = colors[1]
        elif colors[1] is None and colors[0] is not None:
            colors[1] = colors[0]
        return colors

    @staticmethod
    def unitscale(unit):
        ''' convert unit scale to px (used in inkscape)
        '''
        if unit == 'px':
            return 1.
        if unit == 'mm':
            return 96. / 25.4  # 96 dpi / mm/inch
        if unit == 'cm':
            return 96. / 2.54  # 96 dpi / cm/inch
        if unit == 'pt':
            return 1. / 0.75
        if unit == 'in':
            return 96.  # (96 dpi)
        if unit == 'pc':
            return 1. / 0.062500
        raise ValueError(f'unknown unit {unit}')

    @staticmethod
    def measure_with_unit(meas_str):
        unit = 'px'
        for unit_sym in ('mm', 'px', 'pc', 'pt', 'cm', 'in'):
            if meas_str.endswith(unit_sym):
                unit = unit_sym
                meas_str = meas_str[:-len(unit_sym)]
        meas = float(meas_str) * SvgToMesh.unitscale(unit)
        return meas

    @staticmethod
    def get_layers(xml, recursive=True, parent=True):
        todo = [(xml.getroot(), item) for item in xml.getroot()
                if SvgToMesh.is_layer(item)]
        while todo:
            elem = todo.pop(0)
            item = elem[1]
            if recursive:
                todo += [(item, child) for child in item
                         if SvgToMesh.is_layer(child)]
            if parent:
                yield elem
            else:
                yield item

    def document_scale(self, xml=None, unit='px'):
        ''' scale from document (px 96 dpi) to target unit
        '''
        doc_scale = getattr(self, 'doc_scale', None)
        if doc_scale is not None:
            return doc_scale / self.unitscale(unit)
        if xml is None:
            xml = self.svg
        vb = xml.getroot().get('viewBox')
        w = xml.getroot().get('width')
        h = xml.getroot().get('height')
        if w.endswith('mm'):
            self.doc_unit = 'mm'
            w = w[:-2]
            h = h[:-2]
        elif w.endswith('px'):
            self.doc_unit = 'px'
            w = w[:-2]
            h = h[:-2]
        elif w.endswith('pt'):
            self.doc_unit = 'pt'
            w = w[:-2]
            h = h[:-2]
        elif w.endswith('pc'):
            self.doc_unit = 'pc'
            w = w[:-2]
            h = h[:-2]
        else:
            self.doc_unit = 'px'
        unitscale = self.unitscale(self.doc_unit)
        w = float(w) * unitscale
        h = float(h) * unitscale
        vbox = [float(x.strip()) for x in vb.strip().split(' ')]
        sclx = w / (vbox[2] - vbox[0])
        scly = h / (vbox[3] - vbox[1])
        if scly < sclx * 0.7 or scly > sclx * 1.5:
            print('inconsistent x/y scales:', sclx, scly)
        self.doc_scale = (sclx + scly) / 2
        return self.doc_scale / self.unitscale(unit)

    def read_rect(self, xml_path, trans, style=None):
        ''' Read a rectangle element as a mesh
        '''
        if not aims:
            raise RuntimeError('aims module is not available. read_rect() '
                               'needs it.')
        if style is None:
            style = self.get_style(xml_path)
        color = self.get_mesh_color(style)
        material = {}
        if color[0]:
            material['diffuse'] = color[0]
        if color[1]:
            material['border_color'] = color[1]

        x = float(xml_path.get('x'))
        y = float(xml_path.get('y'))
        w = float(xml_path.get('width'))
        h = float(xml_path.get('height'))
        pts = trans * np.matrix([[x, x+w, x+w, x],
                                 [y, y, y+h, y+h],
                                 [1., 1., 1., 1.]])
        pts[2, :] = 0  # reset Z to 0
        mesh = aims.AimsTimeSurface_2()
        mesh.vertex().assign(np.asarray(pts.T))
        mesh.polygon().assign([(0, 1), (1, 2), (2, 3), (3, 0)])

        trans3d = getattr(trans, 'transform_3d', None)
        if trans3d is not None:
            vert = np.vstack((np.asarray(mesh.vertex()).T,
                              np.ones((1, len(mesh.vertex())),
                                      dtype=np.float32)))
            vert = (trans3d * vert).T
            vert = vert[:, :3]
            mesh.vertex().assign(np.asarray(vert))
            mesh.header()['transformation'] = list(np.ravel(trans3d))

        if material:
            mesh.header()['material'] = material
        return mesh

    def read_circle(self, xml_path, trans, style=None):
        ''' Read a circle element as a mesh
        '''
        if not aims:
            raise RuntimeError('aims module is not available. read_circle() '
                               'needs it.')
        if style is None:
            style = self.get_style(xml_path)
        color = self.get_mesh_color(style)
        material = {}
        if color[0]:
            material['diffuse'] = color[0]
        if color[1]:
            material['border_color'] = color[1]

        x = xml_path.get('cx')
        if x is None:
            x = xml_path.get('{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx')
        x = float(x)
        y = xml_path.get('cy')
        if y is None:
            y = xml_path.get('{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy')
        y = float(y)
        r = xml_path.get('r')
        if r is None:
            r = xml_path.get('{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}rx')
        # TODO read ellipse with differing rx and ry
        if r is None:
            r = xml_path.get('rx')
        r = float(r)
        angle_s = xml_path.get('sodipodi:start')
        if angle_s:
            angle_s = float(angle_s)
        else:
            angle_s = 0.
        angle_e = xml_path.get('sodipodi:end')
        if angle_e:
            angle_e = float(angle_e)
        else:
            angle_e = np.pi * 2
        npt = 24
        if hasattr(aims, 'SurfaceGenerator'):
            mesh = aims.SurfaceGenerator.circle_wireframe(
                (x, y, 1.), r, npt, (0, 0, 1), (1, 0, 0), angle_s, angle_e)
            pts = trans * np.matrix(mesh.vertex().np.T)
            pts[2, :] = 0  # reset Z to 0
            mesh.vertex().assign(np.asarray(pts.T))
        else:
            # no aims lib, generate a square instead (it's normally just for
            # the bounding box in 2D)
            pts = trans * np.matrix([[x-r, x+r, x+r, x-r],
                                    [y-r, y+r, y+r, y+r],
                                    [1., 1., 1., 1.]])
            pts[2, :] = 0  # reset Z to 0
            mesh = aims.AimsTimeSurface_2()
            mesh.vertex().assign(np.asarray(pts.T))
            mesh.polygon().assign([(0, 1), (1, 2), (2, 3), (3, 0)])

        trans3d = getattr(trans, 'transform_3d', None)
        if trans3d is not None:
            vert = np.vstack((np.asarray(mesh.vertex()).T,
                              np.ones((1, len(mesh.vertex())),
                                      dtype=np.float32)))
            vert = (trans3d * vert).T
            vert = vert[:, :3]
            mesh.vertex().assign(np.asarray(vert))
            mesh.header()['transformation'] = list(np.ravel(trans3d))

        if material:
            mesh.header()['material'] = material
        return mesh

    def read_polygon(self, xml_path, trans, style=None):
        ''' Read a polygon element as a mesh
        '''
        if not aims:
            raise RuntimeError('aims module is not available. read_polygon() '
                               'needs it.')
        if style is None:
            style = self.get_style(xml_path)
        color = self.get_mesh_color(style)
        material = {}
        if color[0]:
            material['diffuse'] = color[0]
        if color[1]:
            material['border_color'] = color[1]

        points = xml_path.get('points')
        pl = points.split()
        points = np.matrix([[float(p.strip()) for p in pt.split(',')]
                            for pt in pl]).T
        # print('polygon points:', points.T)
        points3 = np.vstack((points, np.ones((points.shape[1], ))))
        pts = trans * points3
        pts[2, :] = 0  # reset Z to 0
        mesh = aims.AimsTimeSurface_2()
        mesh.vertex().assign(np.asarray(pts.T))

        trans3d = getattr(trans, 'transform_3d', None)
        if trans3d is not None:
            vert = np.vstack((np.asarray(mesh.vertex()).T,
                              np.ones((1, len(mesh.vertex())),
                                      dtype=np.float32)))
            vert = (trans3d * vert).T
            vert = vert[:, :3]
            mesh.vertex().assign(np.asarray(vert))
            mesh.header()['transformation'] = list(np.ravel(trans3d))

        poly = [(i, i+1) for i in range(pts.shape[1] - 1)]
        poly.append((pts.shape[1] - 1, 0))
        mesh.polygon().assign(poly)
        if material:
            mesh.header()['material'] = material
        return mesh

    def read_path(self, xml_path, trans, style=None):
        ''' Read a path element as mesh, apply coords transformations
        '''

        def read_point(pdesc, i, pt=None, nvert=None, npoly=None):
            j = i + 1
            try:
                while j < n and pdesc[j] in '0123456789.e-':
                    j += 1
                x = float(pdesc[i:j])
                i = j + 1
                while i < len(pdesc) and pdesc[i] in ' ,':
                    i += 1
            except Exception as e:
                print(e)
                print('failed reading', pt, ', i:', i, ', vertices:', nvert,
                      ', poly:', npoly)
                raise
            return x, i

        if not aims:
            raise RuntimeError('aims module is not available. read_path() '
                               'needs it.')

        if xml_path.tag == 'rect' or xml_path.tag.endswith('}rect') or \
                xml_path.tag.endswith('}image'):
            return self.read_rect(xml_path, trans, style)
        if xml_path.tag == 'polygon' or xml_path.tag.endswith('}polygon'):
            return self.read_polygon(xml_path, trans, style)
        if xml_path.tag == 'circle' or xml_path.tag.endswith('}circle'):
            return self.read_circle(xml_path, trans, style)
        if xml_path.tag == 'ellipse' or xml_path.tag.endswith('}ellipse'):
            return self.read_circle(xml_path, trans, style)
        if xml_path.get(
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}type') \
                    == 'arc':
            return self.read_circle(xml_path, trans, style)

        # read path

        if style is None:
            style = self.get_style(xml_path)
        color = self.get_mesh_color(style)
        material = {}
        if color[0]:
            material['diffuse'] = color[0]
        if color[1]:
            material['border_color'] = color[1]

        vert = []
        poly = []
        pdesc = xml_path.get('d')
        n = len(pdesc)
        i = 0
        first = 0
        cmd = 'M'
        x = 0
        y = 0

        while i < n:
            while(i < n and pdesc[i] == ' '):
                i += 1
            if i == n:
                # print('end of path in:', pdesc)
                break
            # print('i:', i)
            last_x, last_y = x, y
            if pdesc[i] in 'mMcClLhHvVsSqQtTaA':
                cmd = pdesc[i]
                # print('cmd:', cmd)
                i += 1
                while pdesc[i] == ' ':
                    i += 1
            elif pdesc[i] in '-0123456789.':
                if cmd not in 'vV':
                    x, i = read_point(pdesc, i, 'x', len(vert), len(poly))
                    if cmd >= 'a':
                        x += last_x
                if cmd not in 'hH':
                    y, i = read_point(pdesc, i, 'y', len(vert), len(poly))
                    if cmd >= 'a':
                        y += last_y
                # print(x,', ', y)
                if cmd in 'cC':
                    x, i = read_point(pdesc, i, 'x2', len(vert), len(poly))
                    y, i = read_point(pdesc, i, 'y2', len(vert), len(poly))
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                    x, i = read_point(pdesc, i, 'x3', len(vert), len(poly))
                    y, i = read_point(pdesc, i, 'y3', len(vert), len(poly))
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                elif cmd in 'sSqQ':
                    x, i = read_point(pdesc, i, 'x2', len(vert), len(poly))
                    y, i = read_point(pdesc, i, 'y2', len(vert), len(poly))
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                if cmd in 'aA':
                    x, i = read_point(pdesc, i, 'x-axis-rotation',
                                      len(vert), len(poly))
                    y, i = read_point(pdesc, i, 'large-arc-flag',
                                      len(vert), len(poly))
                    y, i = read_point(pdesc, i, 'sweep-flag',
                                      len(vert), len(poly))
                    x, i = read_point(pdesc, i, 'x2', len(vert), len(poly))
                    y, i = read_point(pdesc, i, 'y2', len(vert), len(poly))
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                vert.append((x, y, 0.))
                if len(vert) > 1 and cmd not in 'mM':
                    poly.append((len(vert) - 2, len(vert) - 1))
                if cmd == 'm':
                    cmd = 'l'
                    first = len(vert) - 1
                elif cmd == 'M':
                    cmd = 'L'
                    first = len(vert) - 1
            elif pdesc[i] in 'zZ':
                # print('close')
                if len(vert) >= first + 3:
                    poly.append((len(vert) - 1, first))
                x, y = vert[first][:2]
                i += 1
            else:
                print('unknown command:', pdesc[i], 'at position', i)
                i += 1

        mesh = aims.AimsTimeSurface(2)
        # if getattr(self, 'debug', False):
        #     print('vert:', vert)
        #     print('poly:', poly)
        #     print('path trans:', trans)
        #     print('trans:', trans)
        if not np.all(trans == np.eye(3)):
            vert = np.asarray(vert).T
            vert[2, :] = 1.
            vert = (trans * vert).T
            vert[:, 2] = 0.
            # if getattr(self, 'debug', False):
            #     print('to: vert:', vert)
        mesh.vertex().assign(np.asarray(vert))
        mesh.polygon().assign(poly)
        trans3d = getattr(trans, 'transform_3d', None)
        if trans3d is not None:
            vert = np.vstack((np.asarray(vert).T,
                              np.ones((1, len(vert)), dtype=np.float32)))
            vert = (trans3d * vert).T
            vert = vert[:, :3]
            mesh.vertex().assign(np.asarray(vert))
            mesh.header()['transformation'] = list(np.ravel(trans3d))

        if material:
            mesh.header()['material'] = material

        return mesh

    def get_textures(self, mesh, child, parents):
        if not self.enable_texturing:
            # if texturing is not enabled, don't look for them.
            return
        if 'textures' in mesh.header():
            return  # already done
        tex_types = {
            'texture': None,
            'ceil_texture': None,
            'floor_texture': None,
            'wall_texture': None,
        }
        found = False
        for element in [child] + list(reversed(parents)):
            for ttype in tex_types:
                texture = element.get(ttype)
                if texture is not None:
                    found = True
                    try:
                        tex_def = json.loads(texture)
                    except Exception:
                        print(
                            'error in JSON decoding of %s property of '
                            'element: %s: %s'
                            % (ttype, element.get('id'), texture))
                        raise
                    tex_types[ttype] = tex_def
            if found:
                break
        else:
            return
        textures = {}
        for ttype, tex_def in tex_types.items():
            if tex_def is None:
                continue
            # coords, mapping method, scales & transform
            tex_params = {k: v for k, v in tex_def.items()
                          if k not in ('id', 'label', 'layer')}
            tex_def = {k: v for k, v in tex_def.items()
                       if k in ('id', 'label', 'layer')}
            # TODO
            tex_element = self.find_element(self.svg, tex_def)
            if tex_element is None:
                print('texture image not found for %s, %s: %s'
                      % (element.get('id'), ttype, tex_element))
                continue
            # print('texture image:', tex_element)
            tex_image = self.get_image(tex_element[0], tex_element[1])
            # mesh is possibly not complete yet: tex coords generation
            # must be postponed.
            textures[ttype] = {'image': tex_image, 'params': tex_params}

        mesh.header()['textures'] = textures

    def get_image(self, xml_element, trans):
        if not hasattr(self, 'texture_images'):
            self.texture_images = {}
        else:
            image = self.texture_images.get(xml_element.get('id'))
            if image is not None:
                # already got this one
                return image

        w = float(xml_element.get('width'))
        h = float(xml_element.get('height'))
        x = float(xml_element.get('x'))
        y = float(xml_element.get('y'))
        pos = trans.dot([x, y, 1.])
        uri = xml_element.get('{http://www.w3.org/1999/xlink}href')
        image = aims.Volume_RGBA()
        gltf_props = xml_element.get('gltf_properties')
        if gltf_props is not None:
            gltf_props = json.loads(gltf_props)
        if uri[:6] == 'data:':
            # bin
            pass
        else:
            if not osp.isabs(uri):
                uri_a = osp.join(osp.dirname(self.svg_filename), uri)
                if osp.exists(uri_a):
                    uri = uri_a
                else:
                    # maybe a realpath
                    uri = osp.join(osp.dirname(osp.realpath(
                        self.svg_filename)), uri)
                image = aims.read(uri)
                # ensure RGB or RGBA mode, avoid greyscale
                if not type(image).__name__.split('_')[-1].startswith('RGB'):
                    image = image.astype('RGB')
        svg_p = image.header()
        svg_p['name'] = xml_element.get('id')  # to re-identify the image later
        svg_p['svg_size'] = [w, h]
        svg_p['svg_position'] = np.asarray(pos)[0].tolist()
        svg_p['svg_transform'] = trans.tolist()
        if gltf_props is not None:
            # print('set gltf_properties:', gltf_props)
            image.header()['gltf_properties'] = gltf_props
        # print('image header:', image.header())
        self.texture_images[xml_element.get('id')] = image
        return image

    def build_texture(self, mesh, key):
        textures = mesh.header().get('textures')
        if textures is None:
            return

        if key.endswith('wall_tri'):
            ttype = 'wall_texture'
        elif key.endswith('floor_tri'):
            ttype = 'floor_texture'
        elif key.endswith('ceil_tri'):
            ttype = 'ceil_texture'
        else:
            return
        tex_def = textures.get(ttype)
        if tex_def is None:
            tex_def = textures.get('texture')
        if tex_def is None:
            return

        if 'mapping_method' not in tex_def.get('params', {}) \
                and ttype == 'wall_texture':
            tex_def.setdefault('params', {})['mapping_method'] = 'geodesic_z'

        tex_coords = self.make_texcoords(mesh, tex_def)
        tex_def['coords'] = [tex_coords]
        mesh.header()['texture'] = tex_def

    def make_texcoords(self, mesh, tex_def):
        map_meth = tex_def.get('params', {}).get('mapping_method', 'xy')
        # print('map meth:', tex_def.get('params', {}).get('mapping_method'))
        map_method = self.tex_mapping_methods[map_meth]
        tex_coords = map_method(mesh, tex_def)
        tex_coords.header()['gltf_texture'] = {'teximage': tex_def['image']}
        return tex_coords

    def make_texcoord_xy(self, mesh, tex_def):
        image = tex_def['image']
        svg_p = image.header()
        im_size = svg_p.get('svg_size', [1., 1.])
        im_pos = svg_p.get('svg_position', [0., 0.])
        im_trans = svg_p.get('svg_transform')
        if im_trans is not None:
            im_trans = np.matrix(im_trans)
            im_trans = np.linalg.inv(im_trans)
        else:
            im_trans = np.eye(3)
        im_trans[:, 2] = -im_trans.dot([im_pos[0], im_pos[1], 0]).T
        ptrans = np.matrix(np.eye(3))
        ptrans[0, 0] = 1. / im_size[0]
        ptrans[1, 1] = 1. / im_size[1]
        ptrans[2, 2] = 0.
        ptrans = ptrans * im_trans
        tex = aims.TimeTexture_POINT2DF()
        for t in mesh.keys():
            tx = tex[t]
            vert = mesh.vertex(t).np.T[:2, :]
            vert = np.vstack((vert, np.ones((1, vert.shape[1]))))
            trans_c = ptrans.dot(vert)[:2, :].T
            tx.assign(np.asarray(trans_c))
        return tex

    def make_texcoord_geodesic_z(self, mesh, tex_def):
        image = tex_def['image']
        svg_p = image.header()
        im_size = svg_p.get('svg_size', [1., 1.])
        im_pos = svg_p.get('svg_position', [0., 0.])
        im_trans = svg_p.get('svg_transform')
        if im_trans is not None:
            im_trans = np.matrix(im_trans)
            im_trans = np.linalg.inv(im_trans)
        else:
            im_trans = np.eye(3)
        im_trans[:, 2] = -im_trans.dot([im_pos[0], im_pos[1], 0]).T
        ptrans = np.matrix(np.eye(3))
        ptrans[0, 0] = 1. / im_size[0]
        ptrans[1, 1] = 1. / im_size[1]
        ptrans[2, 2] = 0.
        ptrans = ptrans * im_trans

        geodesic = self.geodesic2d(mesh)

        tex = aims.TimeTexture_POINT2DF()
        for t in mesh.keys():
            tx = tex[t]
            vert = mesh.vertex(t).np
            tx.resize(vert.shape[0])
            tx = tx.np
            tx[:, 0] = geodesic[0].np
            ptrans[0, 2] += ptrans.dot([vert[0, 0], 0, 1])[0, 0] \
                - ptrans.dot([tx[0, 0], 0, 1])[0, 0]
            tx[:, 1] = vert[:, 2]
            pts = np.vstack((tx.T, np.ones((1, tx.shape[0]))))
            trans_c = ptrans.dot(pts)[:2, :].T
            # y of textures is inverted, start at 1 (bottom) at 1st vertex
            trans_c[:, 1] = trans_c[0, 1] - trans_c[:, 1]
            tx[:] = trans_c
        return tex

    def geodesic2d(self, mesh):
        # get range of distances
        mesh2d = type(mesh)(mesh)  # copy mesh
        mesh2d.vertex(0).np[:, 2] = 0  # keep x, y, set z = 0
        vert2d = mesh.vertex(0).np[:, :2]

        # separate disconnected components first
        ictex = aims.TimeTexture_S16()
        ictex[0].resize(mesh.vertex(0).size())
        ictex[0].np[:] = 0
        cctex = aimsalgo.AimsMeshLabelConnectedComponent(mesh, ictex, 10000)
        ccs = np.round(cctex[0].np).astype(int)
        del ictex, cctex

        # in each connected component, set a distancemap seed
        ncc = ccs[-1]
        itex = aims.TimeTexture_S16()
        itex[0].resize(mesh.vertex(0).size())
        itex0 = itex[0].np
        itex0[:] = 0
        for seed in range(ncc):
            w = np.where(ccs == seed + 1)[0]
            seedp = w[0]
            vdist = vert2d[w] - vert2d[seedp]
            vdist = np.sum(vdist * vdist, axis=1)
            # assume dmax / 10000 is the minimum distance to distinguish points
            # (may be wrong...). We set seed label on vertices vertical with
            # the seed vertex
            dmax2 = np.max(vdist) * 0.000000001
            # dmax = np.sqrt(dmax2)
            itex0[w[vdist <= dmax2]] = 1  # start at 1st vertex

        # then run a distance map from these seeds
        dtex = aims.TimeTexture_FLOAT()
        dtex[0].resize(mesh.vertex(0).size())
        dtex0 = dtex[0].np
        dtex0[:] = -1
        # print('geodesic distance map...')
        # print('dmax:', dmax)
        # print('init mesh:', mesh.vertex(0).np)
        ftex = aims.meshdistance.MeshDistance(mesh2d, itex, False)
        ftex0 = ftex[0].np
        dtex0[ftex0 >= -0.1] = ftex0[ftex0 >= -0.1]

        return dtex

    @staticmethod
    def set_transform(xml_elem, trans):
        mat_str = 'matrix(%s)' % ', '.join(str(x)
                                           for x in np.ravel(trans[:2, :].T))
        xml_elem.set('transform', mat_str)

    def get_transform(self, trans, previous=None, no_3d=False):
        '''
        Parameters
        ----------
        trans: str or XML element
            if str: transform field in the SVG element.
            if element: XML element itself
        previous: np array or None
            parent transform to be composed with
        '''
        # print('transform:', trans_str)
        mat3d = None
        tmat3d = None
        if not no_3d:
            if previous is not None:
                tmat3d = getattr(previous, 'transform_3d', None)
            if not isinstance(trans, str):
                mat3d = self._get_transform(trans, trans.get('transform_3d'),
                                            tmat3d, as_3d=True,
                                            previous_2d=previous)
                hshift = trans.get('height_shift')
                if hshift is not None:
                    hshift = float(hshift) * getattr(self, 'z_scale', 1.)
                    # print('z_scale:', getattr(self, 'z_scale', 1.), hshift)
                    m = np.matrix(np.eye(4))
                    m[2, 3] = hshift
                    # print('height_shift 3d:', m)
                    mat3d = mat3d * m
            else:
                mat3d = tmat3d

        if isinstance(trans, str):
            trans_str = trans
        else:
            trans_str = trans.get('transform')
        mat = self._get_transform(trans, trans_str, previous, as_3d=False)
        if mat3d is not None:
            mat = np.matrix(mat, copy=True)
            mat.transform_3d = mat3d

        return mat

    def _get_transform(self, element, trans_str, previous, as_3d,
                       previous_2d=None):
        '''
        element: xml element
        trans_str: str
        previous: np.matrix
        as_3d: bool
        '''
        if trans_str is None:
            if previous is not None:
                return previous
            if as_3d:
                return np.matrix(np.eye(4))
            else:
                return np.matrix(np.eye(3))

        tr_list = trans_str.split(') ')
        tr_list = [x + ')' for x in tr_list[:-1]] + [tr_list[-1]]
        tmat = previous

        for trans_strx in tr_list:
            if as_3d:
                mat = np.matrix(np.eye(4))
            else:
                mat = np.matrix(np.eye(3))
            i = trans_strx.find('(')
            if not i or trans_strx[-1] != ')':
                print('unrecognized transform: %s', trans_strx)
                return tmat
            ttype = trans_strx[:i]
            tdef1 = trans_strx[i+1:-1].strip().split(',')
            tdef1 = [x.strip() for x in tdef1]
            tdef1 = [x for x in tdef1 if x != '']
            tdef = []
            for t in tdef1:
                tdef += [float(x.strip()) for x in t.split(' ')]
            if ttype == 'matrix' and not as_3d:
                mat[:2, 0] = np.reshape(tdef[:2], (2, 1))
                mat[:2, 1] = np.reshape(tdef[2:4], (2, 1))
                mat[:2, 2] = np.reshape(tdef[4:], (2, 1))
            elif ttype == 'translate':
                mat[0, -1] = tdef[0]
                if len(tdef) > 1:
                    mat[1, -1] = tdef[1]
                if len(tdef) > 2:
                    mat[2, -1] = tdef[2]
            elif ttype == 'scale':
                mat[0, 0] = tdef[0]
                if len(tdef) > 1:
                    mat[1, 1] = tdef[1]
                else:
                    mat[1, 1] = tdef[0]
                if as_3d:
                    if len(tdef) > 2:
                        mat[2, 2] = tdef[2]
                    else:
                        mat[2, 2] = tdef[0]
            elif ttype == 'rotate':
                if as_3d:
                    q1 = aims.Quaternion()
                    q1.fromAxis([1, 0, 0], tdef[0] * np.pi / 180.)
                    q2 = aims.Quaternion()
                    q2.fromAxis([0, 1, 0], tdef[1] * np.pi / 180.)
                    q3 = aims.Quaternion()
                    q3.fromAxis([0, 0, 1], tdef[2] * np.pi / 180.)
                    # rotate around z, then y, then x
                    mat = aims.AffineTransformation3d(q1 * q2 * q3).np
                    if len(tdef) == 6:
                        m2 = np.matrix(np.eye(4))
                        m2[:3, 3] = tdef[3:]
                        mat *= m2
                    else:
                        c = self.get_center(element, previous_2d)
                        m2 = np.matrix(np.eye(4))
                        m2[:3, 3] = c[:3]
                        mat = m2 * mat * np.linalg.inv(m2)
                else:
                    ca = np.cos(tdef[0] / 180. * np.pi)
                    sa = np.sin(tdef[0] / 180. * np.pi)
                    mat[0:2, 0] = np.reshape((ca, sa), (2, 1))
                    mat[0:2, 1] = np.reshape((-sa, ca), (2, 1))
                    if len(tdef) >= 3:
                        m2 = np.matrix(np.eye(3))
                        m2[:2, 2] = ((tdef[1], ), (tdef[2], ))
                        mat = m2 * mat
                        m2[:2, 2] *= -1
                        mat *= m2
            elif ttype == 'skewX':
                mat[0, 1] = np.tan(tdef[0] / 180. * np.pi)
            elif ttype == 'skewY':
                mat[1, 0] = np.tan(tdef[0] / 180. * np.pi)
            elif ttype == 'matrix4' or (ttype == 'matrix' and as_3d):
                mat = np.matrix(np.eye(4))
                mat[:3, 0] = np.reshape(tdef[:3], (3, 1))
                mat[:3, 1] = np.reshape(tdef[3:6], (3, 1))
                mat[:3, 2] = np.reshape(tdef[6:9], (3, 1))
                mat[:3, 3] = np.reshape(tdef[9:], (3, 1))
            elif ttype == 'center4' or ttype == 'center':
                # print('CENTER4', element.get('id'))
                mat = np.matrix(np.eye(4))
                # if isinstance(element, str):
                #     print('center4 in string:', element)
                if not isinstance(element, str):
                    bbox = self.boundingbox(element, previous_2d)
                    # print('bbox:', bbox)
                    if bbox[0] is not None and bbox[1] is not None:
                        c = np.matrix(((bbox[1][0] + bbox[0][0]) / 2,
                                       (bbox[1][1] + bbox[0][1]) / 2, 0., 1.))
                        if tmat is not None:
                            tc = tmat.dot(c.T)
                        else:
                            tc = np.matrix(np.zeros((4, ))).T
                        if tmat is None:
                            tmat = np.matrix(np.eye(4))
                        else:
                            tmat = np.matrix(tmat, copy=True)
                        tmat[:3, 3] += (c.T - tc)[:3]
                        # print('center4, tmat:', tmat)
                        # print('c:', c)
            elif ttype == 'quaternion' and as_3d:
                # (axis.x, axis.y, axis.z, angle_degrees)
                q = aims.Quaternion()
                ax = aims.Point3df(tdef[0], tdef[1], tdef[2])
                ax.normalize()
                q.fromAxis(ax, tdef[3] * np.pi / 180.)
                mat = aims.AffineTransformation3d(q).np
                c = self.get_center(element, previous_2d)
                m2 = np.matrix(np.eye(4))
                m2[:3, 3] = c[:3]
                mat = m2 * mat * np.linalg.inv(m2)
            else:
                msg = f'unrecognized transform function: {ttype}'
                if isinstance(element, str):
                    msg += f' in transform string: {element}'
                else:
                    msg += f' in element: {element.get("id")}'
                raise ValueError(msg)
            if tmat is None:
                tmat = mat
            else:
                tmat = tmat * mat

        # print('mat:', tmat)
        return tmat

    def get_center(self, element, trans):
        bbox = self.boundingbox(element, trans)
        if bbox[0] is not None and bbox[1] is not None:
            c = np.matrix(((bbox[1][0] + bbox[0][0]) / 2,
                           (bbox[1][1] + bbox[0][1]) / 2, 0., 1.)).T
            trans3 = getattr(trans, 'transform_3d', None)
            # print('get_center', element.get('id'), ', trans3d:', trans3)
            if trans3 is not None:
                c = trans3.dot(c)
            hshift = element.get('height_shift')
            if hshift is not None:
                hs = float(hshift) * getattr(self, 'z_scale', 1.)
                c[2] += hs
            return c
        return None

    @staticmethod
    def to_transform(matrix):
        transform = 'matrix(' + ', '.join(
            [str(x) for x in np.asarray(matrix[:2, :].T).ravel()]) + ')'
        return transform

    def boundingbox(self, element, trans=None, exhaustive=True,
                    use_text_xy=False):
        todo = [(element, trans)]
        bbox = [None, None]
        bmin, bmax = bbox
        while todo:
            element, trans = todo.pop(0)
            trans = self.get_transform(element, trans, no_3d=True)
            if element.tag.endswith('}g'):
                todo = [(c, trans) for c in element] + todo
            else:
                if element.tag.endswith('}path') \
                        or element.tag.endswith('}rect') \
                        or element.tag.endswith('}image') \
                        or element.tag.endswith('}circle') \
                        or element.tag.endswith('}ellipse'):
                    if trans is None:
                        trans = np.matrix(np.eye(3))
                    mesh = self.read_path(element, trans)
                    for v in mesh.vertex():
                        if bmin is None:
                            bmin = [v[0], v[1]]
                            bmax = [v[0], v[1]]
                            bbox = [bmin, bmax]
                        else:
                            if v[0] < bmin[0]:
                                bmin[0] = v[0]
                            if v[0] > bmax[0]:
                                bmax[0] = v[0]
                            if v[1] < bmin[1]:
                                bmin[1] = v[1]
                            if v[1] > bmax[1]:
                                bmax[1] = v[1]
                    if not exhaustive:
                        break
                elif use_text_xy and (
                        element.tag.endswith('}text')
                        or element.tag.endswith('}tspan')):
                    x = element.get('x')
                    y = element.get('y')
                    if x is None or y is None:
                        todo = todo = [(c, trans) for c in element] + todo
                    else:
                        tx = np.array(trans.dot([float(x), float(y), 1.]))[0][
                            :2]
                        # print('trans text', x, y, ', tx:', tx)
                        # print('trans:', trans)
                        if bmin is None:
                            bmin = [tx[0], tx[1]]
                            bmax = [tx[0], tx[1]]
                            bbox = [bmin, bmax]
                        else:
                            bmin = [min(bmin[0], tx[0]), min(bmin[1], tx[1])]
                            bmax = [max(bmax[0], tx[0]), max(bmax[1], tx[1])]
        return bbox

    def transform_subtree(self, xml, in_trans, trans, otrans=None):
        ''' in_trans: current transform of xml subtree (out of the subtree)
        trans: transform to be applied
        otrans: transform in the output subtree. default=in_trans
        '''
        if otrans is None:
            otrans = in_trans
        todo = [(xml, in_trans, otrans)]
        while todo:
            element, c_trans, c_otrans = todo.pop(0)
            transm = self.get_transform(element)
            if c_trans is None:
                c_trans = transm
            else:
                c_trans = c_trans * transm
                if hasattr(transm, 'transform_3d'):
                    c_trans.transform_3d = transm.transform_3d
            if c_otrans is None:
                c_otrans = transm
            else:
                c_otrans = c_otrans * transm
                if hasattr(transm, 'transform_3d'):
                    c_otrans.transform_3d = transm.transform_3d
                # element.set('transform', None) # FIXME: how to remove it
            if element.tag.endswith('}g'):
                todo = [(c, c_trans, c_otrans) for c in element] + todo
            else:
                if element.tag.endswith('}path'):
                    iotrans = np.matrix(scipy.linalg.inv(c_otrans))
                    ptrans = iotrans * trans * c_trans
                    d = self.transform_path(element, ptrans)
                    element.set('d', d)
                elif element.tag.endswith('}rect'):
                    iotrans = np.matrix(scipy.linalg.inv(c_otrans))
                    ptrans = iotrans * trans * c_trans
                    self.transform_rect(element, ptrans)

    def style_to_str(self, style):
        return ';'.join(['%s:%s' % (k, str(v)) for k, v in style.items()])

    def transform_style(self, xml_path, trans):
        ''' adapt style in path/rect to scale changes (stroke width etc)
        '''
        style = self.get_style(xml_path)
        if style is not None:
            stroke_width = style.get('stroke-width')
            if stroke_width is not None:
                unit = ''
                i = 1
                while stroke_width[-i] not in '0123456789.':
                    unit = stroke_width[-i] + unit
                    i += 1
                if i > 1:
                    stroke_width = stroke_width[:-i+1]
                stroke_width = float(stroke_width)
                tp = trans.dot([[stroke_width], [0.], [1.]]) \
                    - trans.dot([[0.], [0.], [1.]])
                stroke_width = str(tp[0, 0]) + unit
                style['stroke-width'] = stroke_width
            style_str = self.style_to_str(style)
            xml_path.set('style', style_str)

    def transform_path(self, xml_path, trans):
        ''' trans: transform to be applied
        '''
        def read_point(pdesc, i, pt=None):
            j = i + 1
            try:
                while j < n and pdesc[j] in '0123456789.e-':
                    j += 1
                x = float(pdesc[i:j])
                i = j + 1
                while i < len(pdesc) and pdesc[i] in ' ,':
                    i += 1
            except Exception as e:
                print(e)
                print('failed reading', pt, ', i:', i)
                raise
            return x, i

        cx = xml_path.get(
            '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx')
        cy = xml_path.get(
            '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy')
        if cx is not None and cy is not None:
            tp = np.asarray(trans.dot([[float(cx)], [float(cy)],
                                       [1.]])).ravel()
            xml_path.set(
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cx',
                str(tp[0]))
            xml_path.set(
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}cy',
                str(tp[1]))
            rx = xml_path.get(
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}rx')
            ry = xml_path.get(
                '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}ry')
            if rx is not None:
                tp2 = np.asarray(trans.dot([[float(cx) + float(rx)],
                                            [float(cy)], [1.]])).ravel()
                xml_path.set(
                    '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}rx',
                    str(np.abs(tp2[0] - tp[0])))
            if ry is not None:
                tp2 = np.asarray(trans.dot([[float(cx)],
                                            [float(cy) + float(ry)],
                                            [1.]])).ravel()
                xml_path.set(
                    '{http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd}ry',
                    str(np.abs(tp2[1] - tp[1])))
        # additional stuff for stars
        r1 = xml_path.get('{http://sodipodi.sourceforge.net/DTD/'
                          'sodipodi-0.dtd}r1')
        if r1 is not None:
            scale = np.sqrt(np.sum(np.array(
                trans * np.array([[1, 0, 0]]).T
                - trans * np.array([[0, 0, 0]]).T) ** 2))
            xml_path.set('{http://sodipodi.sourceforge.net/DTD/'
                         'sodipodi-0.dtd}r1',
                         str(float(r1) * scale))
            r2 = xml_path.get('{http://sodipodi.sourceforge.net/'
                              'DTD/sodipodi-0.dtd}r2')
            if r2 is not None:
                xml_path.set('{http://sodipodi.sourceforge.net/DTD/'
                             'sodipodi-0.dtd}r2',
                             str(float(r2) * scale))

        self.transform_style(xml_path, trans)

        pdesc = xml_path.get('d')
        n = len(pdesc)
        i = 0
        cmd = 'M'
        x = 0
        y = 0
        tp = [0, 0]
        first = x, y, tp
        out_cmd = []

        while i < n:
            while(i < n and pdesc[i] == ' '):
                i += 1
            if i == n:
                # print('end of path in:', pdesc)
                break
            # print('i:', i)
            last_x, last_y = x, y
            last_tp = tp
            if pdesc[i] in 'mMcClLhHvVsSqQtTaA':
                cmd = pdesc[i]
                out_cmd.append(cmd)
                # print('cmd:', cmd)
                i += 1
                while pdesc[i] == ' ':
                    i += 1
            elif pdesc[i] in '-0123456789.':
                if cmd not in 'vV':
                    x, i = read_point(pdesc, i, 'x')
                    if cmd >= 'a':
                        x += last_x
                if cmd not in 'hH':
                    y, i = read_point(pdesc, i, 'y')
                    if cmd >= 'a':
                        y += last_y
                tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                if cmd not in 'vV':
                    if cmd >= 'a':
                        out_cmd.append(tp[0] - last_tp[0])
                    else:
                        out_cmd.append(tp[0])
                if cmd not in 'hH':
                    if cmd >= 'a':
                        out_cmd.append(tp[1] - last_tp[1])
                    else:
                        out_cmd.append(tp[1])
                if cmd not in 'vVhH':
                    out_cmd = out_cmd[:-2] \
                        + ['%f,%f' % (out_cmd[-2], out_cmd[-1])]
                # print(x,', ', y)
                if cmd in 'cC':
                    x, i = read_point(pdesc, i, 'x2')
                    y, i = read_point(pdesc, i, 'y2')
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append(
                            '%f,%f' % (tp[0] - last_tp[0], tp[1] - last_tp[1]))
                    else:
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append('%f,%f' % (tp[0], tp[1]))
                    x, i = read_point(pdesc, i, 'x3')
                    y, i = read_point(pdesc, i, 'y3')
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append(
                            '%f,%f' % (tp[0] - last_tp[0], tp[1] - last_tp[1]))
                    else:
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append('%f,%f' % (tp[0], tp[1]))
                elif cmd in 'sSqQ':
                    x, i = read_point(pdesc, i, 'x2')
                    y, i = read_point(pdesc, i, 'y2')
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append(
                            '%f,%f' % (tp[0] - last_tp[0], tp[1] - last_tp[1]))
                    else:
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append('%f,%f' % (tp[0], tp[1]))
                if cmd in 'aA':
                    x, i = read_point(pdesc, i, 'x-axis-rotation')
                    y, i = read_point(pdesc, i, 'large-arc-flag')
                    s, i = read_point(pdesc, i, 'sweep-flag')
                    out_cmd += [x, int(y), int(s)]
                    x, i = read_point(pdesc, i, 'x2')
                    y, i = read_point(pdesc, i, 'y2')
                    if cmd >= 'a':
                        x += last_x
                        y += last_y
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append(
                            '%f,%f' % (tp[0] - last_tp[0], tp[1] - last_tp[1]))
                    else:
                        tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                        out_cmd.append('%f,%f' % (tp[0], tp[1]))
                if cmd == 'm':
                    cmd = 'l'
                    first = x, y, tp
                elif cmd == 'M':
                    cmd = 'L'
                    first = x, y, tp
            elif pdesc[i] in 'zZ':
                out_cmd.append(pdesc[i])
                x, y, tp = first
                i += 1
            else:
                out_cmd.append(pdesc[i])
                i += 1

        return ' '.join([str(x) for x in out_cmd])

    def transform_rect(self, xml_path, trans):
        # additional stuff for squares
        x = xml_path.get('x')
        y = xml_path.get('y')
        x = float(x)
        y = float(y)
        pos = trans.dot([[x], [y], [1.]])
        xml_path.set('x', str(pos[0, 0]))
        xml_path.set('y', str(pos[1, 0]))
        w = xml_path.get('width')
        if w is not None:
            w = float(w)
            pos = trans.dot([[w], [0.], [1.]]) - trans.dot([[0.], [0.], [1.]])
            scale = np.sqrt(np.sum(np.array(pos) ** 2))
            xml_path.set('width', str(scale))
        h = xml_path.get('height')
        if h is not None:
            h = float(h)
            pos = trans.dot([[0.], [h], [1.]]) - trans.dot([[0.], [0.], [1.]])
            scale = np.sqrt(np.sum(np.array(pos) ** 2))
            xml_path.set('height', str(scale))

        self.transform_style(xml_path, trans)

    def filter_element(xml_element, style=None):
        ''' Assign a processing function / method to the given element, a
        cleaning function to be called after the associated sub-tree is
        processed, and a bool to tell if children should be skipped.
        This method can be overloaded and is called for each XML tree element.
        The default implementation returns None, which means that there is no
        specific processing and the default behavior should happen.

        Returns
        -------
        proc: (proc_callable, clean_callable, skip_children) or None
            proc_callable and clean_callable may be None, meaning that normal
            processing should happen.
            The processing callable will be called with 3 arguments:
            (xml_element, transform_matrix, style_dict).
            The cleaning callable will be called without arguments.
            if skip_children is True, children are skipped.
        '''
        return None

    def merge_meshes_by_group(self, meshes):
        if not aims:
            raise RuntimeError('aims module is not available. '
                               'merge_meshes_by_group() needs it.')

        for key, mesh_l in meshes.items():
            if isinstance(mesh_l, list) and len(mesh_l) != 0 \
                    and isinstance(mesh_l[0],
                                   (aims.AimsTimeSurface_2,
                                    aims.AimsTimeSurface_3)):
                mesh = mesh_l[0]
                for smesh in mesh_l[1:]:
                    aims.SurfaceManip.meshMerge(mesh, smesh)
                meshes[key] = mesh

    def reorder_layers(self, xml_et=None):
        if xml_et is None:
            xml_et = self.svg

        labels = []
        for g in xml_et.getroot():
            label = None
            if g.tag != '{http://www.w3.org/2000/svg}g':
                label = g.tag.rsplit('}')[-1]
            else:
                label = g.get(
                    '{http://www.inkscape.org/namespaces/inkscape}label')
            labels.append(label)
        layers = []
        for pl in self.priority_layers:
            if pl in labels:
                index = labels.index(pl)
                layer = xml_et.getroot()[index]
                layers.append(layer)
        for layer in layers:
            xml_et.getroot().remove(layer)
        for index, layer in enumerate(layers):
            xml_et.getroot().insert(index, layer)

    def read_paths(self, xml_et):
        '''
        Parse XML tree and extract meshes, text and other objects

        Parameters
        ----------
        xml_et: XML tree
            obtained using xml.etree.cElementTree.parse(svg_filename)
        '''
        if not aims:
            raise RuntimeError('aims module is not available. read_paths() '
                               'needs it.')
        # move some higher priority layers first (like metadata which are used
        # by later ones)
        self.reorder_layers()

        trans = np.matrix(np.eye(3))
        todo = [(xml_et.getroot(), trans, None, [])]
        self.mesh = aims.AimsTimeSurface(2)
        self.mesh_list = []
        self.mesh_dict = {}
        index = 0
        while todo:
            child, trans, main_group, parents = todo.pop(0)
            if child is None:
                # this is a hacked special code to call cleaner
                cleaners = trans
                if not isinstance(cleaners, (tuple, list)):
                    cleaners = [cleaners]
                for cleaner in cleaners:
                    cleaner()
                continue
            # allow to trick main_group
            self.main_group = main_group
            del main_group

            style = self.get_style(child)
            if style is None:
                style = {}  # so that read_path will not parse it again

            trans = self.get_transform(child, trans)

            if self.debug:
                print('process child:', child)

            reader = None
            cleaner = None
            skip_children = False
            reader_cleaner = self.filter_element(child, style)
            if reader_cleaner is not None:
                reader, cleaner, skip_children = reader_cleaner
            if reader is not None:
                reader(child, trans, style)
            if cleaner not in (None, [], ()):
                # insert a special code to do something at the end of this tree
                todo.insert(0, (None, cleaner, None, parents))
            if reader is None and style and style.get('display') == 'none' \
                    and child.get('{http://www.inkscape.org/namespaces/inkscape}label') \
                        not in self.explicitly_show:
                # hidden layer, skip it
                continue
            if reader is not None:
                pass
            elif child.tag.endswith('}defs') or child.tag == 'defs':
                # skip defs sub-tree
                continue
            elif child.tag in ('path', 'rect', 'polygon', 'circle') \
                    or child.tag.endswith('}path') \
                    or child.tag.endswith('}rect') \
                    or child.tag.endswith('}polygon') \
                    or child.tag.endswith('}circle') \
                    or child.tag.endswith('}ellipse'):
                child_mesh = self.read_path(child, trans, style)
                if self.main_group.endswith('_text'):
                    # mesh in a text layer: should be rendered as the text, in
                    # a fixed orientation from the camera
                    # DOTO FIXME
                    # for now we just skip and ignore it...
                    pass
                elif self.concat_mesh == 'merge':
                    aims.SurfaceManip.meshMerge(self.mesh, child_mesh)
                    self.mesh.header().update(child_mesh.header())
                    self.get_textures(self.mesh, child, parents)
                elif self.concat_mesh == 'time':
                    self.mesh.vertex(index).assign(child_mesh.vertex())
                    self.mesh.polygon(index).assign(child_mesh.polygon())
                    self.mesh.header().update(child_mesh.header())
                    self.get_textures(self.mesh, child, parents)
                    index += 1
                elif self.concat_mesh == 'bygroup':
                    mesh = self.mesh_dict.setdefault(self.main_group,
                                                     aims.AimsTimeSurface(2))
                    aims.SurfaceManip.meshMerge(mesh, child_mesh)
                    material = mesh.header().get('material')
                    mesh.header().update(child_mesh.header())
                    if material is not None:
                        mesh.header()['material'] = material
                    self.get_textures(mesh, child, parents)
                elif self.concat_mesh == 'list_bygroup':
                    meshes = self.mesh_dict.setdefault(self.main_group, [])
                    try:
                        meshes.append(child_mesh)
                    except Exception as e:
                        print('FAILED TO READ MESH:', e)
                        print('main_group:', self.main_group)
                        print('child item tag:', child.tag)
                        print('child sub-items:', list(child.items()))
                        print('child mesh type:', type(child_mesh))
                        print('child mesh:', child_mesh)
                        print('meshes type:', type(meshes))
                        print('meshes:', meshes)
                        raise
                    self.get_textures(meshes[0], child, parents)
                    try:
                        if 'material' not in meshes[0].header():
                            meshes[0].header().update(child_mesh.header())
                    except Exception:
                        print('material:', self.main_group, meshes)
                        raise
                else:
                    self.mesh_list.append(child_mesh)
                    self.get_textures(self.mesh, child, parents)
            elif child.tag.endswith('}clipPath') or child.tag == 'clipPath':
                # print('clipPath')
                # skip clipPaths
                pass
            elif child.tag.endswith('}text') or child.tag == 'text':
                self.parse_text(child, parents, trans, style)
            elif child.tag.endswith('}tspan') or child.tag == 'tspan':
                self.parse_subtext(child, parents, trans, style)
            elif child.tag.endswith('}g') or child.tag == 'g':
                if self.main_group is None:
                    self.main_group = child.get('id')
                if self.is_layer(child):
                    if child.get('text') == 'true':
                        # print('text layer')
                        # text layer: prepare special "mesh" object
                        tgroup = self.main_group
                        if not tgroup.endswith('_text'):
                            tgroup += '_text'
                            self.main_group = tgroup
                        self.mesh_dict[tgroup] = {'object_type': 'List',
                                                  'objects': []}
                elif len(parents) != 0 and self.is_layer(parents[-1]) \
                        and (self.main_group.endswith('_text')
                             or parents[-1].get('text') == 'true'):
                    # sub-group inside a text layer: create a new list object
                    self.make_text_group(child, trans)
            if not skip_children and len(child) != 0:
                # set the metadata layer, if present, first, because it may
                # contain information used by other items
                meta = []
                other = []
                for c in child:
                    if c.tag.endswith('}metadata'):
                        meta.append((c, trans, self.main_group,
                                     parents + [child]))
                    else:
                        other.append((c, trans, self.main_group,
                                      parents + [child]))
                todo = meta + other + todo

        if self.concat_mesh in ('merge', 'time'):
            return self.mesh
        elif self.concat_mesh in ('bygroup', 'list_bygroup'):
            return self.mesh_dict
        return self.mesh_list

    @staticmethod
    def is_group(xml_item):
        return xml_item.tag.endswith('}g') or xml_item.tag == 'g'

    @staticmethod
    def is_layer(xml_item):
        return SvgToMesh.is_group(xml_item) \
            and xml_item.get(
                '{http://www.inkscape.org/namespaces/inkscape}groupmode') \
                    == 'layer'

    def parse_text(self, child, parents, trans, style):
        if len(parents) == 0 or self.is_layer(parents[-1]):
            # not inside a group: create a new group
            self.make_text_group(child, trans)

        tgroup = self.main_group
        if not tgroup.endswith('_text'):
            tgroup += '_text'
        current_text = self.mesh_dict.get(tgroup)
        if current_text is None:
            self.mesh_dict[tgroup] = {'object_type': 'List', 'objects': []}
            current_text = self.mesh_dict.get(tgroup)
            self.make_text_group(child, trans)
        current_text_o = current_text['objects'][-1]
        text = child.text
        if isinstance(text, bytes):
            text = text.decode()
        text_desc = self.text_description(
            child, current_text_o, trans, style=style, text=text)
        current_text_o['objects'].append(text_desc)
        # determine relative position to group
        if not child.get('x') or not child.get('y'):
            if len(child[:]) != 0 and child[0].get('x') and child[0].get('y'):
                # coords on tspan item
                pos = (float(child[0].get('x')),
                       float(child[0].get('y')))
            else:
                print('text without coords, id:', child.get('id'))
                print('main_group:', self.main_group)
                print(child)
                print(child.items())
                pos = (0., 0.)
        else:
            pos = (float(child.get('x')), float(child.get('y')))
        # trans = self.get_transform(child, trans)
        if trans is not None:
            p0 = np.array(((pos[0], pos[1], 1.),)).T
            pos = list(np.array(trans.dot(p0)).ravel()[:2])
        gpos = current_text_o['properties']['position']
        rpos = [pos[0] - gpos[0], pos[1] - gpos[1]]
        text_desc['properties']['position'] = rpos
        text_desc['properties']['local_pos_transformed'] = False
        self.update_text_group_size(current_text_o, text_desc)

    def update_text_group_size(self, current_text_o, text_desc):
        size, anchor = self.text_size(text_desc)
        rpos = text_desc['properties']['position']
        # go to local box referential (with rotation)
        if not text_desc['properties'].get('local_pos_transformed', True):
            trans = current_text_o['properties'].get('transform')
            if trans is not None:
                trans = np.matrix(trans)
                trans[:2, 2] = 0  # local without tranlation
                itrans = np.linalg.inv(trans)
                locpoint = np.array(rpos + [1.])
                rpos = np.array(itrans.dot(locpoint))[0][:2]
                # update rpos in text_desc
                text_desc['properties']['position'] = rpos.tolist()
            # now it is transformed.
            del text_desc['properties']['local_pos_transformed']

        bbox = [rpos[0] - anchor[0], rpos[1] - anchor[1],
                rpos[0] + size[0] - anchor[0], rpos[1] + size[1] - anchor[1]]
        old_size = current_text_o['properties'].get('size', [0., 0.])
        bbshift = current_text_o['properties'].get('bbox_shift', [0., 0.])
        old_bbox = [bbshift[0], bbshift[1],
                    bbshift[0] + old_size[0], bbshift[1] + old_size[1]]
        bbox = [min(old_bbox[0], bbox[0]), min(old_bbox[1], bbox[1]),
                max(old_bbox[2], bbox[2]), max(old_bbox[3], bbox[3])]
        size = [bbox[2] - bbox[0], bbox[3] - bbox[1]]
        current_text_o['properties']['size'] = size
        bbshift[0] = bbox[0]
        bbshift[1] = bbox[1]
        current_text_o['properties']['bbox_shift'] = bbshift

    def make_text_group(self, xml_item, trans):
        tgroup = self.main_group
        if not tgroup.endswith('_text'):
            tgroup += '_text'
        props = {
            'object_type': 'TransformedObject',
            'properties': {},
            'objects': [],
        }
        if not xml_item.get('x') or not xml_item.get('y'):
            pos = None
            children = [(it, self.get_transform(it, trans))
                        for it in xml_item[:]]
            while children:
                child, tr = children.pop(0)
                x = child.get('x')
                y = child.get('y')
                if x is not None and y is not None:
                    p0 = np.array(((float(x), float(y), 1.),)).T
                    p1 = list(np.array(tr.dot(p0)).ravel()[:2])
                    pos = (p1[0], p1[1])
                    break
                else:
                    children += [(it, self.get_transform(it, tr))
                                 for it in child[:]]
            if pos is None:
                print('text group without coords, id:', xml_item.get('id'))
                print('main_group:', self.main_group)
                print(xml_item)
                print(xml_item.items())
                pos = (0., 0.)
        else:
            pos = (float(xml_item.get('x')), float(xml_item.get('y')))
            if trans is not None:
                p0 = np.array(((pos[0], pos[1], 1.),)).T
                pos = list(np.array(trans.dot(p0)).ravel()[:2])
        trobj_props = {'position': [pos[0], pos[1], 4.]}  # 4 is arbitrary
        if trans is not None:
            # trans2 = np.matrix(trans, copy=True)
            # trans2[:2, 2] -= np.array([pos[:2]]).T
            if not np.all(trans != np.eye(3)):
                trobj_props['transform'] = trans.tolist()
        props['properties'] = trobj_props
        g = self.mesh_dict.setdefault(tgroup, {'object_type': 'List',
                                               'objects': []})
        if len(g['objects']) != 0 and len(g['objects'][-1]['objects']) == 0:
            print('empty text group in layer', tgroup)
            del g['objects'][-1]
        g['objects'].append(props)
        return props

    def parse_subtext(self, child, parents, trans, style):
        text = child.text
        tgroup = self.main_group
        if not tgroup.endswith('_text'):
            tgroup += '_text'
        current_text_o = self.mesh_dict[tgroup]['objects'][-1]
        try:
            current_text_co = current_text_o['objects'][-1]
            current_text_d = current_text_co['properties']
        except Exception:
            print('error in text item:', file=sys.stderr)
            print('current_text_o:', repr(current_text_o))
            print('main_group:', self.main_group)
            # traceback.print_exc()
            raise
        try:
            current_text = current_text_d['text']
        except Exception as e:
            print('error in current_text_d["text"]')
            print(current_text_d)
            raise
        if text is None:
            print('tspan without text, id:', child.get('id'))
            text = ''
        elif isinstance(text, bytes):
            text = child.text.decode()
        if not current_text:
            current_text = text
        else:
            current_text += '\n' + text
        current_text_d['text'] = current_text
        self.update_text_group_size(current_text_o, current_text_co)

    def text_description(self, xml_item, props, trans=None, style=None,
                         text=''):
        font_size = None
        obj_props = {'text': text,
                     'position': [0, 0, 0.],
                     'font_size': 10.,
                     'scale': 1.,
                     'material': {'diffuse': [.5, .5, .5, 1.]}}
        trobj_props = props['properties']
        tobject = {
            'object_type': 'TextObject',
            'name': 'Text',
            'properties': obj_props,
        }
        if style is not None:
            text_anchor = style.get('text-anchor')
            if text_anchor is not None:
                obj_props['text-anchor'] = text_anchor
            font_size = style.get('font-size')
            scale = 1.  # arbitrary
            if font_size is not None:
                unit = ''
                i = 1
                while font_size[-i] not in '0123456789.':
                    unit = font_size[-i] + unit
                    i += 1
                if i > 1:
                    font_size = font_size[:-i+1]
                font_size = float(font_size)
                if trans is not None:
                    pt = trans.dot([[0.], [font_size], [1.]]) \
                        - trans.dot([[0.], [0.], [1.]])
                    font_size = np.sqrt(pt[0, 0] * pt[0, 0]
                                        + pt[1, 0] * pt[1, 0])
                uscale = self.unitscale(unit) / self.unitscale('pt')
                font_size *= uscale
                if font_size < 10:
                    scale *= font_size / 10.
                    font_size = 10.
                elif font_size > 20:
                    scale *= font_size / 20.
                    font_size = 20
                obj_props['font_size'] = font_size
                obj_props['scale'] = scale
            font_family = style.get('font-family')
            font_family = self.font_substitutions.get(font_family, font_family)
            if font_family is not None:
                obj_props['font_family'] = font_family
            line_height = style.get('line-height')
            if line_height is not None:
                if line_height.endswith('%'):
                    line_height = float(line_height[:-1]) / 100
                else:
                    line_height = float(line_height)
                if line_height != 0:
                    obj_props['line_height'] = line_height
            fill = style.get('fill')
            if fill is not None and fill != 'none':
                try:
                    col = [float(int(fill[1:3], 16)) / 255.,
                           float(int(fill[3:5], 16)) / 255.,
                           float(int(fill[5:7], 16)) / 255.,
                           1.]
                except Exception as e:
                    print(e)
                    print('error while reading text color:', repr(fill))
                    print('in element:', xml_item.get('id'))
                    raise
                # avoid dark colors (intensity < 0.4)
                if col[0] * col[0] + col[1] * col[1] + col[2] * col[2] < 0.16:
                    col = [1., 1., 1., 1.]
                obj_props['material'] = {'diffuse': col}
            bg = style.get('stroke')
            if bg is not None and bg != 'none':
                try:
                    bgcol = [float(int(bg[1:3], 16)) / 255.,
                             float(int(bg[3:5], 16)) / 255.,
                             float(int(bg[5:7], 16)) / 255.,
                             1.]
                except Exception as e:
                    print(e)
                    print('error while reading text fg color:', repr(bg))
                    print('in element:', xml_item.get('id'))
                    raise
                trobj_props['background'] = bgcol
        return tobject

    @staticmethod
    def text_size(text_item):
        if not text_item:
            return [[0., 0.], [0., 0.]]
        text_obj = text_item['properties']
        scale = text_obj.get('scale', 1.)
        fscale = 1.
        fsize = text_obj.get('font_size', 10.) * fscale
        text = text_obj.get('text')
        if not text:
            return [[0., 0.], [0., 0.]]
        if isinstance(text, bytes):
            text = text.decode()
        text = text.split('\n')
        try:
            # try using Qt
            from soma.qt_gui.qt_backend import QtGui, QtCore

            if QtCore.QCoreApplication.instance() is None:
                qapp = QtGui.QGuiApplication([])

            line_height = text_obj.get('line_height', 1.)
            ffamily = text_obj.get('font_family')
            if ffamily is None:
                ffamily = QtGui.QFont().family()
            font = QtGui.QFont(ffamily, int(round(fsize)))
            fm = QtGui.QFontMetricsF(font)
            width = 0
            height = 0
            anchor = None
            bbox = None
            a_line_height = (fm.height() + fm.leading()) * line_height
            for iline, line in enumerate(text):
                if line == '':
                    line = 'I'
                r = fm.tightBoundingRect(line)
                if bbox is None:
                    bbox = [r.left(), r.top(), r.right(), r.bottom()]
                else:
                    bbox = [
                        min(bbox[0], r.left()),
                        min(bbox[1],
                            r.top() + iline * a_line_height),
                        max(bbox[2], r.right()),
                        max(bbox[3],
                            r.bottom() + iline * a_line_height)]
            width = bbox[2] - bbox[1]
            height = bbox[3] - bbox[1]
            width *= scale / fscale
            height *= scale / fscale
            anchor = [0., -bbox[1] * scale / fscale]
            tanchor = text_obj.get('text-anchor')
            if tanchor == 'middle':
                anchor[0] = width / 2.  # centered
            # print('text size:', width, height, anchor, scale, fscale, fsize, text)

        except ImportError:
            # assume fixed size font, with height/width ratio of 3.3.
            # also assume a final scale factor of 2.12 (old: 0.0827)
            # this is arbitrary but I don't know how to do better
            fscale *= 2.12 * fsize  # 0.0827
            hw_ratio = 2.5
            height = len(text) * fscale
            width = max([len(line) for line in text]) * fscale / hw_ratio
            anchor = [width / 2., fscale * 0.9]

        return ([width, height], anchor)

    @staticmethod
    def extrude(mesh, distance):
        if not aims:
            raise RuntimeError('aims module is not available. extrude() '
                               'needs it.')

        up = aims.AimsTimeSurface(mesh)
        tr = aims.AffineTransformation3d()
        tr.setTranslation([0., 0., distance])
        trans3d = mesh.header().get('transformation')
        if trans3d:
            trans3d = aims.AffineTransformation3d(trans3d)
            trans3d.setTranslation([0, 0, 0])
            trans = trans3d.transform(0., 0., distance)
            tr.setTranslation(trans)
        aims.SurfaceManip.meshTransform(up, tr)

        walls = aims.AimsTimeSurface(3)
        walls.header().update(
            {k: copy.deepcopy(v) for k, v in mesh.header().items()})
        # restore shared texture images (avoid duplications)
        if 'textures' in mesh.header():
            for tt, tv in mesh.header()['textures'].items():
                tim = tv.get('image')
                if tim is not None:
                    walls.header()['textures'][tt]['image'] = tim
        material = {}
        if 'material' in walls.header():
            material = walls.header()['material']
        material['face_culling'] = 0
        walls.header()['material'] = material
        vert0 = mesh.vertex()
        poly0 = mesh.polygon()
        vert = walls.vertex()
        poly = walls.polygon()

        vert.assign(vert0 + up.vertex())
        nv = len(vert0)

        for line in poly0:
            poly.append((line[0], line[1], nv + line[0]))
            poly.append((line[1], nv + line[1], nv + line[0]))

        walls.updateNormals()

        return up, walls

    @staticmethod
    def prune_empty_groups(xml):
        todo = [(xml.getroot(), None, True)]
        count = 0
        total = 0

        while todo:
            element, parent, begin = todo.pop(0)
            total += 1
            if element.tag.endswith('}g'):
                if len(element) == 0:
                    if parent is not None:
                        parent.remove(element)
                        count += 1
                        continue
            if begin:
                added = [(child, element, True) for child in element]
                if parent is not None:
                    added.append((element, parent, False))
                todo = added + todo
        print('pruned', count, 'elements out of', total)

    def copy_svg(self, xml):
        xml2 = copy.deepcopy(xml)
        todo = [xml2]
        while todo:
            item = todo.pop(0)
            eid = item.get('id')
            if eid is None:
                eid = 'copy'
            elif '-' in eid:
                eid = '-'.join(eid.split('-')[:-1]) + '_copy'
            else:
                eid = eid + '_copy'
            eid += '-%d' % self.id_count
            self.id_count += 1
            item.set('id', eid)
            if item.tag == 'g' or item.tag.endswith('}g'):
                todo = item[:] + todo
        return xml2

    def copy_item_properties(self, source, dest):
        for prop in self.keep_transformed_properties:
            value = source.get(prop)
            if value is not None:
                dest.set(prop, value)

    def replace_filter_element(self, xml):
        '''
        Inside replace_elements, this function is called for each xml element,
        and should return either the element itself (no replacement), or None
        (element is discarded), or a replaced XML element.

        The default method always returns the input element.
        '''
        return xml

    def replace_elements(self, xml, replace_dict):
        # replace_dict: {'id': {eid: {label: label, element: xml,
        #                              children: bool, center: (x, y)}},
        #                'label': {label: {element: xml, children: bool,
        #                                  center: (x, y)}}}
        todo = [(xml.getroot(), np.matrix(np.eye(3)), None, None, None)]
        count = 0
        total = 0
        if replace_dict is None:
            replace_dict = {}
        rid = replace_dict.get('id', {})
        rlabel = replace_dict.get('label', {})

        # print('replace_dict:', replace_dict)

        while todo:
            element, trans, parent, current_id, current_label = todo.pop(0)
            element2 = self.replace_filter_element(element)
            if element2 is None:
                parent.remove(element)
                continue
            element = element2
            total += 1
            eid = element.get('id')
            if eid is not None and eid.endswith('_proto'):
                continue  # replacement prototype: don't replace with itself
            glabel = element.get('glabel')  # glabel can replace id
            relem = None
            replace_children = False
            if eid in rid:
                relem = rid[eid]
            elif glabel in rid:
                relem = rid[glabel]
                eid = glabel
            elif eid is not None and '-' in eid:
                eid = '-'.join(eid.split('-')[:-1])
                if eid in rid:
                    relem = rid[eid]
            if relem is not None:
                current_id = eid
            label = element.get('label')
            if label is not None:
                current_label = label
                if relem is not None:
                    elabel = relem.get('label')
                    if elabel is not None and elabel != label:
                        relem = None
                else:
                    relem = rlabel.get(label)

            if relem is None and current_label:
                relem = rlabel.get(current_label)
            if relem is None and current_id:
                relem = rid.get(current_id)

            if relem is not None:
                item = relem['element']
                replace_children = relem.get('children', False)
                center = relem.get('center')
                # print('replace element:', eid, label, relem)
                if element.get(
                        '{http://www.inkscape.org/namespaces/inkscape}'
                        'groupmode') == 'layer' \
                          or element.get('groupmode') == 'layer':
                    # it's a layer (or group marked as 'groupmode=layer'):
                    # process children
                    replace_children = True
                if replace_children:
                    trans = self.get_transform(element, trans)

                    added = [(child, trans, element, current_id, current_label)
                             for child in element]
                    todo = added + todo
                else:
                    bbox = self.boundingbox(element, trans)
                    ecent = ((bbox[0][0] + bbox[1][0]) / 2,
                             (bbox[0][1] + bbox[1][1]) / 2)
                    tr = np.matrix(np.eye(3))
                    tr[0, 2] = ecent[0] - center[0]
                    tr[1, 2] = ecent[1] - center[1]
                    parent.remove(element)
                    new_item = self.copy_svg(item)
                    self.copy_item_properties(element, new_item)
                    eid = new_item.get('id')
                    if '-' in eid:
                        eid = '-'.join(eid.split('-')[:-1])
                    eid += '-%d' % self.id_count
                    new_item.set('id', eid)
                    self.id_count += 1
                    self.transform_subtree(new_item, relem.get('trans'), tr,
                                           trans)
                    parent.append(new_item)
            else:
                added = [(child, trans, element, current_id, current_label)
                         for child in element]
                todo = added + todo

    def cut_segment(self, v1, v2, bmin, bmax):
        if v1[0] < bmin[0]:
            if v2[0] < bmin[0]:
                return None  # drop segment
            else:
                v1b = type(v1)(v1)
                v1b[0] = bmin[0]
                v1b[1] = v1[1] \
                    + (v2[1] - v1[1]) * (bmin[0] - v1[0]) / (v2[0] - v1[0])
            return self.cut_segment(v1b, v2, bmin, bmax)
        if v1[0] > bmax[0]:
            if v2[0] > bmax[0]:
                return None  # drop segment
            else:
                v1b = type(v1)(v1)
                v1b[0] = bmax[0]
                v1b[1] = v1[1] \
                    + (v2[1] - v1[1]) * (bmax[0] - v1[0]) / (v2[0] - v1[0])
            return self.cut_segment(v1b, v2, bmin, bmax)

        if v2[0] < bmin[0]:
            v2b = type(v2)(v2)
            v2b[0] = bmin[0]
            v2b[1] = v2[1] \
                + (v1[1] - v2[1]) * (bmin[0] - v2[0]) / (v1[0] - v2[0])
            return self.cut_segment(v1, v2b, bmin, bmax)
        if v2[0] > bmax[0]:
            v2b = type(v2)(v2)
            v2b[0] = bmax[0]
            v2b[1] = v2[1] \
                + (v1[1] - v2[1]) * (bmax[0] - v2[0]) / (v1[0] - v2[0])
            return self.cut_segment(v1, v2b, bmin, bmax)

        if v1[1] < bmin[1]:
            if v2[1] < bmin[1]:
                return None  # drop segment
            else:
                v1b = type(v1)(v1)
                v1b[1] = bmin[1]
                v1b[0] = v1[0] \
                    + (v2[0] - v1[0]) * (bmin[1] - v1[1]) / (v2[1] - v1[1])
            return self.cut_segment(v1b, v2, bmin, bmax)
        if v1[1] > bmax[1]:
            if v2[1] > bmax[1]:
                return None  # drop segment
            else:
                v1b = type(v1)(v1)
                v1b[1] = bmax[1]
                v1b[0] = v1[0] \
                    + (v2[0] - v1[0]) * (bmax[1] - v1[1]) / (v2[1] - v1[1])
            return self.cut_segment(v1b, v2, bmin, bmax)

        if v2[1] < bmin[1]:
            v2b = type(v2)(v2)
            v2b[1] = bmin[1]
            v2b[0] = v2[0] \
                + (v1[0] - v2[0]) * (bmin[1] - v2[1]) / (v1[1] - v2[1])
            return (v1, v2b)
        if v2[1] > bmax[1]:
            v2b = type(v2)(v2)
            v2b[1] = bmax[1]
            v2b[0] = v2[0] \
                + (v1[0] - v2[0]) * (bmax[1] - v2[1]) / (v1[1] - v2[1])
            return (v1, v2b)

        return (v1, v2)

    def clip_mesh(self, mesh, bmin, bmax):
        vert = mesh.vertex()
        poly = mesh.polygon()
        cmesh = type(mesh)()
        cmesh.header().update(mesh.header())
        cvert = cmesh.vertex()
        cpoly = cmesh.polygon()
        # print('clip vertices:', len(vert), ', segments:', len(poly))
        pts = {}  # reverse map pos: index
        ns = len(poly)

        for i, p in enumerate(poly):
            if i != 0 and i % 1000 == 0:
                print(f'\rseg: {i} / {ns}: {int(i*100 /ns)}% ', end='')
            v1 = vert[p[0]]
            v2 = vert[p[1]]
            npoly = self.cut_segment(v1, v2, bmin, bmax)
            if npoly is None:
                continue
            v1b, v2b = npoly
            index1 = pts.get(tuple(v1b))
            if index1 is None:
                index1 = len(pts)
                pts[tuple(v1b)] = index1
                cvert.append(v1b)
            index2 = pts.get(tuple(v2b))
            if index2 is None:
                index2 = len(pts)
                pts[tuple(v2b)] = index2
                cvert.append(v2b)
            cpoly.append((index1, index2))
        print()

        return cmesh

    def mesh_to_pyclipper(self, mesh, scale=1000):
        pc_mesh = mesh.header().get('pyclipper')
        if pc_mesh:
            return pc_mesh

        vert = mesh.vertex()
        poly = mesh.polygon()
        paths = []
        path = []
        closed = False
        first = None
        prev = None

        for i, p in enumerate(poly):
            v1 = [int(x) for x in vert[p[0]] * scale][:2]
            v2 = [int(x) for x in vert[p[1]] * scale][:2]
            if first is None or prev != p[0]:
                if first is not None:
                    paths.append(path)
                    path = []
                path += [v1, v2]
                first = p[0]
                prev = p[1]
            elif first == p[1]:
                closed = True
                prev = None
                first = None
                paths.append(path)
                path = []
            else:
                path.append(v2)
                prev = p[1]
        if path:
            paths.append(path)

        return paths, closed

    def pyclipper_to_mesh(self, tree, scale=1000., itrans=None):
        iscale = 1. / scale
        mesh = aims.AimsTimeSurface_2()
        vert = []
        poly = []
        todo = [tree]
        while todo:
            item = todo.pop(0)
            if item.Contour:
                n = len(vert)
                vert += [(x * iscale, y * iscale, 0.) for x, y in item.Contour]
                poly += [(i, i+1) for i in range(n, len(vert) - 1)]
                if not item.IsOpen:
                    poly.append((len(vert) - 1, n))
            if item.Childs:
                todo += item.Childs

        if itrans is not None and len(vert) != 0:
            vert = np.asarray(vert).T
            vert[2, :] = 1.
            vert = (itrans * vert).T
            vert[:, 2] = 0.
        mesh.vertex().assign(vert)
        mesh.polygon().assign(poly)
        return mesh

    def mesh_to_path(self, mesh, style=None):
        element = ET.Element('{http://www.w3.org/2000/svg}path')
        if style is None:
            style = 'stroke-width: 1.1; stroke-dasharray: none; ' \
                'stroke: #d7b497; stroke-opacity: 1;'
            # TODO: else get material etc.

        element.set('style', style)

        vert = mesh.vertex()
        poly = mesh.polygon()

        prev = None
        first = None
        lastx = 0
        lasty = 0
        pdesc = []
        for p in poly:
            v1 = vert[p[0]]
            v2 = vert[p[1]]
            if first is None or prev != p[0]:
                x = v1[0] - lastx
                y = v1[1] - lasty
                pdesc.append(f'm {x},{y}')
                x = v2[0] - v1[0]
                y = v2[1] - v1[1]
                pdesc.append(f'{x},{y}')
                prev = p[1]
                first = p[0]
            elif first == p[1]:
                pdesc.append('z')
                first = None
                prev = None
            else:
                x = v2[0] - lastx
                y = v2[1] - lasty
                pdesc.append(f'{x},{y}')
                prev = p[1]
            lastx = v2[0]
            lasty = v2[1]

            if len(pdesc) >= 1000:
                # squeeze for memory / perf
                pdesc = [' '.join(pdesc)]

        pdesc = ' '.join(pdesc)
        element.set('d', pdesc)

        return element

    def clip_path_rect(self, xml_path, trans, bmin, bmax):
        mesh = self.read_path(xml_path, trans)
        cmesh = self.clip_mesh(mesh, bmin, bmax)
        style = self.get_style(xml_path)
        clipped = self.mesh_to_path(cmesh, style)

        return clipped

    def clip_path(self, xml_path, trans, clip_poly, clip_trans=None):
        try:
            import pyclipper
        except ImportError:
            global _pyclipper_failed
            if not _pyclipper_failed:
                _pyclipper_failed = True
                print('PROBLEM: the pyclipper module is not installed. '
                      'Polygon clipping will not be possible without this '
                      'module. Please install it using the command:',
                      file=sys.stderr)
                print('python -m pip install pyclipper', file=sys.stderr)
                print('For the time being, some objects will disappear from '
                      'clipped zoomed regions.')
                return None

        mesh = self.read_path(xml_path, trans)
        if len(mesh.polygon()) == 0:
            return None
        if isinstance(clip_poly, aims.AimsTimeSurface_2):
            clip_mesh = clip_poly
        else:
            clip_mesh = self.read_path(clip_poly, clip_trans)
        clip, _ = self.mesh_to_pyclipper(clip_mesh)
        subj, closed = self.mesh_to_pyclipper(mesh)
        del mesh, clip_mesh
        pc = pyclipper.Pyclipper()
        # print('clip:', clip)
        pc.AddPath(clip[0], pyclipper.PT_CLIP, True)
        # print('subj:', subj)
        pc.AddPaths(subj, pyclipper.PT_SUBJECT, closed)
        clipped = pc.Execute2(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD,
                              pyclipper.PFT_EVENODD)
        itrans = None
        if trans is not None:
            itrans = np.linalg.inv(trans)
        cmesh = self.pyclipper_to_mesh(clipped, itrans=itrans)
        del clipped
        style = self.get_style(xml_path)
        clipped_xml = self.mesh_to_path(cmesh, style)

        return clipped_xml

    def remove_paths_outside_bounds(self, xml_group, bbmin, bbmax, trans=None):
        trans = self.get_transform(xml_group, trans)

        to_remove = []
        for path in xml_group:
            pbmin, pbmax = self.boundingbox(path, trans)
            if pbmin[0] > bbmax[0] or pbmin[1] > bbmax[1] \
                    or pbmax[0] < bbmin[0] or pbmax[1] < bbmin[1]:
                to_remove.append(path)
        for path in to_remove:
            xml_group.remove(path)

    def merge_paths(self, xml_group, trans=None):
        if len(xml_group) == 0:
            return
        trans = self.get_transform(xml_group, trans)
        path = xml_group[0]
        ptrans = self.get_transform(path, trans)
        d = [self.transform_path(path, ptrans)]
        for p in xml_group[1:]:
            ptrans = self.get_transform(p, trans)
            d.append(self.transform_path(p, ptrans))
        d = ' '.join(d)
        path.set('d', d)
        for i in range(len(xml_group) - 1):
            xml_group.remove(xml_group[1])

    def save_mesh_dict(self, meshes, dirname, mesh_format='.obj',
                       mesh_wf_format='.obj', lights=None, verbose=True):
        '''
        mesh_format may be a valid mesh extension (".obj", ".gii", ".mesh") or
        GLTF (".gltf" or ".glb"), or None (not saved here).

        If GLTF is used a scene dict (JSON) is returned in the output summary
        under the key "gltf_scene".
        '''
        import json
        from soma.aims import gltf_io
        if not os.path.exists(dirname):
            os.makedirs(dirname)
        summary = {}
        if mesh_format in ('.gltf', '.glb') or mesh_wf_format in ('.gltf',
                                                                  '.glb'):
            matrix = [-1, 0, 0, 0,  0, 1, 0, 0,  0, 0, 1, 0,  0, 0, 0, 1]
            gltf = gltf_io.default_gltf_scene(matrix)
            summary['gltf_scene'] = gltf

        for key, mesh in meshes.items():
            # if key is None:
                # print('key is None, mesh:', mesh)
                # continue
            if type(mesh) in (list, dict):
                # dict object (text...), save as .aobj
                filename = os.path.join(dirname,
                                        key.replace('/', '_') + '.aobj')
                if verbose:
                    print('saving:', filename, '(', key, ')')
                try:
                    json.dump(mesh, open(filename, 'w'))
                    summary.setdefault('text_fnames', {})[filename] = key
                except Exception as e:
                    print(e)
                    if verbose:
                        print('while saving object:', mesh)
                    try:
                        os.unlink(filename)
                    except Exception:
                        pass
            else:
                if isinstance(mesh, aims.AimsTimeSurface_2):
                    ext = mesh_wf_format
                else:
                    ext = mesh_format
                if isinstance(ext, (tuple, list)):
                    ext, format = ext
                else:
                    format = None
                fext = ext
                if ext is None:
                    fext = ''
                filename = os.path.join(dirname,
                                        key.replace('/', '_') + fext)
                if verbose:
                    print('saving:', filename, '(', key, ')')
                self.build_texture(mesh, key)
                if ext in ('.gltf', '.glb'):
                    gltf = self.store_gltf_texmesh(mesh, key, gltf)
                elif ext is not None:
                    aims.write(mesh, filename, format=format)
                summary.setdefault("meshes", {})[filename] = key

        # if gltf and lights
        if mesh_format in ('.gltf', '.glb'):
            if lights is not None:
                ext = gltf.setdefault('extensions', {})
                lext = ext.setdefault("KHR_lights_punctual", {})
                gltflights = lext.setdefault('lights', [])
                nodes = gltf.setdefault('nodes', [])
                scnodes = gltf.setdefault('scenes',
                                          [{'nodes': []}])[0]['nodes']
                nn = len(scnodes)
                nl = 0
                # print('LIGHTS:', lights)
                for light in lights:
                    pos = light[0][:3]
                    props = light[0][4]
                    if props is None:
                        props = {}
                    gltflights.append(props)
                    scnodes.append(nn)
                    node = {
                        "extensions": {
                            "KHR_lights_punctual": {
                                "light": nl
                            }
                        },
                        "translation": [-pos[0], pos[1], pos[2]],
                    }
                    direction = props.get('direction')
                    if direction is not None:
                        del props['direction']
                        direction = aims.Point3df(direction)
                        direction.normalize()
                        direction[0] *= -1  # we have inverted x
                        axis = aims.vectProduct([0, 0, -1], direction)
                        angle = math.asin(axis.norm())
                        rotation = aims.Quaternion()
                        rotation.fromAxis(axis, angle)
                        node['rotation'] = list(rotation.vector())
                    nodes.append(node)
                    nn += 1
                    nl += 1
        return summary

    def store_gltf_texmesh(self, mesh, name, gltf):
        from soma.aims import gltf_io
        if 'texture' in mesh.header():
            # print('MESH WITH TEXTURE', name)
            texture = mesh.header()['texture']
            tcoords = texture['coords']
            gltf = gltf_io.tex_mesh_to_gltf(
                mesh, tcoords, name=name, gltf=gltf,
                tex_format='webp', images_as_buffers=True,
                single_buffer=True)
        else:
            gltf = gltf_io.mesh_to_gltf(mesh, name=name, gltf=gltf)
        return gltf

    def find_element(self, xml_et, filters):
        filt_layer = None
        if isinstance(filters, str):
            filters = {'id': filters}
        else:
            if 'layer' in filters:
                filt_layer = filters['layer']
                filters = dict(filters)
                del filters['layer']

        doc = xml_et.getroot()
        todo = [(layer, None) for layer in doc
                if filt_layer is None
                    or layer.get(
                        '{http://www.inkscape.org/namespaces/inkscape}label')
                            == filt_layer]
        while todo:
            elem, strans = todo.pop(0)
            trans = self.get_transform(elem, strans)
            match = 0
            for k, v in filters.items():
                ev = elem.get(k)
                if v != ev:
                    break
                match += 1
            if match == len(filters):
                return elem, trans
            todo += [(child, trans) for child in elem]
        return None

    def get_metadata(self, xml_et):
        meta = getattr(self, 'svg_metadata', None)
        if meta is not None:
            return meta
        meta = [layer for layer in xml_et.getroot()
                if layer.tag.endswith('}metadata')]
        if len(meta) != 0:
            meta = meta[0]
        else:
            meta = {}
        self.svg_metadata = meta
        return meta

    def clip_rect_from_id(self, xml_et, rect_id):
        if isinstance(rect_id, str):
            elem = self.find_element(xml_et, rect_id)
            if not elem:
                raise ValueError('element not found: %s' % rect_id)
            elem, trans = elem
            # un-apply element transform
            telem = elem.get('transform')
            if telem:
                telem = self.get_transform(telem)
                if trans is not None:
                    trans = trans * scipy.linalg.inv(telem)
                else:
                    trans = scipy.linalg.inv(telem)
            # print('elem:', elem)
            # print(elem.items())
            bbox = self.boundingbox(elem, trans)
            dims = [bbox[0][0],
                    bbox[0][1],
                    bbox[1][0] - bbox[0][0],
                    bbox[1][1] - bbox[0][1]]
        else:
            dims = rect_id

        return dims

    def clip_page(self, xml_et, dims_or_rect):
        dims = self.clip_rect_from_id(xml_et, dims_or_rect)
        doc = xml_et.getroot()
        init_w = self.measure_with_unit(doc.get('width'))
        init_vbox = [float(x) for x in doc.get('viewBox').split()[2:]]
        ratio = init_w / init_vbox[0]
        doc.set('width', str(dims[2] * ratio))
        doc.set('height', str(dims[3] * ratio))
        doc.set('viewBox', '0 0 %f %f' % (dims[2], dims[3]))
        transl = 'translate(%f, %f)' % (-dims[0], -dims[1])
        for layer in doc:
            if layer.tag.endswith('}g'):
                ltrans = layer.get('transform')
                if ltrans:
                    ltrans = '%s %s' % (transl, ltrans)
                else:
                    ltrans = transl
                layer.set('transform', ltrans)

    def read_xml(self, svg_filename):
        self.svg_filename = svg_filename
        self.svg = ET.parse(svg_filename)
        return self.svg


if __name__ == '__main__':

    filenames = [
        '/volatile/riviere/neurosvn/capsul/trunk/doc/source/_static/capsul_logo.svg',
        '/home/riviere/neurosvn/capsul/trunk/doc/source/_static/capsul_logo.svg',
        '/tmp/galeries_big.svg',
        '/home/riviere/catacombes/plans/14/big_2017/GRS-2010-galeries.svg',
        '/home/riviere/catacombes/plans/14/big_2017/PARIS-2017.svg',
    ]
    svg_filename = filenames[-1]
    if not os.path.exists(svg_filename):
        svg_filename = [f for f in filenames if os.path.exists(f)][0]

    svg_mesh = SvgToMesh('bygroup')

    xml_et = svg_mesh.read_xml(svg_filename)

    mesh = svg_mesh.read_paths(xml_et)
