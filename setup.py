# To use a consistent encoding
from codecs import open
from os import path
from setuptools import setup, find_packages
import sys

if sys.version_info[0] > 2:
    sys.exit("Incompatible with Python 3. IronPython 2.7 from Rhino can only be "
             "connected to a Python 2 instance.")

here = path.abspath(path.dirname(__file__))

# Default version
__version__ = '0.1.0'
# Get __version__, __version_info__
execfile(path.join(here, 'ghpythonremote', 'version.py'))

# Get the long description from the README file
with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()
# Append the CHANGELOG to it
with open(path.join(here, 'CHANGELOG.rst'), encoding='utf-8') as f:
    long_description += '\n\n====\n\n' + f.read()

setup(
    name='gh-python-remote',
    description=('GH Python Remote is a package to get Rhinoceros3D/Grasshopper and '
                 + 'Python to collaborate better: connect an external python instance'
                 + ' to Grasshopper, and vice-versa.'),
    long_description=long_description,
    long_description_content_type='text/x-rst',
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
            'examples/CPython_to_GH.py',
            'examples/TestClusterGHPythonRemote.ghuser',
            'ghcluster/GHPythonRemote.ghuser',
        ],
    },
    data_files=[
    ],
    install_requires=[
        'plumbum==1.7.2'
        'rpyc==4.1.5'
    ],
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },
)
