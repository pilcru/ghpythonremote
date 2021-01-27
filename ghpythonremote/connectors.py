import errno
import logging
import os
import socket
import subprocess
from time import sleep

from ghpythonremote import rpyc
from .helpers import (
    get_python_path,
    get_extended_env_path_conda,
    get_rhino_executable_path,
    WINDOWS,
)

logger = logging.getLogger("ghpythonremote.connectors")


class GrasshopperToPythonRemote:
    def __init__(
        self,
        rpyc_server_py,
        python_exe=None,
        location=None,
        timeout=60,
        max_retry=3,
        port=None,
        log_level=logging.WARNING,
        working_dir=None,
    ):
        if python_exe is None:
            self.python_exe = get_python_path(location)
        else:
            if location is not None:
                logger.debug(
                    "python_exe and env_name specified at the same time, ignoring "
                    "env_name."
                )
            self.python_exe = python_exe
        self.env = get_extended_env_path_conda(self.python_exe)
        self.rpyc_server_py = rpyc_server_py
        self.timeout = timeout
        self.retry = 0
        self.max_retry = max(0, max_retry)
        self.log_level = log_level
        self.working_dir = working_dir
        if port is None:
            self.port = _get_free_tcp_port()
        else:
            self.port = port
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
                logger.error("{!s}, {!s}, {!s}".format(exc_type, exc_val, exc_tb))
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
            logger.info("Closing connection.")
            self.connection.close()
        if self.python_popen.poll() is None:
            logger.info("Closing Python.")
            self.python_popen.terminate()

    def _launch_python(self):
        logger.debug("Using python executable: {!s}".format(self.python_exe))
        logger.debug("Using rpyc_server module: {!s}".format(self.rpyc_server_py))
        logger.debug("Using port: {}".format(self.port))
        logger.debug("Using log_level: {!s}".format(self.log_level))
        logger.debug("Using working_dir: {!s}".format(self.working_dir))
        assert self.python_exe is not "" and self.python_exe is not None
        assert self.rpyc_server_py is not "" and self.rpyc_server_py is not None
        assert self.port is not "" and self.port is not None
        assert self.log_level is not "" and self.log_level is not None
        python_call = [
            self.python_exe,
            self.rpyc_server_py,
            str(self.port),
            self.log_level,
        ]
        cwd = self.working_dir
        python_popen = subprocess.Popen(
            python_call,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            cwd=cwd,
            env=self.env,
        )
        return python_popen

    def _get_connection(self):
        connection = None
        logger.info("Connecting...")
        for i in range(self.timeout):
            try:
                if not connection:
                    logger.debug(
                        "Connecting. Timeout in {:d} seconds.".format(self.timeout - i)
                    )
                    connection = rpyc.utils.factory.connect(
                        "localhost",
                        self.port,
                        service=rpyc.core.service.ClassicService,
                        config={"sync_request_timeout": None},
                        ipv6=False,
                        keepalive=True,
                    )
                else:
                    logger.debug(
                        "Found connection, testing. Timeout in {:d} seconds.".format(
                            self.timeout - i
                        )
                    )
                    connection.ping(timeout=1)
                    logger.debug("Connection ok, returning.")
                    logger.info("Connected.")
                    return connection
            except socket.error as e:
                if self.python_popen.poll() is not None:
                    raise RuntimeError(
                        "Remote python {!s} failed on launch. ".format(self.python_exe)
                        + "Does the remote python have rpyc installed?"
                    )
                if i == self.timeout - 1 or not e.errno == errno.ECONNREFUSED:
                    raise RuntimeError(
                        "Could not connect to remote python {!s}. ".format(
                            self.python_exe
                        )
                        + "Does the remote python have rpyc installed?"
                    )
                sleep(1)
            except (
                rpyc.core.protocol.PingError,
                rpyc.core.async_.AsyncResultTimeout,
            ) as e:
                logger.debug(str(e))
                raise e

    def _rebuild_py_remote(self):
        if self.retry < self.max_retry:
            logger.info("Lost Rhino connection, retrying.")
            self.retry += 1
            self.close()
            [self.rhino_popen, self.connection, self.gh_remote] = [None, None, None]
            logger.info("Waiting 10 seconds.")
            sleep(10)
            self.python_popen = self._launch_python()
            self.connection = self._get_connection()
        else:
            raise RuntimeError(
                "Lost connection to Python, and reconnection attempts limit ({:d}) "
                "reached. Exiting.".format(self.max_retry)
            )


