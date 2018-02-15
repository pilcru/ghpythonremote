from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path
import sys

if sys.version_info[0] > 2:
    sys.exit("Incompatible with Python 3. IronPython 2.7 from Rhino can only be connected to a Python 2 instance.")

here = path.abspath(path.dirname(__file__))

# Default version
__version__ = '0.1.0'
# Get __version__, __version_info__
execfile(path.join(here, 'ghpythonremote', 'version.py'))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup(
    name='gh-python-remote',
    description=('GH Python Remote is a package to get Rhinoceros3D/Grasshopper and Python to collaborate better: '
                 + 'connect an external python instance to Grasshopper, and vice-versa.'),
    long_description=long_description,
    version=__version__,

    author='Pierre Cuvilliers',
    author_email='pcuvil@mit.edu',
    url='https://github.com/Digital-Structures/ghpythonremote',

    license='MIT',

    classifiers=[
        'Development Status :: 5 - Production/Stable',

        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Software Development :: Interpreters',
        'Topic :: Scientific/Engineering',

        'License :: OSI Approved :: MIT License',

        'Programming Language :: Python :: 2 :: Only',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: IronPython',
    ],
    keywords='CAD design engineering scientific numpy scipy IronPython Rhinoceros3D',

    python_requires='>=2.6,<3',
    platforms=["Windows", ],
    zip_safe=False,

    use_2to3=False,

    packages=find_packages(),
    package_data={
        'ghpythonremote': [
            'examples/curves.3dm',
            'examples/GH_python_remote.ghx',
            'examples/GH_python_remote_plt_example.ghx',
            'examples/GH_to_python.py',
            'examples/python_to_GH.py',
            'ghcluster/GHPythonRemote.ghuser',
        ],
    },
    data_files=[
    ],

    install_requires=['git+git://github.com/tomerfiliba/rpyc.git@e97f860c3af1b8950a691665af02447e6faf3b70#egg=rpyc', ],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
)
