#!/usr/bin/python
# Setup script to install this package.
# M.Blakeney, Mar 2018.

from pathlib import Path
from setuptools import setup

here = Path(__file__).resolve().parent
readme = here.joinpath('README.md').read_text()
name = str(here.name)

setup(
    name=name,
    version='0',
    description='Utility to push an Arch host\'s package and AUR '
    'caches to other hosts',
    long_description=readme,
    url=f'https://github.com/bulletmark/{name}',
    author='Mark Blakeney',
    author_email='mark@irsaere.net',
    classifiers=[
        'License :: OSI Approved :: GPL-3.0',
        'Programming Language :: Python :: 3',
    ],
    keywords='pacman',
    py_modules=[name],
    install_requires=['requests', 'ruamel.yaml'],
    data_files=[
        (f'share/doc/{name}', ['README.md']),
        (f'/etc', [f'{name}.conf']),
    ],
    scripts=[name],
)
