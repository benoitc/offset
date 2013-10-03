import os
import sys

from setuptools import setup, find_packages, Extension
from setuptools.command.test import test as TestCommand

class PyTest(TestCommand):
    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        errno = pytest.main(self.test_args)
        sys.exit(errno)


is_pypy = '__pypy__' in sys.builtin_module_names
py_version = sys.version_info[:2]

if py_version < (2, 7):
    raise RuntimeError('On Python 2, offset requires Python 2.7 or better')



REQUIREMENTS = ["cffi", "wrapt", "fibers"]

if py_version == (2, 7):
    REQUIREMENTS.append('futures')

import imp

def load_module(name, path):
    f, pathname, description = imp.find_module(name, [path])
    return imp.load_module(name, f, pathname, description)


try:
    atomic = load_module('atomic', './offset/sync')
except ImportError:
    EXT_MODULES=[]
else:
    EXT_MODULES=[atomic.ffi.verifier.get_extension()]

CLASSIFIERS = [
    'Development Status :: 4 - Beta',
    'Environment :: Web Environment',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Programming Language :: Python :: 2',
    'Programming Language :: Python :: 2.7',
    'Programming Language :: Python :: 3',
    'Programming Language :: Python :: 3.0',
    'Programming Language :: Python :: 3.1',
    'Programming Language :: Python :: 3.2',
    'Programming Language :: Python :: 3.3',
    'Topic :: Software Development :: Libraries']


# read long description
with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as f:
    long_description = f.read()

DATA_FILES = [
        ('offset', ["LICENSE", "MANIFEST.in", "NOTICE", "README.rst",
                        "THANKS"])
        ]

VERSION = load_module('version', './offset').__version__

setup(name='offset',
        version=VERSION,
        description = 'collection of modules to build distributed and reliable concurrent systems',
        long_description = long_description,
        classifiers = CLASSIFIERS,
        license = 'BSD',
        url = 'http://github.com/benoitc/offset',
        author = 'Benoit Chesneau',
        author_email = 'benoitc@e-engura.org',
        packages=find_packages(),
        install_requires = REQUIREMENTS,
        setup_requires=REQUIREMENTS,
        tests_require=['pytest'],
        ext_modules=EXT_MODULES,
        data_files = DATA_FILES,
        cmdclass={"test": PyTest})
