import inspect
import logging
from os import path

import ghpythonremote
from ghpythonremote.connectors import PythonToGrasshopperRemote

logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)

# TODO: This could be made a console script in setup.py, with some additional config
if __name__ == "__main__":
    ROOT = path.abspath(path.dirname(inspect.getfile(ghpythonremote)))
    rhino_file_path = path.join(ROOT, "examples", "curves.3dm")
    rpyc_server_py = path.join(ROOT, "ghcompservice.py")

    with PythonToGrasshopperRemote(
        rhino_file_path, rpyc_server_py, rhino_ver=6, timeout=60
    ) as py2gh:
        # Stuff that we can reach
        rghcomp = (
            py2gh.gh_remote_components
        )  # A getter function for a named Grasshopper compiled component or cluster
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
        area = rghcomp("Area", is_cluster_component=False)
        print(sum(area(gh_curves)[0]))
