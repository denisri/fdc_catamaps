# -*- coding: utf-8 -*-

version_major = 2
version_minor = 0
version_micro = 0
version_extra = ''

# Format expected by setup.py and doc/source/conf.py: string of form "X.Y.Z"
__version__ = "%s.%s.%s%s" % (version_major,
                              version_minor,
                              version_micro,
                              version_extra)
CLASSIFIERS = ['Development Status :: 5 - Production/Stable',
               'Environment :: Console',
               'Environment :: X11 Applications',
               'Intended Audience :: Developers',
               'Operating System :: OS Independent',
               'Programming Language :: Python',
               'Topic :: Utilities',]


description = '2D/3D Catacombs maps from Inkscape SVG maps'

long_description = """
============
FDC Catamaps
============

2D/3D Catacombs maps from Inkscape SVG maps
"""

# versions for dependencies
SPHINX_MIN_VERSION = '1.0'

# Main setup parameters
NAME = 'fdc_catamaps'
PROJECT = 'soma'
ORGANISATION = "denisri"
MAINTAINER = "denisri"
MAINTAINER_EMAIL = ""
DESCRIPTION = description
LONG_DESCRIPTION = long_description
URL = "https://github.com/denisri/fdc_catamaps"
DOWNLOAD_URL = "https://github.com/denisri/fdc_catamaps"
LICENSE = "CeCILL-B"
CLASSIFIERS = CLASSIFIERS
AUTHOR = "someone"
AUTHOR_EMAIL = "none"
PLATFORMS = "OS Independent"
PROVIDES = ["fdc_catamaps"]
REQUIRES = [
    "argparse",
    "numpy",
    "scipy",
    "Pillow"
]
EXTRA_REQUIRES = {
    "doc": ["sphinx>=" + SPHINX_MIN_VERSION]}

brainvisa_build_model = 'pure_python'

