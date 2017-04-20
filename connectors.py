import _winreg
import platform
import subprocess
import errno
import socket
import logging
import json
import os
import rpyc
from time import sleep


class GrasshopperToPythonRemote:
    def __init__(self, rpyc_server_py, python_exe=None, env_name=None, timeout=60, max_retry=3):
        if python_exe is None:
            self.python_exe = self._get_python_path(env_name)
        else:
            if env_name is not None:
                logging.debug('python_exe and env_name specified at the same time, ignoring env_name.')
            self.python_exe = python_exe
        self.rpyc_server_py = rpyc_server_py  # TODO: Build one if not passed in
        self.timeout = timeout
        self.retry = 0
        self.max_retry = max(0, max_retry)
        self.python_popen = self._launch_python()
        self.connection = self._get_connection()
        self.py_remote_modules = self.connection.root.getmodule

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the connection on error and exit.

        Parameters
        ----------
        exc_type : Error
            Type of the exception that caused the __exit__.
        exc_val : str
            Value of the exception that caused the __exit__.
        exc_tb : type
            Exception log.

        Returns
        -------
        True if the connection was successfully closed."""
        try:
            if exc_type:
                logging.error("{!s}, {!s}, {!s}".format(exc_type, exc_val, exc_tb))
        except NameError:
            pass
        self.close()
        return True

    def run_py_function(self, module_name, function_name, *nargs, **kwargs):
        """Run a specific Python function on the remote, with Python crash handling."""
        remote_module = self.py_remote_modules(module_name)
        function = getattr(remote_module, function_name)
        function_output = kwargs.pop("function_output", None)

        try:
            result = function(*nargs, **kwargs)
        except (socket.error, EOFError):
            self._rebuild_py_remote()
            return self.run_py_function(*nargs, **kwargs)

        if function_output is not None:
            try:
                result = result[function_output]
            except NameError:
                pass
        return result

    def close(self):
        if not self.connection.closed:
            logging.info('Closing connection.')
            self.connection.close()
        if self.python_popen.poll() is None:
            logging.info('Closing Python.')
            self.python_popen.terminate()

    @staticmethod
    def _get_python_path(env_name=None):
        if env_name is not None:
            try:
                envs = json.loads(subprocess.check_output(["conda", "env", "list", "--json"]))['envs']
            except OSError:
                logging.warning('conda not found in your windows $PATH$, cannot fetch environment by name.\n'
                                'Falling back to getting python path from windows $PATH$.')
                return GrasshopperToPythonRemote._get_python_path()
            env_dir = [path for path in envs if os.path.split(path)[-1] == env_name]
            if len(env_dir) > 1:
                logging.warning('Found several environments with target name; selecting first one.')

            try:
                python_exe = os.path.join(env_dir[0], 'python.exe')
            except IndexError:
                logging.warning('Environment {!s} was not found in your conda list of environments.\n'.format(env_name)
                                + 'Falling back to getting python path from windows $PATH$.')
                return GrasshopperToPythonRemote._get_python_path()

            if os.path.isfile(python_exe) and os.access(python_exe, os.X_OK):
                logging.debug('Using python executable: {!s}'.format(python_exe))
                return python_exe
            else:
                logging.warning('No python executable found in environment directory {!s}.\n'.format(env_dir)
                                + 'Falling back to getting python path from windows $PATH$.')
                return GrasshopperToPythonRemote._get_python_path()
        else:
            try:
                python_exe = subprocess.check_output(["where", "python"]).split('\n')[0].strip()
                logging.debug('Using python executable: {!s}'.format(python_exe))
                return python_exe
            except (OSError, subprocess.CalledProcessError) as e:
                logging.error("Unable to find a python installation in your windows $PATH$."
                              "Are you running Windows with python accessible in your path?")
                raise e

    def _launch_python(self):
        python_call = '"{!s}" "{!s}"'.format(self.python_exe, self.rpyc_server_py)
        python_popen = subprocess.Popen(python_call, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        return python_popen

    def _get_connection(self):
        connection = None
        logging.info("Connecting...")
        for i in range(self.timeout):
            try:
                if not connection:
                    logging.debug("Connecting. Timeout in {:d} seconds.".format(self.timeout - i))
                    connection = rpyc.classic.connect('localhost', 18872)  # TODO: use nameserver to avoid relying on available ports
                else:
                    logging.debug("Found connection, testing. Timeout in {:d} seconds.".format(self.timeout - i))
                    connection.ping(timeout=1)
                    logging.debug("Connection ok, returning.")
                    logging.info("Connected.")
                    return connection
            except (socket.error, rpyc.core.protocol.PingError, rpyc.core.async.AsyncResultTimeout) as e:
                if e is socket.error and not e.errno == errno.ECONNREFUSED:
                    raise
                if i == self.timeout - 1:
                    raise
                elif e is socket.error:
                    sleep(1)

    def _rebuild_py_remote(self):
        if self.retry < self.max_retry:
            logging.info("Lost Rhino connection, retrying.")
            self.retry += 1
            self.close()
            [self.rhino_popen, self.connection, self.gh_remote] = [None, None, None]
            logging.info("Waiting 10 seconds.")
            sleep(10)
            self.python_popen = self._launch_python()
            self.connection = self._get_connection()
        else:
            logging.error(
                "Lost Rhino connection, and attempts limit ({:d}) reached. Exiting.".format(self.max_retry))
            raise



class PythonToGrasshopperRemote:
    """Creates a remote Rhino/IronPython instance (with Grasshopper functions) connected to a local python engine.
    
    The local instance will be able to import all objects from the Rhino IronPython engine, as well as Grasshopper
    components. Rhino will appear frozen on a python script it is reading.
        
    Parameters
    ----------
    rhino_file_path : str
        Absolute file path to a Rhino .3dm file to open in the remote Rhino. Can be empty.
    rpyc_server_py : str
        Absolute path to the ghcompservice.py module that launches the server on the remote.
    rhino_exe : str
        Absolute path to the Rhino executable. By default, fetches from the windows registry the
        Rhino 5.0 install with the same bitness as the platform.
    timeout : int
        Number of seconds to wait for Rhino and IronPython to startup.
    max_retry : int
        Number of times Rhino will be restarted if it crashes, before declaring the connection dead.
    
    Examples
    --------
    >>> ROOT = os.path.abspath(os.path.join(path.curdir, '..'))
    >>> rhino_file_path = os.path.join(ROOT, 'examples', 'curves.3dm')
    >>> rpyc_server_py = os.path.join(ROOT, 'ghcompservice.py')
    >>> with PythonToGrasshopperRemote(rhino_file_path, rpyc_server_py, timeout=60) as py2gh:
    >>>     rghcomp = py2gh.gh_remote_components
    >>>     rgh = py2gh.connection
    >>>     Rhino = rgh.modules.Rhino
    >>>     rs = rgh.modules.rhinoscriptsyntax
    >>>     # Do stuff with all this
    >>>     # See python_to_GH.py for a longer example
    """

    def __init__(self, rhino_file_path, rpyc_server_py, rhino_exe=None, timeout=60, max_retry=3):
        if rhino_exe is None:
            self.rhino_exe = self._get_rhino_path()
        else:
            self.rhino_exe = rhino_exe
        self.rhino_file_path = rhino_file_path
        self.rpyc_server_py = rpyc_server_py  # TODO: Build one if not passed in
        self.timeout = timeout
        self.retry = 0
        self.max_retry = max(0, max_retry)
        self.rhino_popen = self._launch_rhino()
        self.connection = self._get_connection()
        self.gh_remote_components = self.connection.root.get_component  # TODO: improve ghcomp to get clusters the same way we get compiled components, thus removing the need for a custom getter

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Cleanup the connection on error and exit.
        
        Parameters
        ----------
        exc_type : Error
            Type of the exception that caused the __exit__.
        exc_val : str
            Value of the exception that caused the __exit__.
        exc_tb : type
            Exception log.
            
        Returns
        -------
        True if the connection was successfully closed."""
        try:
            if exc_type:
                logging.error("{!s}, {!s}, {!s}".format(exc_type, exc_val, exc_tb))
        except NameError:
            pass
        self.close()
        return True

    def run_gh_component(self, component_name, *nargs, **kwargs):
        """Run a specific Grasshopper component on the remote, with Rhino crash handling."""
        is_cluster = kwargs.pop("is_cluster", False)  # TODO: improve ghcomp to get clusters the same way we get compiled components, thus removing the need for a custom getter
        component = self.gh_remote_components(component_name, is_cluster=is_cluster)
        component_output = kwargs.pop("component_output", None)

        try:
            result = component(*nargs, **kwargs)
        except (socket.error, EOFError):
            self._rebuild_gh_remote()
            return self.run_gh_component(*nargs, **kwargs)

        if component_output is not None:
            try:
                result = result[component_output]
            except NameError:
                pass
        return result

    def close(self):
        if not self.connection.closed:
            logging.info('Closing connection.')
            self.connection.close()
        if self.rhino_popen.poll() is None:
            logging.info('Closing Rhino.')
            self.rhino_popen.terminate()

    @staticmethod
    def _get_rhino_path(version='5.0', preferred_bitness='same'):
        rhino_reg_key_path = None
        if platform.machine().endswith('64'):
            if preferred_bitness == 'same' or preferred_bitness == '64':
                rhino_reg_key_path = r'SOFTWARE\McNeel\Rhinoceros\{}x64\Install'.format(version)
            elif preferred_bitness == '32':
                rhino_reg_key_path = r'SOFTWARE\Wow6432Node\McNeel\Rhinoceros\{}\Install'.format(version)
        elif platform.machine().endswith('32'):
            if preferred_bitness == 'same' or preferred_bitness == '32':
                rhino_reg_key_path = r'SOFTWARE\McNeel\Rhinoceros\{}\Install'.format(version)

        if rhino_reg_key_path is None:
            logging.error(
                "Did not understand Rhino version ({!s}) and bitness ({!s}) options for platform {!s}.".format(
                    version, preferred_bitness, platform.machine()))
        try:
            rhino_reg_key = _winreg.OpenKey(_winreg.HKEY_LOCAL_MACHINE, rhino_reg_key_path)
            rhino_path = _winreg.QueryValueEx(rhino_reg_key, 'Path')[0]
        except OSError as e:
            logging.error(
                "Unable to find Rhino installation in registry. Are you running Windows with Rhinoceros installed?")
            raise e
        return os.path.join(rhino_path, 'Rhino.exe')

    def _launch_rhino(self):
        rhino_call = '"{!s}" /nosplash /notemplate /runscript="-_RunPythonScript ""{!s}"" -_Exit" "{!s}"'.format(
            self.rhino_exe, self.rpyc_server_py, (self.rhino_file_path or ''))
        rhino_popen = subprocess.Popen(rhino_call, stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        return rhino_popen

    def _get_connection(self):
        connection = None
        logging.info("Connecting...")
        for i in range(self.timeout):
            try:
                if not connection:
                    logging.debug("Connecting. Timeout in {:d} seconds.".format(self.timeout - i))
                    connection = rpyc.classic.connect('localhost', 18871)  # TODO: use nameserver to avoid relying on available ports
                else:
                    logging.debug("Found connection, testing. Timeout in {:d} seconds.".format(self.timeout - i))
                    connection.ping(timeout=1)
                    logging.debug("Connection ok, returning.")
                    logging.info("Connected.")
                    return connection
            except (socket.error, rpyc.core.protocol.PingError, rpyc.core.async.AsyncResultTimeout) as e:
                if e is socket.error and not e.errno == errno.ECONNREFUSED:
                    raise
                if i == self.timeout - 1:
                    raise
                elif e is socket.error:
                    sleep(1)

    def _rebuild_gh_remote(self):
        if self.retry < self.max_retry:
            logging.info("Lost Rhino connection, retrying.")
            self.retry += 1
            self.close()
            [self.rhino_popen, self.connection, self.gh_remote] = [None, None, None]
            logging.info("Waiting 10 seconds.")
            sleep(10)
            self.rhino_popen = self._launch_rhino()
            self.connection = self._get_connection()
            self.gh_remote_components = self.connection.root.get_component
        else:
            logging.error(
                "Lost Rhino connection, and attempts limit ({:d}) reached. Exiting.".format(self.max_retry))
            raise
