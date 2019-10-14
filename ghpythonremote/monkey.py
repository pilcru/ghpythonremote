import sys

import rpyc

if sys.platform == "cli":
    # Some compatibility fixes for IronPython
    rpyc.core.brine.IMM_INTS = dict((i, bytes([i + 0x50])) for i in range(-0x30, 0xA0))

    def BYTES_LITERAL(text):
        return bytes(text)

    rpyc.lib.compat.BYTES_LITERAL = BYTES_LITERAL

    if sys.version_info < (2, 7, 5):

        def dump(obj):
            stream = []
            rpyc.core.brine._dump(obj, stream)
            return b"".join(map(bytes, stream))

        rpyc.core.brine.dump = dump
else:
    # This is only needed if the local is CPython and the remote is IronPython, doesn't
    # really hurt otherwise
    _netref_factory_orig = rpyc.core.protocol.Connection._netref_factory

    def _netref_factory_str(self, id_pack):
        return _netref_factory_orig(self, (str(id_pack[0]), id_pack[1], id_pack[2]))

    rpyc.core.protocol.Connection._netref_factory = _netref_factory_str
