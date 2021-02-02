import json
import logging
import os
import platform
import subprocess


logger = logging.getLogger("ghpythonremote.helpers")


RUNNING_IN_RHINO5 = False
try:
    from Rhino.RhinoApp import ExeVersion

    if ExeVersion == 5:
        RUNNING_IN_RHINO5 = True
except ImportError:
    pass

WINDOWS = False
MACOS = False
# "cli" is for IronPython in Rhino 5
if platform.system() == "Windows" or (RUNNING_IN_RHINO5 and platform.system() == "cli"):
    WINDOWS = True
if platform.system() == "Darwin":
    MACOS = True
if platform.system() == "Linux" or not (WINDOWS or MACOS):
    logger.error("Unknown platform {!s}".format(platform.system()))
    raise RuntimeError("This package only runs on Windows and MacOS")

if WINDOWS:
    try:
        import _winreg as winreg
    except ImportError:
        import winreg

DEFAULT_RHINO_VERSION = 7


# IronPython is being picky about check_output in Mono, because some arguments are not supported. Base functionallity works:
def _mono_check_output(*popenargs, **kwargs):
    if "stdout" in kwargs:
        raise ValueError("stdout argument not allowed, it will be overridden.")
    process = subprocess.Popen(stdout=subprocess.PIPE, *popenargs, **kwargs)
    output, unused_err = process.communicate()
    retcode = process.poll()
    if retcode:
        cmd = kwargs.get("args")
        if cmd is None:
            cmd = popenargs[0]
        raise subprocess.CalledProcessError(retcode, cmd, output=output)
    return output


def get_python_path(location=None):
    if location is None or location == "":
        if WINDOWS:
            return get_python_from_windows_path()
        else:
            return get_python_from_macos_path()

    if os.path.exists(location):
        logger.debug(" Directly trying python executable at {!s}\n".format(location))
        return get_python_from_path(location)

    try:
        [method, env_name] = location.split("://")
    except ValueError as e:
        if WINDOWS:
            logger.warning(
                "Location format for {!s} did not match expected format: "
                '"method://env_name"({!s}).\n'.format(location, e)
                + "Falling back to getting python path from Windows %PATH%.\n"
            )
            return get_python_from_windows_path()
        else:
            logger.warning(
                "Location format for {!s} did not match expected format: "
                '"method://env_name"({!s}).\n'.format(location, e)
                + "Falling back to getting python path from MacOS $PATH.\n"
            )
            return get_python_from_macos_path()
    if method == "conda":
        return get_python_from_conda_env(env_name)

    if WINDOWS:
        logger.warning(
            "Method {!s} for location not implemented.\n".format(method)
            + "Falling back to getting python path from Windows %PATH%.\n"
        )
        return get_python_from_windows_path()
    else:
        logger.warning(
            "Method {!s} for location not implemented.\n".format(method)
            + "Falling back to getting python path from MacOS $PATH.\n"
        )
        return get_python_from_macos_path()


def get_python_from_path(path):
    path = os.path.normpath(os.path.realpath(path))
    if os.path.isdir(path):
        if WINDOWS:
            path = os.path.join(path, "python.exe")
        else:
            path = os.path.join(path, "python")
    if os.path.isfile(path) and os.access(path, os.X_OK):
        return path
    else:
        if WINDOWS:
            logger.warning(
                "Path {!s} is not executable.\n".format(path)
                + "Falling back to getting python path from Windows %PATH%.\n"
            )
            return get_python_from_windows_path()
        else:
            logger.warning(
                "Path {!s} is not executable.\n".format(path)
                + "Falling back to getting python path from MacOS $PATH.\n"
            )
            return get_python_from_macos_path()


def get_python_from_windows_path():
    try:
        python_exe = subprocess.check_output(["where", "python"]).split("\n")[0].strip()
        return python_exe
    except (OSError, subprocess.CalledProcessError) as e:
        logger.error(
            "Unable to find a python installation in your Windows %PATH%. "
            + "Are you running Windows with python accessible in your path?\n"
        )
        raise e


def get_python_from_macos_path():
    try:
        python_exe = _mono_check_output(["which", "python"]).split("\n")[0].strip()
        return python_exe
    except (OSError, subprocess.CalledProcessError) as e:
        logger.error(
            "Unable to find a python installation in your MacOS $PATH. "
            + "Are you running MacOS with python accessible in your path?\n"
        )
        raise e


