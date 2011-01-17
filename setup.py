#!/usr/bin/env python

from setuptools import setup, find_packages

setup(name='libgreader',
      version = '0.6dev',
      author='askedrelic',
      author_email='askedrelic@gmail.com',
      test_suite = 'libgreader.tests',
      packages = find_packages(),
)
