import sys
import logging
import inspect
import ghpythonremote
from ghpythonremote.connectors import GrasshopperToPythonRemote
from os import path

# Fakes the GH_to_pytohn script for testing outside of GH

# Define the variables normally created in GH
location = "conda://rhinoremote"
run = True
modules = ["numpy", "scipy", "matplotlib", "matplotlib.pyplot", "cv2"]
log_level = "DEBUG"
working_dir = r"C:\Users\pierre\Pierre\CODE\ghpythonremote\ghpythonremote\examples"
# Replace sticky dict
sticky = {}


local_log_level = getattr(logging, log_level, logging.WARNING)
logger = logging.getLogger('ghpythonremote')
logger.setLevel(local_log_level)
ch = logging.StreamHandler()
ch.setLevel(local_log_level)
formatter = logging.Formatter('%(levelname)s: %(name)s:\n%(message)s')
ch.setFormatter(formatter)
logger.handlers = []
logger.addHandler(ch)
logger = logging.getLogger('ghpythonremote.GH_to_Python')

ROOT = path.abspath(path.dirname(inspect.getfile(ghpythonremote)))
rpyc_server_py = path.join(ROOT, 'pythonservice.py')

remote_python_status = 'CLOSED'
lkd_modules = set()

gh2py_manager = GrasshopperToPythonRemote(rpyc_server_py, location=location, timeout=10,
                                          port=None, log_level=log_level, working_dir=working_dir)
gh2py = gh2py_manager.__enter__()

# Stuff that we can reach
rpymod = gh2py.py_remote_modules  # A getter function for a named python module
rpy = gh2py.connection  # Represents the remote instance root object
# Add modules
for mod in modules:
    try:
        sticky[mod] = rpymod(mod)
        lkd_modules.add(mod)
    except ImportError:
        gh2py_manager.__exit__(*sys.exc_info())
        raise

# Change variable name because ghpython resets outputs to None before each run
linked_modules = lkd_modules

logger.info('GH to python connection is {}'.format(remote_python_status))
