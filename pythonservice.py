import rpyc
from rpyc.utils.server import OneShotServer


class PythonService(rpyc.SlaveService):
    def on_connect(self):
        print('Incoming connection.')
        super(PythonService, self).on_connect()

    def on_disconnect(self):
        print('Disconnected.')


if __name__ == '__main__':
    print('Starting server...')
    server = OneShotServer(PythonService, hostname='localhost', port=18872, listener_timeout=None)  # TODO: use nameserver to avoid relying on available ports
    server.start()
