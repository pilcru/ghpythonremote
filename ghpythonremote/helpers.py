import os
import logging
import subprocess
import json

logger = logging.getLogger('ghpythonremote.helpers')


def get_python_path(location=None):
    if location is None or location == '':
        return get_python_from_windows_path()

    if os.path.exists(location):
        logger.debug('Directly trying python executable at {!s}'.format(location))
        return get_python_from_path(location)

    try:
        [method, env_name] = location.split('://')
    except ValueError as e:
        logger.warning(
            'Location format for {!s} did not match expected format: "method://env_name"({!s}).\n'.format(
                location, e.message
            )
            + 'Falling back to getting python path from windows %PATH%.'
        )
        return get_python_from_windows_path()
    if method == 'conda':
        return get_python_from_conda_env(env_name)

    logger.warning('Method {!s} for location not implemented.\n'.format(method)
                   + 'Falling back to getting python path from windows %PATH%.')
    return get_python_from_windows_path()


def get_python_from_path(path):
    if os.path.isdir(path):
        path = os.path.join(path, 'python.exe')
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    else:
        logger.warning('Path {!s} is not executable.\n'.format(path))
        return get_python_from_windows_path()


def get_python_from_windows_path():
    try:
        python_exe = subprocess.check_output(["where", "python"]).split('\n')[0].strip()
        return python_exe
    except (OSError, subprocess.CalledProcessError) as e:
        logger.error("Unable to find a python installation in your windows %PATH%."
                     "Are you running Windows with python accessible in your path?")
        raise e


def get_python_from_conda_env(env_name):
    try:
        envs = json.loads(subprocess.check_output(["conda", "env", "list", "--json"]))['envs']
    except OSError:
        logger.warning('conda not found in your windows %PATH%, cannot fetch environment by name.\n'
                       'Falling back to getting python path from windows %PATH%.')
        return get_python_path()

    env_dir = [path for path in envs if os.path.split(path)[-1] == env_name]
    if len(env_dir) > 1:
        logger.warning('Found several environments with target name; selecting first one.')

    try:
        python_exe = os.path.join(env_dir[0], 'python.exe')
        return python_exe
    except IndexError:
        logger.warning('Environment {!s} was not found in your conda list of environments.\n'.format(env_name)
                       + 'Falling back to getting python path from windows %PATH%.')
        return get_python_from_windows_path()


def get_rhino_ironpython_path(location=None):
    if location is None or location == '':
        return get_ironpython_from_appdata()

    if os.path.isdir(location):
        logger.debug('Directly using IronPython lib folder at {!s}'.format(location))
        return get_ironpython_from_path(location)

    logger.warning('Path {!s} is not a directory or does not exist.\n'.format(location)
                   + 'Falling back to getting IronPython lib folder path from windows %APPDATA%.')
    return get_ironpython_from_appdata()


def get_ironpython_from_appdata():
    appdata_path = os.getenv('APPDATA', '')
    ironpython_settings_path = os.path.join(appdata_path, 'McNeel', 'Rhinoceros', '5.0', 'Plug-ins',
                                            'IronPython (814d908a-e25c-493d-97e9-ee3861957f49)', 'settings')
    ghpython_version_path = os.path.join(ironpython_settings_path, 'ghpy_version.txt')
    ironpython_lib_path = os.path.join(ironpython_settings_path, 'lib')

    if os.path.isfile(ghpython_version_path):
        with open(ghpython_version_path) as ghpython_version:
            ghpython_version_list = ghpython_version.readline().split('.')
        try:
            ghpython_version_tuple = tuple(int(x) for x in ghpython_version_list)
            if ghpython_version_tuple < (0, 6, 0, 3):
                logger.warning(
                    'ghpy_version.txt indicates obsolete version {!s}.\n'.format('.'.join(ghpython_version_list))
                    + 'Please install version 0.6.0.3 or superior from http://www.food4rhino.com/app/ghpython')
            logger.info('Found ghpython version {!s} in {!s}'.format('.'.join(ghpython_version_list),
                                                                     ironpython_settings_path))
        except ValueError:
            logger.warning(
                'Could not parse ghpy_version.txt file installation found in {!s}.\n'.format(ironpython_settings_path)
                + 'Was ghpython installed and opened in Grasshopper at least once on this machine?'
            )
    else:
        logger.warning('No ghpy_version.txt file installation found in {!s}.\n'.format(ironpython_settings_path)
                       + 'Was ghpython installed and opened in Grasshopper at least once on this machine?')

    if not os.path.isdir(ironpython_lib_path):
        logger.error('IronPython lib directory for Rhinoceros not found in {!s}.\n'.format(ironpython_settings_path)
                     + 'Please provide a full path to one of the folders in your IronPython for Rhinoceros path.\n'
                     + 'These folders are listed in the settings of the window opened with the command '
                     + '`_EditPythonScript` in Rhinoceros')
        raise RuntimeError('No IronPython lib folder found in %APPDATA%')
    logger.info('Found IronPython lib folder {!s}'.format(ironpython_lib_path))

    return ironpython_lib_path


def get_ironpython_from_path(location):
    logger.debug('Using IronPython lib folder provided {!s}'.format(location))
    return location