def get_python_from_conda_env(env_name):
    if MACOS:
        # Need to find the conda exec from the .zshrc file
        try:
            output = _mono_check_output(
                "source ~/.zshrc; env", shell=True, executable="/bin/zsh"
            )
            new_vars_list = [line.partition("=")[::2] for line in output.split("\n")]
            new_vars_dict = {name: value for (name, value) in new_vars_list}
            conda_exe_path = new_vars_dict.get("CONDA_EXE", None)
        except (OSError, subprocess.CalledProcessError):
            logger.warning(
                "Could not source ~/.zshrc file when looking for $CONDA_EXE. Continuing."
            )
        if conda_exe_path is None or not (
            os.path.isfile(conda_exe_path) and os.access(conda_exe_path, os.X_OK)
        ):
            logger.warning("Could not find $CONDA_EXE in ~/.zshrc. Continuing.")
            conda_exe_path = "conda"

    try:
        if WINDOWS:
            envs = json.loads(
                subprocess.check_output(["conda", "env", "list", "--json"])
            )["envs"]
        else:
            envs = json.loads(
                _mono_check_output([conda_exe_path, "env", "list", "--json"])
            )["envs"]
    except OSError:
        if WINDOWS:
            logger.warning(
                "conda not found in your Windows %PATH%, cannot fetch environment by "
                + "name.\nFalling back to getting python path from Windows %PATH%.\n"
            )
            return get_python_from_windows_path()
        else:
            logger.warning(
                "conda not found in your MacOS $PATH or ~/.zshrc, cannot fetch environment by "
                + "name.\nFalling back to getting python path from MacOS $PATH.\n"
            )
            return get_python_from_macos_path()
    except subprocess.CalledProcessError:
        if WINDOWS:
            logger.warning(
                "conda env list failed, cannot fetch environment by name.\n"
                + "Falling back to getting python path from Windows %PATH%.\n"
            )
            return get_python_from_windows_path()
        else:
            logger.warning(
                "conda env list failed, cannot fetch environment by name.\n"
                + "Falling back to getting python path from MacOS $PATH.\n"
            )
            return get_python_from_macos_path()

    env_dir = [path for path in envs if os.path.split(path)[-1] == env_name]
    if len(env_dir) > 1:
        logger.warning(
            "Found several environments with target name; selecting first one."
        )

    try:
        if WINDOWS:
            python_exe = os.path.join(env_dir[0], "python.exe")
        else:
            python_exe = os.path.join(env_dir[0], "bin", "python")
        if os.path.isfile(python_exe) and os.access(python_exe, os.X_OK):
            return python_exe
        else:
            if WINDOWS:
                logger.warning(
                    "Path {!s} is not executable.\n".format(python_exe)
                    + "Falling back to getting python path from Windows %PATH%.\n"
                )
                return get_python_from_windows_path()
            else:
                logger.warning(
                    "Path {!s} is not executable.\n".format(python_exe)
                    + "Falling back to getting python path from MacOS $PATH.\n"
                )
                return get_python_from_macos_path()
    except IndexError:
        if WINDOWS:
            logger.warning(
                "Environment {!s} was not found in your conda list of "
                "environments.\n".format(env_name)
                + "Falling back to getting python path from Windows %PATH%.\n"
            )
            return get_python_from_windows_path()
        else:
            logger.warning(
                "Environment {!s} was not found in your conda list of "
                "environments.\n".format(env_name)
                + "Falling back to getting python path from MacOS $PATH.\n"
            )
            return get_python_from_macos_path()


def get_extended_env_path_conda(python_exe):
    # Conda stores useful DLLs in these paths, add them to the path like they would be
    # by conda activate
    new_env = os.environ.copy()
    if WINDOWS:
        conda_folders = [
            "",
            "/Library/mingw-w64/bin",
            "/Library/usr/bin",
            "/Library/bin",
            "/Scripts",
            "/bin",
        ]
    else:
        conda_folders = [
            "",
            "/bin",
        ]

    add_path = [
        os.path.normpath(os.path.dirname(python_exe) + folder)
        for folder in conda_folders
    ]
    new_env["PATH"] = os.pathsep.join(add_path) + os.pathsep + new_env["PATH"]
    return new_env


