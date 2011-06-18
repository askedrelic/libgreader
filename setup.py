from setuptools import setup, find_packages
import libgreader

setup(
name         = 'libgreader',
version      = libgreader.__version__,
author       = libgreader.__author__,
author_email = 'askedrelic@gmail.com',

description      = 'Library for working with the Google Reader API',
long_description = open('README.markdown').read(),

url          = 'https://github.com/askedrelic/libgreader',
# Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
#classifiers  = ['Development Status :: 3 - Alpha', ],

packages     = find_packages(),
test_suite   = 'tests',
)
