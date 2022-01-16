#!/usr/bin/env python3

from wheel.bdist_wheel import bdist_wheel as bdist_wheel_
from setuptools import setup, Extension, Command
from distutils.util import get_platform

import glob
import sys
import os

directory = os.path.dirname(os.path.realpath(__file__))


setup(
    name="scicall",
    packages=["scicall"],
    version="0.1.0",
    license="MIT",
    description="TODO",
    author="netricks",
    author_email="mirmikns@yandex.ru",
    url="https://github.com/mirmik/scilab-caller",
    long_description=open(os.path.join(
        directory, "README.md"), "r", encoding="utf8").read(),
    long_description_content_type="text/markdown",
    keywords=["testing"],
    classifiers=[],
    package_data={
        "scicall": [
        ]
    },
    include_package_data=True,
    install_requires=[
        'PyQt5',
        'PyQt5-sip',
    ],
    entry_points={"console_scripts": [
        "scicall=scicall.__main__:main"
    ]},
)
