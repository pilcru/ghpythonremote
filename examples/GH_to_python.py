import sys
import scriptcontext
import logging
import inspect
import ghpythonremote
from ghpythonremote.connectors import GrasshopperToPythonRemote
from os import path
from time import sleep

local_log_level = getattr(logging, log_level, logging.WARNING)
logger = logging.getLogger('ghpythonremote')
logger.setLevel(local_log_level)
ch = logging.StreamHandler()
ch.setLevel(local_log_level)
formatter = logging.Formatter('%(levelname)s: %(name)s:\n%(message)s')
ch.setFormatter(formatter)
logger.handlers = []
logger.addHandler(ch)
logger = logging.getLogger('ghpythonremote.GH_to_python_sticky')

ROOT = path.abspath(path.dirname(inspect.getfile(ghpythonremote)))
rpyc_server_py = path.join(ROOT, 'pythonservice.py')

# Set connection to CLOSED if this is the first run
# and initialize set of linked modules
try:
    remote_python_status
except NameError:
    remote_python_status = 'CLOSED'
    lkd_modules = set()

# Wait for connection to connect or terminate
timer = 0
while remote_python_status == 'CONNECTING' or remote_python_status == 'CLOSING':
    sleep(1)
    timer += 1
    if timer == 10:
        try:
            gh2py_manager.__exit__(*sys.exc_info())
        except Exception:
            pass
        remote_python_status = 'CLOSED'
        lkd_modules = set()
        raise RuntimeError("Connection left in an inconsistent state and not returning. Reset everything.")

if run:
    if not remote_python_status == 'OPEN':
        remote_python_status = 'CONNECTING'
        gh2py_manager = GrasshopperToPythonRemote(rpyc_server_py, location=location, timeout=10,
                                                  port=None, log_level=log_level, working_dir=working_dir)
        gh2py = gh2py_manager.__enter__()
        remote_python_status = 'OPEN'

    # Stuff that we can reach
    rpymod = gh2py.py_remote_modules  # A getter function for a named python module
    rpy = gh2py.connection  # Represents the remote instance root object
    # Add modules
    for mod in modules:
        try:
            scriptcontext.sticky[mod] = rpymod(mod)
            lkd_modules.add(mod)
        except ImportError:
            gh2py_manager.__exit__(*sys.exc_info())
            raise

elif not remote_python_status == 'CLOSED':
    remote_python_status = 'CLOSING'
    # Remove linked modules
    for mod in lkd_modules:
        del scriptcontext.sticky[mod]
    gh2py_manager.__exit__(*sys.exc_info())
    lkd_modules = set()
    remote_python_status = 'CLOSED'

# Change variable name because ghpython resets outputs to None before each run
linked_modules = lkd_modules

logger.info('GH to python connection is {}'.format(remote_python_status))
