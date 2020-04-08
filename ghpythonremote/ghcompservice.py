import logging
import sys

from ghpythonremote import rpyc
from rpyc.utils.server import OneShotServer


class GhcompService(rpyc.ClassicService):
    def on_connect(self, conn):
        print("Incoming connection.")
        super(GhcompService, self).on_connect(conn)
        import ghpythonlib.components as ghcomp
        from ghpythonremote import ghuserobjects as ghuo

        self.ghcomp = ghcomp
        self.ghuo = ghuo

    def on_disconnect(self, conn):
        print("Disconnected.")


if __name__ == "__main__":
    import rhinoscriptsyntax as rs

    port = rs.GetInteger("Server bind port", 18871, 1023, 65535)
    log_level = rs.GetInteger("Log level as int", 30, 0, 100)

    logger = logging.getLogger()
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    formatter = logging.Formatter(
        "\n%(asctime)s - %(name)s - %(levelname)s -\n%(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger = logging.getLogger("ghpythonremote.ghcompservice")
    logger.info("Starting server...")

    server = OneShotServer(
        GhcompService, hostname="localhost", port=port, listener_timeout=None
    )
    server.start()
