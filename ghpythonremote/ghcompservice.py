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


if __name__ == "__main__":
    import rhinoscriptsyntax as rs

    port = rs.GetInteger("Server bind port", 18871, 1023, 65535)

    server = OneShotServer(
        GhcompService, hostname="localhost", port=port, listener_timeout=None
    )
    server.start()
