#!/usr/bin/python3
# Setup script to install this package.
# M.Blakeney, Mar 2018.

import stat
from pathlib import Path
from setuptools import setup

name = 'pacpush'
module = name.replace('-', '_')
here = Path(__file__).resolve().parent
executable = stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH

setup(
    name=name,
    version='0',
    description='Utility to push an Arch host\'s package and AUR '
    'caches to other hosts',
    long_description=here.joinpath('README.md').read_text(),
    url=f'https://github.com/bulletmark/{name}',
    author='Mark Blakeney',
    author_email='mark@irsaere.net',
    classifiers=[
        'License :: OSI Approved :: GPL-3.0',
        'Programming Language :: Python :: 3',
    ],
    keywords='pacman',
    py_modules=[module],
    python_requires='>=3.6',
    install_requires=['requests', 'ruamel.yaml'],
    data_files=[
        ('share/{}'.format(name), ['README.md', '{}.conf'.format(name)]),
    ],
    scripts=[f.name for f in here.iterdir() if f.name.startswith(name)
        and f.is_file() and f.stat().st_mode & executable],
)
