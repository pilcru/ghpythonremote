import _winreg
import platform
import subprocess
import errno
import socket
import logging
import psutil
from os import path
from time import sleep

import rpyc
from rpyc.utils.server import OneShotServer


logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)


class NumpyService(rpyc.Service):
    def on_connect(self):
        print('Incoming connection.')
        import numpy as np
        self.np = np

    def on_disconnect(self):
        print('Disconnected.')

    def exposed_get_module(self, module_name, is_cluster=False):
        module = getattr(self.np, module_name)
        if is_cluster:
            module = getattr(module, module_name)
        return module


class GrasshopperToPythonRemote:
    def __init__(self):
        print('Starting server')
        cpu_count = psutil.cpucount()
        threads = max(cpu_count - 1, 1)
        server = OneShotServer(Pythonservice, hostname='localhost', ipv6=False, port=12345, listener_timeout=None)
        server.start()

    def _get_python_path(path=None):
        if path is None:
            try:
                return subprocess.check_output(["where", "python"]).split('\n')[0].strip()
            except (OSError, subprocess.CalledProcessError) as e:
                logging.error(
                    "Unable to find a python installation. Are you running Windows with python accessible in your path?")
                raise e
        else:
            return path


class PythonToGrasshopperRemote:
    def __init__(self, rhino_file_path, rpyc_server_py, rhino_exe=None, timeout=60, max_retry=3):
        if rhino_exe is None:
            self.rhino_exe = self._get_rhino_path()
        else:
            self.rhino_exe = rhino_exe
        self.rhino_file_path = rhino_file_path
        self.rpyc_server_py = rpyc_server_py
        self.timeout = timeout
        self.retry = 0
        self.max_retry = max(0, max_retry)
        self.rhino_popen = self._launch_rhino()
        self.connection = self._get_connection()
        self.gh_remote_components = self.connection.root.get_component

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            if exc_type:
                logging.error("{!s}, {!s}, {!s}".format(exc_type, exc_val, exc_tb))
        except NameError:
            pass
        self.close()
        return True

    def run_remote(self, *nargs, **kwargs):
        component_output = kwargs.pop("component_output", None)
        try:
            result = self.gh_remote(*nargs, **kwargs)
        except (socket.error, EOFError):
            self._rebuild_gh_remote()
            return self.run_remote(*nargs, **kwargs)
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
        return path.join(rhino_path, 'Rhino.exe')

    def _launch_rhino(self):
        rhino_call = '{!s} /nosplash /notemplate /runscript="-_RunPythonScript ""{!s}"" -_Exit" "{!s}"'.format(
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
            [self.rhino_popen, self.connection, self.gh_remote_components] = self._make_gh_remote()
        else:
            logging.error(
                "Lost Rhino connection, and attempts limit ({:d}) reached. Exiting.".format(self.max_retry))
            raise
