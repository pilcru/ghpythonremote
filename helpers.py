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
