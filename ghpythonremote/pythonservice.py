import logging
import sys

from ghpythonremote import rpyc
from rpyc.utils.server import OneShotServer


class PythonService(rpyc.ClassicService):
    def on_connect(self, conn):
        logger.info("Incoming connection.")
        super(PythonService, self).on_connect(conn)

    def on_disconnect(self, conn):
        logger.info("Disconnected.")


if __name__ == "__main__":

    if len(sys.argv) >= 3:
        log_level = sys.argv[2]
        try:
            log_level = int(log_level)
        except (TypeError, ValueError):
            log_level = getattr(logging, log_level, logging.WARNING)
    else:
        log_level = logging.WARNING
    if len(sys.argv) >= 2:
        port = sys.argv[1]
    else:
        port = 18871
    try:
        port = int(port)
    except (TypeError, ValueError):
        port = 18871

    # Log everything that happens on the Python server in the console
    logger = logging.getLogger()
    logger.setLevel(log_level)
    ch = logging.StreamHandler()
    ch.setLevel(log_level)
    formatter = logging.Formatter(
        "\n%(asctime)s - %(name)s - %(levelname)s -\n%(message)s"
    )
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger = logging.getLogger("ghpythonremote.pythonservice")
    logger.info("Starting server...")
    server = OneShotServer(
        PythonService,
        hostname="localhost",
        port=port,
        listener_timeout=None,
        logger=logger,
    )
    server.start()
