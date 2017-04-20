import rpyc
from rpyc.utils.server import OneShotServer


class GhcompService(rpyc.SlaveService):
    def on_connect(self):
        print('Incoming connection.')
        super(GhcompService, self).on_connect()
        import ghpythonlib.components as ghcomp
        self.ghcomp = ghcomp

    def on_disconnect(self):
        print('Disconnected.')

    def exposed_get_component(self, component_name, is_cluster_component=False):
        component = getattr(self.ghcomp, component_name)
        if is_cluster_component:
            component = getattr(component, component_name)  # TODO: improve ghcomp to get clusters the same way we get compiled components, thus removing the need for a custom getter
        return component


if __name__ == '__main__':
    print('Starting server...')
    server = OneShotServer(GhcompService, hostname='localhost', port=18871, listener_timeout=None)  # TODO: use nameserver to avoid relying on available ports
    server.start()
