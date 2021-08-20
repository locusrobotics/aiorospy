#!/usr/bin/env python

from setuptools import setup
from catkin_pkg.python_setup import generate_distutils_setup
import sys

if sys.version_info < (3,5):
    sys.exit('Sorry, Python < 3.5 is not supported')

setup_args = generate_distutils_setup(
    packages=[
        'aiorospy'
    ],
    package_dir={'': 'src'},
    python_requires='>3.5.0')

setup(**setup_args)
