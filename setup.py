#!/usr/bin/env python
# -*- coding: utf-8 -*-

import codecs
import os

from setuptools import setup


def read(fname):
    file_path = os.path.join(os.path.dirname(__file__), fname)
    return codecs.open(file_path, encoding="utf-8").read()


setup(
    name="pytest-sphinx",
    version="0.3",
    author="Thomas Hisch",
    author_email="t.hisch@gmail.com",
    maintainer="Thomas Hisch",
    maintainer_email="t.hisch@gmail.com",
    license="BSD-3",
    url="https://github.com/thisch/pytest-sphinx",
    description=(
        "Doctest plugin for pytest with support for "
        "Sphinx-specific doctest-directives"
    ),
    long_description=read("README.rst"),
    py_modules=["pytest_sphinx"],
    install_requires=['enum34;python_version<"3.4"', "pytest>=3.1.1"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Framework :: Pytest",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Operating System :: OS Independent",
        "License :: OSI Approved :: BSD License",
    ],
    entry_points={"pytest11": ["sphinx = pytest_sphinx"]},
)