def get_rhino_ironpython_path(location=None):
    if location is None or location == "":
        if WINDOWS:
            return get_ironpython_from_windows_appdata()
        else:
            return get_ironpython_from_macos_appsupport()

    if type(location) == int:
        logger.debug(
            " Looking for IronPython installation of Rhino version {!s}.\n".format(
                location
            )
        )
        if WINDOWS:
            return get_ironpython_from_windows_appdata(location)
        else:
            return get_ironpython_from_macos_appsupport(location)

    if os.path.isdir(location):
        logger.debug(" Directly using IronPython lib folder at {!s}\n".format(location))
        return get_ironpython_from_path(location)

    if WINDOWS:
        logger.warning(
            " Path {!s} is not a directory or does not exist.\n".format(location)
            + " " * 9
            + "Falling back to getting IronPython lib folder path from Windows %APPDATA%.\n"
        )
        return get_ironpython_from_windows_appdata()
    else:
        logger.warning(
            " Path {!s} is not a directory or does not exist.\n".format(location)
            + " " * 9
            + "Falling back to getting IronPython lib folder path from MacOS ~/Library folder.\n"
        )
        return get_ironpython_from_macos_appsupport()


def get_ironpython_from_windows_appdata(rhino_version=DEFAULT_RHINO_VERSION):
    appdata_path = os.getenv("APPDATA", "")
    if rhino_version == 7:
        ironpython_settings_path = os.path.join(
            appdata_path,
            "McNeel",
            "Rhinoceros",
            "7.0",
            "Plug-ins",
            "IronPython (814d908a-e25c-493d-97e9-ee3861957f49)",
            "settings",
        )
    elif rhino_version == 6:
        ironpython_settings_path = os.path.join(
            appdata_path,
            "McNeel",
            "Rhinoceros",
            "6.0",
            "Plug-ins",
            "IronPython (814d908a-e25c-493d-97e9-ee3861957f49)",
            "settings",
        )
    elif rhino_version == 5:
        ironpython_settings_path = os.path.join(
            appdata_path,
            "McNeel",
            "Rhinoceros",
            "5.0",
            "Plug-ins",
            "IronPython (814d908a-e25c-493d-97e9-ee3861957f49)",
            "settings",
        )
    else:
        logger.warning(
            ' Unknown Rhino version "{!s}". Defaulting to Rhino {!s}.\n'.format(
                rhino_version, DEFAULT_RHINO_VERSION
            )
        )
        return get_ironpython_from_windows_appdata()
    return check_windows_ironpython_installation(
        ironpython_settings_path, rhino_version
    )


def get_ironpython_from_macos_appsupport(rhino_version=DEFAULT_RHINO_VERSION):
    appsupport_path = os.path.abspath(
        os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    )
    if rhino_version == 7:
        ironpython_path = os.path.join(
            appsupport_path,
            "McNeel",
            "Rhinoceros",
            "7.0",
            "Plug-Ins",
            "IronPython (814d908a-e25c-493d-97e9-ee3861957f49)",
            "settings",
        )
    elif rhino_version == 6:
        ironpython_path = os.path.join(
            appsupport_path,
            "McNeel",
            "Rhinoceros",
            "6.0",
            "Plug-ins",
            "IronPython (814d908a-e25c-493d-97e9-ee3861957f49)",
            "settings",
        )
    else:
        logger.warning(
            ' Unknown Rhino version "{!s}". Defaulting to Rhino {!s}.\n'.format(
                rhino_version, DEFAULT_RHINO_VERSION
            )
        )
        return get_ironpython_from_macos_appsupport()
    return check_macos_ironpython_installation(ironpython_path, rhino_version)


