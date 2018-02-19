import sys
import os
import pip
import logging
from shutil import copy, rmtree
from .helpers import get_rhino_ironpython_path

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

if __name__ == '__main__':
    location = None
    if len(sys.argv) > 1:
        location = sys.argv[1]

    rhino_ironpython_path = get_rhino_ironpython_path(location=location)

    # Install the package to Rhino IronPython Users lib
    package_name = 'gh-python-remote'
    pip_cmd = ['install', '--upgrade', '--target=' + rhino_ironpython_path,
               '--no-binary=:all:', '--no-compile', '--ignore-requires-python',
               '--process-dependency-links',
               package_name, ]
    print('\n\nThis will install ghpythonremote in Rhino IronPython with the command:')
    print('pip ' + ' '.join(pip_cmd))
    pip.main(pip_cmd)

    # Get the Grasshopper libraries base dir
    gh_userobjects_path = os.path.join(os.getenv('APPDATA', ''), 'Grasshopper', 'UserObjects')
    if os.path.isdir(gh_userobjects_path):
        dest_dir_path = os.path.join(gh_userobjects_path, package_name)
    else:
        logging.warning('Could not find Grasshopper "UserObjects" special folder; '
                        + 'example files will be installed to deafult temp dir.')
        dest_dir_path = os.path.join(os.getenv('TEMP', 'C:\\'), package_name)
    # Get the filepath in the installed package
    source_dir_path = os.path.dirname(os.path.realpath(__file__))
    # Send the files there
    if os.path.isdir(dest_dir_path):
        rmtree(dest_dir_path)
    os.mkdir(dest_dir_path)
    copy_pairs = [
        ('examples', [
            'examples/curves.3dm',
            'examples/GH_python_remote.ghx',
            'examples/GH_to_python.py',
            'examples/python_to_GH.py',
        ]),
        ('', [
            'ghcluster/GHPythonRemote.ghuser',
        ])
    ]
    for copy_pair in copy_pairs:
        dest = os.path.join(dest_dir_path, copy_pair[0])
        if not os.path.isdir(dest):
            os.mkdir(dest)
        for file_rel_path in copy_pair[1]:
            source = os.path.join(source_dir_path, *file_rel_path.split('/'))
            copy(source, dest)
    logging.info('Copied example files to {!s}'.format(dest_dir_path))