from setuptools import setup, find_packages
import libgreader

setup(
    name             = 'libgreader',
    version          = libgreader.__version__,
    description      = 'Library for working with the Google Reader API',
    long_description = open('README.md').read() + '\n\n' + open('HISTORY.md').read(),

    author           = libgreader.__author__,
    author_email     = 'askedrelic@gmail.com',
    url              = 'https://github.com/askedrelic/libgreader',
    license          = open("LICENSE.txt").read(),

    packages         = find_packages(),
    test_suite       = 'tests',
    # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
    #classifiers  = ['Development Status :: 3 - Alpha', ],
)
