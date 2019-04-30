#!/usr/bin/env python3
from setuptools import setup, find_packages
from os import path

here = path.abspath(path.dirname(__file__))
version = '1.0'

long_des = ""
with open(path.join(here, 'README.md')) as f:
    long_des = f.read()

setup(
    name='SlippiPy',
    description="unofficial python client for slippi mirroring",
    long_description=long_des,
    long_description_content_type="text/markdown",
    url="https://github.com/Savestate2A03/slippi-python-client",
    author="Savestate2A03",
    author_email="savestate",
    license="GNU Public License v3.0",
    keywords='smash melee slippi',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Programming Language :: Python :: 3.7',
        'Operating System :: OS Independent',
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Natural Language :: English",
    ],
    python_requires='~=3.7',
    version=version,
    packages=find_packages(),
    install_requires=[
        'pypubsub'
    ],
)
