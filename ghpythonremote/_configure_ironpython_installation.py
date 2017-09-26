import sys
import pip
import logging
from .helpers import get_rhino_ironpython_path

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.INFO)

if __name__ == '__main__':
    location = None
    if len(sys.argv) > 1:
        location = sys.argv[1]
    rhino_ironpython_path = get_rhino_ironpython_path(location=location)
    package_name = __package__.split('.')[0]
    pip_cmd = ['install', '--upgrade', '--target="' + rhino_ironpython_path + '"',
               '--no-binary=:all:', '--no-compile', '--ignore-requires-python',
               package_name, ]
    print('\n\nThis will install ghpythonremote in Rhino IronPython with the command:')
    print('pip ' + ' '.join(pip_cmd))
    pip.main(pip_cmd)