def check_windows_ironpython_installation(ironpython_settings_path, rhino_version):
    if rhino_version == 5:
        ghpython_version_path = os.path.join(
            ironpython_settings_path, "ghpy_version.txt"
        )

        if os.path.isfile(ghpython_version_path):
            with open(ghpython_version_path) as ghpython_version:
                ghpython_version_list = ghpython_version.readline().split(".")
            try:
                ghpython_version_tuple = tuple(int(x) for x in ghpython_version_list)
                if ghpython_version_tuple < (0, 6, 0, 3):
                    logger.warning(
                        " ghpy_version.txt indicates obsolete version {!s}.\n".format(
                            ".".join(ghpython_version_list)
                        )
                        + " " * 9
                        + "Please install version 0.6.0.3 or superior from "
                        + "http://www.food4rhino.com/app/ghpython\n"
                    )
                logger.info(
                    " Found ghpython version {!s} in {!s}\n".format(
                        ".".join(ghpython_version_list), ironpython_settings_path
                    )
                )
            except ValueError:
                logger.warning(
                    " Could not parse ghpy_version.txt file installation found in "
                    "{!s}.\n".format(ironpython_settings_path)
                    + " " * 9
                    + "Was ghpython installed and opened in Grasshopper at least once "
                    + "on this machine?\n"
                )
        else:
            logger.warning(
                " No ghpy_version.txt file installation found in {!s}.\n".format(
                    ironpython_settings_path
                )
                + " " * 9
                + "Was ghpython installed and opened in Grasshopper at least once on "
                + "this machine?\n"
            )
    if rhino_version >= 6:
        # Rhino 6, 7 do not have a ghpy_version.txt file, check that there is a
        # ghpythonlib __init__.py
        ghpythonlib_init_path = os.path.join(
            ironpython_settings_path, "lib", "ghpythonlib", "__init__.py"
        )

        if not os.path.isfile(ghpythonlib_init_path):
            logger.warning(
                " No ghpythonlib package found in {!s}.\n".format(
                    os.path.join(ironpython_settings_path, "lib")
                )
                + " " * 9
                + "Was Grasshopper for Rhino {!s} opened at least once on this machine?\n".format(
                    rhino_version
                )
            )

    ironpython_lib_path = os.path.join(ironpython_settings_path, "lib")
    if not os.path.isdir(ironpython_lib_path):
        logger.error(
            " IronPython lib directory for Rhinoceros not found in {!s}.\n".format(
                ironpython_settings_path
            )
            + " " * 7
            + "Please provide a full path to one of the folders in your IronPython for "
            + "Rhinoceros path.\n"
            + " " * 7
            + "These folders are listed in the settings of the window opened with the "
            + "command `_EditPythonScript` in Rhinoceros.\n"
        )
        raise RuntimeError(
            "No IronPython lib folder found in %APPDATA%\\McNeel\\Rhinoceros"
        )
    logger.info(" Found IronPython lib folder {!s}\n".format(ironpython_lib_path))

    return ironpython_lib_path


def check_macos_ironpython_installation(ironpython_path, rhino_version):
    if rhino_version == 5:
        if MACOS:
            logger.error("This package is not compatible with Rhinoceros 5 on MacOS")
    if rhino_version >= 6:
        # On MacOS, ghpythonlib is installed for all users in /Applications
        # Just check that the ghpythonlib folder is here and install in scripts
        ghpythonlib_path = os.path.join(ironpython_path, "lib", "ghpythonlib")

        if not os.path.isdir(ghpythonlib_path):
            logger.warning(
                " No ghpythonlib folder found in {!s}.\n".format(
                    os.path.join(ironpython_path, "lib")
                )
                + " " * 9
                + "Was Grasshopper for Rhino {!s} opened at least once on this machine?\n".format(
                    rhino_version
                )
            )

    rhino_scripts_path = os.path.abspath(
        os.path.join(ironpython_path, "..", "..", "..", "scripts")
    )
    if not os.path.isdir(rhino_scripts_path):
        logger.error(
            " scripts directory for Rhinoceros not found in {!s}.\n".format(
                os.path.abspath(os.path.join(ironpython_path, "..", "..", ".."))
            )
            + " " * 7
            + "Please provide a full path to one of the folders in your IronPython for "
            + "Rhinoceros path.\n"
            + " " * 7
            + "These folders are listed in the settings of the window opened with the "
            + "command `_EditPythonScript` in Rhinoceros.\n"
        )
        raise RuntimeError(
            "No scripts folder found in ~/Library/Application Support/McNeel/Rhinoceros/{!s}.0".format(
                rhino_version
            )
        )
    logger.info(" Found scripts folder {!s}\n".format(rhino_scripts_path))

    return rhino_scripts_path


def get_ironpython_from_path(location):
    return location


def get_gh_userobjects_path(location=None):
    if location is None or location == "":
        if WINDOWS:
            return get_userobjects_from_windows_appdata()
        else:
            return get_userobjects_from_macos_appsupport()

    if type(location) == int:
        logger.debug(
            " Looking for Grasshopper UserObjects folder of Rhino version {!s}.\n".format(
                location
            )
        )
        if WINDOWS:
            return get_userobjects_from_windows_appdata(location)
        else:
            return get_userobjects_from_macos_appsupport(location)

    if os.path.isdir(location):
        logger.debug(
            " Directly using Grasshopper UserObjects folder at {!s}\n".format(location)
        )
        return get_userobjects_from_path(location)

    if WINDOWS:
        logger.warning(
            " Path {!s} is not a directory or does not exist.\n".format(location)
            + " " * 9
            + "Falling back to getting Grasshopper UserObjects folder path from Windows %APPDATA%.\n"
        )
        return get_userobjects_from_windows_appdata()
    else:
        logger.warning(
            " Path {!s} is not a directory or does not exist.\n".format(location)
            + " " * 9
            + "Falling back to getting Grasshopper UserObjects folder path from MacOS ~/Library folder.\n"
        )
        return get_userobjects_from_macos_appsupport()


