
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
import six
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
* six
* optionally, soma.aims

  The AIMS library is used to build and manpulate meshes.
  (https://github.com/brainvisa/aims-free)
  This lib is compiled (C++ + python bindings) thus is not completely
  straightforward to install.
  Alternately we can implement basic replacements for vector and mesh classes.
  This allows to use the 2D part.
  The 3D part however needs more algorithmic things in Aims, and Anatomist
  to render depth maps.
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

    class aims(object):
        ''' Fake aims-lite module '''

        class vector(object):
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


        class AimsTimeSurface(object):
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


        class AimsTimeSurface_2(AimsTimeSurface):
            ''' Segments mesh (2 points per polygon) '''

            def __init__(self):
                super(aims.AimsTimeSurface_2, self).__init__(2)


        class AimsTimeSurface_3(AimsTimeSurface):
            ''' Triangles mesh (3 points per polygon) '''

            def __init__(self):
                super(aims.AimsTimeSurface_3, self).__init__(3)


class SvgToMesh(object):
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
        mesh = aims.SurfaceGenerator.circle_wireframe(
            (x, y, 1.), r, npt, (0, 0, 1), (1, 0, 0), angle_s, angle_e)
        pts = trans * np.matrix(mesh.vertex().np.T)
        pts[2, :] = 0  # reset Z to 0
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
        # print('vert:', vert)
        # print('poly:', poly)
        # print('path trans:', trans)
        if not np.all(trans == np.eye(3)):
            # print('trans:', trans)
            vert = np.asarray(vert).T
            vert[2, :] = 1.
            vert = (trans * vert).T
            vert[:, 2] = 0.
            # print('to: vert:', vert)
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
        print('map meth:', tex_def.get('params', {}).get('mapping_method'))
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
        print('geodesic distance map...')
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

    @staticmethod
    def get_transform(trans, previous=None):
        '''
        Parameters
        ----------
        trans: str or XML element
            if str: transform field in the SVG element.
            if element: element itself
        previous: np array or None
            parent transform to be composed with
        '''
        # print('transform:', trans_str)
        if trans is None:
            return np.matrix(np.eye(3))
        mat3d = None
        if not isinstance(trans, str):
            trans3d = trans.get('transform_3d')
            if trans3d is not None:
                mat3d = SvgToMesh.get_transform(trans3d)
            trans_str = trans.get('transform')
            if not trans_str:
                mat = np.matrix(np.eye(3))
                if previous is not None:
                    mat = previous * mat
                    if trans3d is None and hasattr(previous, 'transform_3d'):
                        mat3d = previous.transform_3d
                if mat3d is not None:
                    mat.transform_3d = mat3d
                return mat

        else:
            trans_str = trans

        tr_list = trans_str.split(') ')
        tr_list = [x + ')' for x in tr_list[:-1]] + [tr_list[-1]]
        tmat = previous
        for trans_strx in tr_list:
            mat = np.matrix(np.eye(3))
            i = trans_strx.find('(')
            if not i or trans_strx[-1] != ')':
                print('unrecognized transform: %s', trans_strx)
                return tmat
            ttype = trans_strx[:i]
            tdef1 = trans_strx[i+1:-1].strip().split(',')
            tdef = []
            for t in tdef1:
                tdef += [float(x.strip()) for x in t.strip().split(' ')]
            if ttype == 'matrix':
                mat[:2, 0] = np.reshape(tdef[:2], (2, 1))
                mat[:2, 1] = np.reshape(tdef[2:4], (2, 1))
                mat[:2, 2] = np.reshape(tdef[4:], (2, 1))
            elif ttype == 'translate':
                mat[0, 2] = tdef[0]
                if len(tdef) > 1:
                    mat[1, 2] = tdef[1]
            elif ttype == 'scale':
                mat[0, 0] = tdef[0]
                if len(tdef) > 1:
                    mat[1, 1] = tdef[1]
                else:
                    mat[1, 1] = tdef[0]
            elif ttype == 'rotate':
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
            if ttype == 'matrix4':
                mat = np.matrix(np.eye(4))
                mat[:3, 0] = np.reshape(tdef[:3], (3, 1))
                mat[:3, 1] = np.reshape(tdef[3:6], (3, 1))
                mat[:3, 2] = np.reshape(tdef[6:9], (3, 1))
                mat[:3, 3] = np.reshape(tdef[9:], (3, 1))
            if tmat is None:
                tmat = mat
            else:
                tmat = tmat * mat

        # print('mat:', tmat)
        if mat3d is not None:
            tmat.transform_3d = mat3d
        return tmat

    @staticmethod
    def to_transform(matrix):
        transform = 'matrix(' + ', '.join(
            [str(x) for x in np.asarray(matrix[:2, :].T).ravel()]) + ')'
        return transform

    def boundingbox(self, element, trans=None, exhaustive=True):
        todo = [(element, trans)]
        bbox = [None, None]
        bmin, bmax = bbox
        while todo:
            element, trans = todo.pop(0)
            trans = self.get_transform(element, trans)
            if element.tag.endswith('}g'):
                todo = [(c, trans) for c in element] + todo
            else:
                if element.tag.endswith('}path') \
                        or element.tag.endswith('}rect') \
                        or element.tag.endswith('}image'):
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
                    or child.tag.endswith('}circle'):
                child_mesh = self.read_path(child, trans, style)
                if self.concat_mesh == 'merge':
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
                        print(child.tag)
                        print(list(child.items()))
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
                tgroup = self.main_group
                if not tgroup.endswith('_text'):
                    tgroup += '_text'
                current_text \
                    = self.mesh_dict.setdefault(
                        tgroup, {'object_type': 'List', 'objects': []})
                text = child.text
                if text is not None:
                    text = six.ensure_str(text)
                current_text_o = self.text_description(
                    child, trans, style=style, text=text)
                current_text['objects'].append(current_text_o)
                size = self.text_size(current_text_o)
                current_text_o['properties']['size'] = size
                current_text_o['objects'][0]['properties']['position'] \
                    = [-size[0]/2., size[1]/2., 0]
            elif child.tag.endswith('}tspan') or child.tag == 'tspan':
                text = child.text
                tgroup = self.main_group
                if not tgroup.endswith('_text'):
                    tgroup += '_text'
                current_text_o \
                    = self.mesh_dict[tgroup]['objects'][-1]
                try:
                    current_text_d \
                        = current_text_o['objects'][-1]['properties']
                except Exception:
                    print('error in text item:', file=sys.stderr)
                    print('current_text_o:', repr(current_text_o))
                    # traceback.print_exc()
                    raise
                current_text = current_text_d['text']
                if text is None:
                    print('tspan without text, id:', child.get('id'))
                    text = ''
                else:
                    text = six.ensure_str(child.text)
                if not current_text:
                    current_text = text
                else:
                    current_text += '\n' + text
                current_text_d['text'] = current_text
                size = self.text_size(current_text_o)
                current_text_o['properties']['size'] = size
                current_text_o['objects'][0]['properties']['position'] \
                    = [-size[0]/2., size[1]/2., 0]
            elif self.main_group is None \
                    and (child.tag.endswith('}g') or child.tag == 'g'):
                self.main_group = child.get('id')
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

    def text_description(self, xml_item, trans=None, style=None, text=''):
        props = {
            'object_type': 'TransformedObject',
            'properties': {},
            'objects': [],
        }
        if not xml_item.get('x') or not xml_item.get('y'):
            if len(xml_item[:]) != 0 and xml_item[0].get('x') \
                    and xml_item[0].get('y'):
                # coords on tspan item
                pos = (float(xml_item[0].get('x')),
                       float(xml_item[0].get('y')))
            else:
                print('text without coords, id:', xml_item.get('id'))
                print(xml_item)
                print(xml_item.items())
                pos = (0., 0.)
        else:
            pos = (float(xml_item.get('x')), float(xml_item.get('y')))
        if trans is not None:
            p0 = np.array(((pos[0], pos[1], 1.),)).T
            pos = list(np.array(trans.dot(p0)).ravel()[:2])
        font_size = None
        obj_props = {'text': text, 'position': [0, 0, 0.],
                     'font_size': 10., 'scale': 0.1,
                     'material': {'diffuse': [.5, .5, .5, 1.]}}
        trobj_props = {'position': [pos[0], pos[1], 4.]}
        props['properties'] = trobj_props
        props['objects'].append({
            'object_type': 'TextObject',
            'name': 'Text',
            'properties': obj_props,
        })
        if style is not None:
            text_anchor = style.get('text-anchor')
            if text_anchor is not None:
                obj_props['text-anchor'] = text_anchor
                if text_anchor == 'middle':
                    pass  # TODO
            font_size = style.get('font-size')
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
                if unit in ('', 'pt', 'px'):
                    font_size *= 10. / 3.95  # arbitrary
                obj_props['font_size'] = font_size
            font_family = style.get('font-family')
            if font_family is not None:
                obj_props['font_family'] = font_family
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
        return props

    @staticmethod
    def text_size(text_item):
        if not text_item:
            return [0, 0]
        text_obj = text_item['objects'][0]['properties']
        scale = text_obj.get('scale', 1.) * text_obj.get('font_size', 10.)
        text = text_obj.get('text')
        if not text:
            return [0, 0]
        text = six.ensure_text(text).split('\n')
        # assume fixed size font, with height/width ratio of 3.3.
        # also assume a final scale factor of 2.12 (old: 0.0827)
        # this is arbitrary but I don't know how to do better
        scale *= 2.12  # 0.0827
        hw_ratio = 2.5
        height = len(text) * scale
        width = max([len(line) for line in text]) * scale / hw_ratio
        return [width, height]

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

    #def clip_path(self, xml_path, trans, bmin, bmax):
        #def read_point(pdesc, i, pt=None):
            #j = i + 1
            #try:
                #while j < n and pdesc[j] in '0123456789.e-':
                    #j += 1
                #x = float(pdesc[i:j])
                #i = j + 1
                #while i<len(pdesc) and pdesc[i] in ' ,':
                    #i += 1
            #except Exception as e:
                #print(e)
                #print('failed reading', pt, ', i:', i)
                #raise
            #return x, i

        #pdesc = xml_path.get('d')
        #n = len(pdesc)
        #i = 0
        #cmd = 'M'
        #x = 0
        #y = 0
        #tp = [0, 0]
        #first = x, y, tp
        #out_cmd = []
        #clip = None
        #points_kept = 0
        #cond_cmd = []
        #valid = False

        #while i < n:
            #while(i < n and pdesc[i] == ' '):
                #i += 1
            #if i == n:
                ##print('end of path in:', pdesc)
                #break
            ##print('i:', i)
            #last_x, last_y = x, y
            #last_valid = valid
            #last_tp = tp
            #if pdesc[i] in 'mMcClLhHvVsSqQtTaA':
                #cmd = pdesc[i]
                #clip = 0
                #cond_cmd.append(cmd)
                #np = 0
                ##print('cmd:', cmd)
                #i += 1
                #while pdesc[i] == ' ':
                    #i += 1
            #elif pdesc[i] in '-0123456789.':
                #if cmd not in 'vV':
                    #x, i = read_point(pdesc, i, 'x')
                    #cond_cmd.append(x)
                    #if cmd >= 'a':
                        #x += last_x
                #if cmd not in 'hH':
                    #y, i = read_point(pdesc, i, 'y')
                    #cond_cmd.append(y)
                    #j = i + 1
                    #if cmd >= 'a':
                        #y += last_y
                #tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                #np += 1
                #if tp[0] < bmin[0] or tp[0] > bmax[0] \
                        #or tp[1] < bmin[1] or tp[1] > bmax[1]:
                    #clip += 1
                    #valid = False
                #else:
                    #valid = True
                #if cmd in 'cC':
                    ##last_x, last_y = x, y
                    #x, i = read_point(pdesc, i, 'x2')
                    #y, i = read_point(pdesc, i, 'y2')
                    #cond_cmd.append(x)
                    #cond_cmd.append(y)
                    #if cmd >= 'a':
                        #x += last_x
                        #y += last_y
                    #tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                    ##last_x, last_y = x, y
                    #x, i = read_point(pdesc, i, 'x3')
                    #y, i = read_point(pdesc, i, 'y3')
                    #cond_cmd.append(x)
                    #cond_cmd.append(y)
                    #if cmd >= 'a':
                        #x += last_x
                        #y += last_y
                    #tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                #elif cmd in 'sSqQ':
                    ##last_x, last_y = x, y
                    #x, i = read_point(pdesc, i, 'x2')
                    #y, i = read_point(pdesc, i, 'y2')
                    #cond_cmd.append(x)
                    #cond_cmd.append(y)
                    #if cmd >= 'a':
                        #x += last_x
                        #y += last_y
                    #tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                #if cmd in 'aA':
                    #x, i = read_point(pdesc, i, 'x-axis-rotation')
                    #y, i = read_point(pdesc, i, 'large-arc-flag')
                    #s, i = read_point(pdesc, i, 'sweep-flag')
                    #cond_cmd += [x, int(y), int(s)]
                    #x, i = read_point(pdesc, i, 'x2')
                    #y, i = read_point(pdesc, i, 'y2')
                    #cond_cmd += [x, y]
                    #if cmd >= 'a':
                        #x += last_x
                        #y += last_y
                    #tp = np.asarray(trans.dot([[x], [y], [1.]])).ravel()
                #if cmd in 'cCsSqQaA':
                    #np += 1
                    #if tp[0] < bmin[0] or tp[0] > bmax[0] \
                            #or tp[1] < bmin[1] or tp[1] > bmax[1]:
                        #clip += 1
                        #valid2 = False
                    #else:
                        #valid2 = True
                    #if not valid and not valid2:
                        ## invalid segment: keep last as potential Move
                        #if cmd >= 'a':
                            #cond_cmd = ['m', x, y]
                        #else:
                            #cond_cmd = ['M', x, y]
                #if cmd == 'm':
                    #cmd = 'l'
                    #first = x, y, tp
                #elif cmd == 'M':
                    #cmd = 'L'
                    #first = x, y, tp
            #elif pdesc[i] in 'zZ':
                #if valid:
                    #out_cmd.append(pdesc[i])
                    #cond_cmd = []
                #else:
                    #cond_cmd = [pdesc[i], x, y]
                #x, y, tp = first
                #i += 1
            #else:
                #out_cmd.append(pdesc[i])
                #i += 1

        #return ' '.join([str(x) for x in out_cmd])

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
                       mesh_wf_format='.obj', lights=None):
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
                print('saving:', filename, '(', key, ')')
                try:
                    json.dump(mesh, open(filename, 'w'))
                    summary.setdefault('text_fnames', {})[filename] = key
                except Exception as e:
                    print(e)
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
                print('LIGHTS:', lights)
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
            print('MESH WITH TEXTURE', name)
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

    @staticmethod
    def get_metadata(xml_et):
        meta = [layer for layer in xml_et.getroot()
                if layer.tag.endswith('}metadata')]
        if len(meta) != 0:
            meta = meta[0]
        else:
            meta = {}
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
            print('elem:', elem)
            print(elem.items())
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
        init_w = float(doc.get('width'))
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
