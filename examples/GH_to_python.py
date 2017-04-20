# TODO: Check if this work without installing IronPython on computer.
import logging
import inspect
# TODO: Automatically add this to the path for gh python
import ghpythonremote
from ghpythonremote.connectors import GrasshopperToPythonRemote
from os import path

logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)

if __name__ == '__main__':
    # TODO: Make an example where the python remote is not killed every time we finish calling it:
    # TODO: Could we attach it to the gh.sticky dict to be able to call it from all of gh?
    ROOT = path.abspath(path.dirname(inspect.getfile(ghpythonremote)))
    rpyc_server_py = path.join(ROOT, 'pythonservice.py')  # TODO: build this file on the fly

    with GrasshopperToPythonRemote(rpyc_server_py, env_name='py27', timeout=60) as gh2py:
        # Stuff that we can reach
        rpymod = gh2py.py_remote_modules  # A getter function for a named python module
        rgh = gh2py.connection  # Represents the remote instance root object
        np = rgh.modules.numpy  # rgh.modules.something is like ``import something`` on the remote

        # Do some stuff
        a = np.arange(15).reshape(3, 5)
        print(a)