class PythonToGrasshopperRemote:
    """Creates a remote Rhino/IronPython instance (with Grasshopper functions)
    connected to a local python engine.
    
    The local instance will be able to import all objects from the Rhino IronPython
    engine, as well as Grasshopper components. Rhino will appear frozen on a python
    script it is reading.
        
    Parameters
    ----------
    rhino_file_path : str
        Absolute file path to a Rhino .3dm file to open in the remote Rhino. Can be
        empty.
    rpyc_server_py : str
        Absolute path to the ghcompservice.py module that launches the server on the
        remote.
    rhino_ver : int
        A Rhino version to use, from 5 to 7. Overridden by rhino_exe. Defaults to 7.
    rhino_exe : str
        Absolute path to the Rhino executable. By default, fetches from the windows
        registry the Rhino install with the same bitness as the platform, and version
        given by rhino_ver.
    timeout : int
        Number of seconds to wait for Rhino and IronPython to startup.
    max_retry : int
        Number of times Rhino will be restarted if it crashes, before declaring the
        connection dead.
    
    Examples
    --------
    >>> ROOT = os.path.abspath(os.path.join(os.path.curdir, '..'))
    >>> rhino_file_path = os.path.join(ROOT, 'examples', 'curves.3dm')
    >>> rpyc_server_py = os.path.join(ROOT, 'ghcompservice.py')
    >>> with PythonToGrasshopperRemote(
    >>>     rhino_file_path, rpyc_server_py, rhino_ver=7, timeout=60
    >>> ) as py2gh:
    >>>     rghcomp = py2gh.gh_remote_components
    >>>     rgh = py2gh.connection
    >>>     Rhino = rgh.modules.Rhino
    >>>     rs = rgh.modules.rhinoscriptsyntax
    >>>     # Do stuff with all this
    >>>     # See CPython_to_GH.py for a longer example
    """

    def __init__(
        self,
        rhino_file_path,
        rpyc_server_py,
        rhino_ver=7,
        preferred_bitness="same",
        rhino_exe=None,
        timeout=60,
        max_retry=3,
        port=None,
        log_level=logging.WARNING,
    ):
        if rhino_exe is None:
            self.rhino_exe = self._get_rhino_path(
                version=rhino_ver, preferred_bitness=preferred_bitness
            )
        else:
            self.rhino_exe = rhino_exe
        self.rhino_file_path = rhino_file_path
        self.rpyc_server_py = rpyc_server_py
        self.timeout = timeout
        self.retry = 0
        self.max_retry = max(0, max_retry)
        if port is None:
            self.port = _get_free_tcp_port()
        else:
            self.port = port
        self.log_level = log_level
        self.rhino_popen = self._launch_rhino()
        self.connection = self._get_connection()
        self.gh_remote_components = self.connection.root.ghcomp
        self.gh_remote_userobjects = self.connection.root.ghuo

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
                logger.error("{!s}, {!s}, {!s}".format(exc_type, exc_val, exc_tb))
        except NameError:
            pass
        self.close()
        return True

    def run_gh_component(self, component_name, *nargs, **kwargs):
        """Run a specific Grasshopper component on the remote, with Rhino crash
        handling.
        """
        is_cluster = kwargs.pop("is_cluster", False)
        # TODO: improve ghcomp to get clusters the same way we get compiled components,
        # thus removing the need for a custom getter
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
            logger.info("Closing connection.")
            self.connection.close()
        if self.rhino_popen.poll() is None:
            logger.info("Closing Rhino.")
            self.rhino_popen.terminate()

    @staticmethod
    def _get_rhino_path(version, preferred_bitness):
        return get_rhino_executable_path(version, preferred_bitness)

    def _launch_rhino(self):
        assert self.rhino_exe is not "" and self.rhino_exe is not None
        assert self.rpyc_server_py is not "" and self.rpyc_server_py is not None
        assert self.port is not "" and self.port is not None
        if WINDOWS:
            rhino_call = [
                '"' + self.rhino_exe + '"',
                "/nosplash",
                "/notemplate",
                '/runscript="-_RunPythonScript ""{!s}"" {!s} {!s} -_Exit "'.format(
                    self.rpyc_server_py, self.port, self.log_level,
                ),
            ]
        else:
            rhino_call = [
                self.rhino_exe,
                "-nosplash",
                "-notemplate",
                '-runscript=-_RunPythonScript "{!s}" {!s} {!s} -_Exit'.format(
                    self.rpyc_server_py, self.port, self.log_level,
                ),
            ]
        if self.rhino_file_path:
            rhino_call.append(self.rhino_file_path)
        if WINDOWS:
            # Default escaping in subprocess.line2cmd does not work here,
            # manually convert to string
            rhino_call = " ".join(rhino_call)
        rhino_popen = subprocess.Popen(
            rhino_call, stdout=subprocess.PIPE, stdin=subprocess.PIPE
        )
        return rhino_popen

    def _get_connection(self):
        connection = None
        logger.info("Connecting...")
        for i in range(self.timeout):
            try:
                if not connection:
                    logger.debug(
                        "Connecting. Timeout in {:d} seconds.".format(self.timeout - i)
                    )
                    connection = rpyc.utils.factory.connect(
                        "localhost",
                        self.port,
                        service=rpyc.core.service.ClassicService,
                        config={"sync_request_timeout": None},
                        ipv6=False,
                        keepalive=True,
                    )
                else:
                    logger.debug(
                        "Found connection, testing. Timeout in {:d} seconds.".format(
                            self.timeout - i
                        )
                    )
                    connection.ping(timeout=1)
                    logger.debug("Connection ok, returning.")
                    logger.info("Connected.")
                    return connection
            except (
                socket.error,
                rpyc.core.protocol.PingError,
                rpyc.core.async_.AsyncResultTimeout,
            ) as e:
                if e is socket.error and not e.errno == errno.ECONNREFUSED:
                    raise
                if i == self.timeout - 1:
                    raise
                elif e is socket.error or isinstance(e, socket.error):
                    sleep(1)

    def _rebuild_gh_remote(self):
        if self.retry < self.max_retry:
            logger.info("Lost Rhino connection, retrying.")
            self.retry += 1
            self.close()
            [self.rhino_popen, self.connection, self.gh_remote] = [None, None, None]
            logger.info("Waiting 10 seconds.")
            sleep(10)
            self.rhino_popen = self._launch_rhino()
            self.connection = self._get_connection()
            self.gh_remote_components = self.connection.root.get_component
        else:
            raise RuntimeError(
                "Lost connection to Rhino, and reconnection attempts limit ({:d}) "
                "reached. Exiting.".format(self.max_retry)
            )


def _get_free_tcp_port():
    tcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    tcp.bind(("", 0))
    addr, port = tcp.getsockname()
    tcp.close()
    return port