def get_userobjects_from_windows_appdata(rhino_version=None):
    if rhino_version is not None:
        logger.warning(
            " Discarding Rhino version {!s} -- on Windows, this package is always installed to the global UserObjects folder.".format(
                rhino_version
            )
        )
    return os.path.join(os.getenv("APPDATA", ""), "Grasshopper", "UserObjects")


def get_userobjects_from_macos_appsupport(rhino_version=DEFAULT_RHINO_VERSION):
    appsupport_path = os.path.abspath(
        os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    )
    if rhino_version == 7:
        return os.path.join(
            appsupport_path,
            "McNeel",
            "Rhinoceros",
            "7.0",
            "Plug-ins",
            "Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)",
            "UserObjects",
        )
    elif rhino_version == 6:
        return os.path.join(
            appsupport_path,
            "McNeel",
            "Rhinoceros",
            "6.0",
            "Plug-ins",
            "Grasshopper (b45a29b1-4343-4035-989e-044e8580d9cf)",
            "UserObjects",
        )
    else:
        logger.warning(
            "Unknown Rhino version {!s}. Installing to default, version {!s}."
        ).format(rhino_version, DEFAULT_RHINO_VERSION)
        return get_userobjects_from_macos_appsupport()


def get_userobjects_from_path(location):
    return location


def get_rhino_executable_path(version=DEFAULT_RHINO_VERSION, preferred_bitness="same"):
    if WINDOWS:
        return get_rhino_windows_path(version, preferred_bitness)
    else:
        return get_rhino_macos_path(version, preferred_bitness)


def get_rhino_windows_path(version, preferred_bitness):
    rhino_reg_key_path = None
    version_str = "{!s}.0".format(version)
    if platform.architecture()[0] == "64bit":
        if preferred_bitness == "same" or preferred_bitness == "64":
            if version == 5:
                version_str += "x64"
            rhino_reg_key_path = r"SOFTWARE\McNeel\Rhinoceros\{}\Install".format(
                version_str
            )
            if version < 5:
                rhino_reg_key_path = None
        elif preferred_bitness == "32":
            rhino_reg_key_path = r"SOFTWARE\WOW6432Node\McNeel\Rhinoceros\{}\Install"
            rhino_reg_key_path = rhino_reg_key_path.format(version_str)
    elif platform.architecture()[0] == "32bit":
        if preferred_bitness == "same" or preferred_bitness == "32":
            rhino_reg_key_path = r"SOFTWARE\McNeel\Rhinoceros\{}\Install".format(
                version_str
            )
        if version > 5:
            rhino_reg_key_path = None

    if rhino_reg_key_path is None:
        logger.error(
            "Did not understand Rhino version ({!s}) and bitness ({!s}) options "
            "for platform {!s}.".format(version, preferred_bitness, platform.machine())
        )

    # In Python 3, OpenKey might throw a FileNotFoundError, which is not defined in
    # Python 2. Just pretend to work around that
    try:
        FileNotFoundError
    except NameError:
        FileNotFoundError = IOError
    try:
        rhino_reg_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, rhino_reg_key_path)
        rhino_path = winreg.QueryValueEx(rhino_reg_key, "Path")[0]
    except (FileNotFoundError, OSError) as e:
        logger.error(
            "Unable to find Rhino installation in registry. Are you running "
            "Windows with Rhinoceros installed?"
        )
        raise e
    return os.path.join(rhino_path, "Rhino.exe")


def get_rhino_macos_path(version, preferred_bitness):
    if version == 7:
        return os.path.join(
            "/Applications", "Rhino 7.app", "Contents", "MacOS", "Rhinoceros"
        )
    elif version == 6:
        return os.path.join(
            "/Applications", "Rhinoceros.app", "Contents", "MacOS", "Rhinoceros"
        )
    else:
        logger.error("Unknown Rhino version {!s}.".format(version))
        raise (RuntimeError("Unknown Rhino version"))

