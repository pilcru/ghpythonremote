import rpyc

c = rpyc.utils.factory.connect(
    "localhost",
    18871,
    service=rpyc.core.service.ClassicService,
    config={"sync_request_timeout": None},
    ipv6=False,
    keepalive=True,
)

rghcomp = c.root.get_component
rgh = c
Rhino = rgh.modules.Rhino
rs = rgh.modules.rhinoscriptsyntax

readopt = Rhino.FileIO.FileReadOptions()
readopt.BatchMode = True
Rhino.RhinoDoc.ReadFile(
    r"C:\Users\pcuvil\CODE\ghpythonremote\ghpythonremote\examples\curves.3dm", readopt
)
type_curve = Rhino.DocObjects.ObjectType.Curve
curves = Rhino.RhinoDoc.ActiveDoc.Objects.FindByObjectType(type_curve)
curves_id = tuple(c.Id for c in curves)
gh_curves = rs.coerceguidlist(curves_id)
area = rghcomp("Area", is_cluster_component=False)
print(sum(area(gh_curves)[0]))


########################################
### Below is what to paste in Rhino Python

from ghpythonremote import rpyc
from rpyc.utils.server import OneShotServer


class GhcompService(rpyc.ClassicService):
    def on_connect(self, conn):
        print("Incoming connection.")
        super(GhcompService, self).on_connect(conn)
        import ghpythonlib.components as ghcomp

        self.ghcomp = ghcomp

    def on_disconnect(self, conn):
        print("Disconnected.")

    def get_component(self, component_name, is_cluster_component=False):
        component = getattr(self.ghcomp, component_name)
        if is_cluster_component:
            component = getattr(
                component, component_name
            )
            # TODO: improve ghcomp to get clusters the same way we get compiled
            # components, thus removing the need for a custom getter
        return component

server = OneShotServer(
    GhcompService, hostname="localhost", port=18871, listener_timeout=None
)
server.start()
