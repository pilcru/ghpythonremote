import inspect
import logging
from os import path

import ghpythonremote
from ghpythonremote.connectors import PythonToGrasshopperRemote

local_log_level = logging.DEBUG
logger = logging.getLogger("ghpythonremote")
logger.setLevel(local_log_level)
ch = logging.StreamHandler()
ch.setLevel(local_log_level)
formatter = logging.Formatter("%(levelname)s: %(name)s:\n%(message)s")
ch.setFormatter(formatter)
logger.handlers = []
logger.addHandler(ch)
logger = logging.getLogger("ghpythonremote.Python_to_GH")

ROOT = path.abspath(path.dirname(inspect.getfile(ghpythonremote)))
rpyc_server_py = path.join(ROOT, "pythonservice.py")


# TODO: This could be made a console script in setup.py, with some additional config
if __name__ == "__main__":
    ROOT = path.abspath(path.dirname(inspect.getfile(ghpythonremote)))
    rhino_file_path = path.join(ROOT, "examples", "curves.3dm")
    rpyc_server_py = path.join(ROOT, "ghcompservice.py")

    with PythonToGrasshopperRemote(
        None, rpyc_server_py, rhino_ver=7, timeout=60, log_level=logging.DEBUG
    ) as py2gh:
        # Stuff that we can reach
        rghcomp = py2gh.gh_remote_components  # Named Grasshopper compiled components
        rghuo = py2gh.gh_remote_userobjects  # Named Grasshopper user objects
        rgh = py2gh.connection  # Represents the remote instance root object
        Rhino = (
            rgh.modules.Rhino
        )  # rgh.modules.something is like ``import something`` on the remote
        rs = rgh.modules.rhinoscriptsyntax  # Same

        # Opening a Rhino file
        readopt = Rhino.FileIO.FileReadOptions()
        readopt.BatchMode = True
        Rhino.RhinoDoc.ReadFile(
            rhino_file_path, readopt
        )  # Or pass in a first argument to py2gh to open a file

        # Doing stuff in that file
        type_curve = Rhino.DocObjects.ObjectType.Curve
        curves = Rhino.RhinoDoc.ActiveDoc.Objects.FindByObjectType(type_curve)
        curves_id = tuple(
            c.Id for c in curves
        )  # rhinoscriptsyntax doesn't like mutable objects through the connection
        gh_curves = rs.coerceguidlist(curves_id)
        # Call a GH component
        print(sum(rghcomp.Area(gh_curves)[0]))
        # Call a GH user object, previously created with the name "TestClusterGHPythonRemote"
        # returns x^2 + y + 2
        print(rghuo.TestClusterGHPythonRemote(3, y=4))  # = 15
