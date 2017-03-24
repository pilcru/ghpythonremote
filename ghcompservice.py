import rpyc
import sys
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
            component = getattr(component, component_name)
        return component


if __name__ == '__main__':
    print('Starting server...')
    cpu_count = 8
    threads = max(cpu_count - 1, 1)
    server = OneShotServer(GhcompService, hostname='localhost', port=18871, listener_timeout=None)  # TODO: use nameserver to avoid relying on available ports
    server.start()
