import inspect
import sys

import rpyc

if sys.platform == "cli":
    # Some compatibility fixes for IronPython
    rpyc.core.brine.IMM_INTS = dict((i, bytes([i + 0x50])) for i in range(-0x30, 0xA0))

    def BYTES_LITERAL(text):
        return bytes(text)

    rpyc.lib.compat.BYTES_LITERAL = BYTES_LITERAL

    # Fixes for ghpythonlib.components.__namedtuple.__getattr__
    fix_rhino_getattr = False
    try:
        from Rhino.RhinoApp import ExeVersion

        if ExeVersion == 6:
            fix_rhino_getattr = True
    except ImportError:
        pass

    if fix_rhino_getattr:
        import ghpythonlib.components

        def get_id_pack(obj):
            """introspects the given "local" object, returns id_pack as expected by BaseNetref

            The given object is "local" in the sense that it is from the local cache. Any object in the local cache exists
            in the current address space or is a netref. A netref in the local cache could be from a chained-connection.
            To handle type related behavior properly, the attribute `__class__` is a descriptor for netrefs.

            So, check thy assumptions regarding the given object when creating `id_pack`.
            """

            # TODO: Remove that when ghpythonlib.components.__namedtuple.__getattr__ is fixed
            if hasattr(obj, "____id_pack__") and not isinstance(
                obj, ghpythonlib.components.__namedtuple
            ):
                # netrefs are handled first since __class__ is a descriptor
                return obj.____id_pack__
            # str(obj).split(':')[0] == "Microsoft.Scripting.Actions.NamespaceTracker" should also work
            elif (
                inspect.ismodule(obj)
                or getattr(obj, "__name__", None) == "module"
                or str(type(obj)) == "<type 'namespace#'>"
            ):
                # TODO: not sure about this, need to enumerate cases in units
                if isinstance(obj, type):  # module
                    obj_cls = type(obj)
                    name_pack = "{0}.{1}".format(obj_cls.__module__, obj_cls.__name__)
                    return (name_pack, id(type(obj)), id(obj))
                else:
                    if inspect.ismodule(obj) and obj.__name__ != "module":
                        if obj.__name__ in sys.modules:
                            name_pack = obj.__name__
                        else:
                            name_pack = "{0}.{1}".format(
                                obj.__class__.__module__, obj.__name__
                            )
                    elif inspect.ismodule(obj):
                        name_pack = "{0}.{1}".format(obj.__module__, obj.__name__)
                        print(name_pack)
                    elif hasattr(obj, "__module__"):
                        name_pack = "{0}.{1}".format(obj.__module__, obj.__name__)
                    else:
                        obj_cls = type(obj)
                        name_pack = "{0}".format(obj.__name__)
                    return (name_pack, id(type(obj)), id(obj))
            elif not inspect.isclass(obj):
                name_pack = "{0}.{1}".format(
                    obj.__class__.__module__, obj.__class__.__name__
                )
                return (name_pack, id(type(obj)), id(obj))
            else:
                name_pack = "{0}.{1}".format(obj.__module__, obj.__name__)
                return (name_pack, id(obj), 0)

        def _handle_inspect(self, id_pack):  # request handler
            obj = self._local_objects[id_pack]
            if hasattr(obj, "____conn__") and not isinstance(
                obj, ghpythonlib.components.__namedtuple
            ):
                # When RPyC is chained (RPyC over RPyC), id_pack is cached in local objects as a netref
                # since __mro__ is not a safe attribute the request is forwarded using the proxy connection
                # see issue #346 or tests.test_rpyc_over_rpyc.Test_rpyc_over_rpyc
                conn = self._local_objects[id_pack].____conn__
                return conn.sync_request(rpyc.core.consts.HANDLE_INSPECT, id_pack)
            else:
                return tuple(
                    rpyc.lib.get_methods(
                        rpyc.core.netref.LOCAL_ATTRS, self._local_objects[id_pack]
                    )
                )

        rpyc.core.protocol.Connection._handle_inspect = _handle_inspect
        
    else:

        def get_id_pack(obj):
            """introspects the given "local" object, returns id_pack as expected by BaseNetref

            The given object is "local" in the sense that it is from the local cache. Any object in the local cache exists
            in the current address space or is a netref. A netref in the local cache could be from a chained-connection.
            To handle type related behavior properly, the attribute `__class__` is a descriptor for netrefs.

            So, check thy assumptions regarding the given object when creating `id_pack`.
            """

            if hasattr(obj, "____id_pack__"):
                # netrefs are handled first since __class__ is a descriptor
                return obj.____id_pack__
            # str(obj).split(':')[0] == "Microsoft.Scripting.Actions.NamespaceTracker" should also work
            elif (
                inspect.ismodule(obj)
                or getattr(obj, "__name__", None) == "module"
                or str(type(obj)) == "<type 'namespace#'>"
            ):
                # TODO: not sure about this, need to enumerate cases in units
                if isinstance(obj, type):  # module
                    obj_cls = type(obj)
                    name_pack = "{0}.{1}".format(obj_cls.__module__, obj_cls.__name__)
                    return (name_pack, id(type(obj)), id(obj))
                else:
                    if inspect.ismodule(obj) and obj.__name__ != "module":
                        if obj.__name__ in sys.modules:
                            name_pack = obj.__name__
                        else:
                            name_pack = "{0}.{1}".format(
                                obj.__class__.__module__, obj.__name__
                            )
                    elif inspect.ismodule(obj):
                        name_pack = "{0}.{1}".format(obj.__module__, obj.__name__)
                        print(name_pack)
                    elif hasattr(obj, "__module__"):
                        name_pack = "{0}.{1}".format(obj.__module__, obj.__name__)
                    else:
                        obj_cls = type(obj)
                        name_pack = "{0}".format(obj.__name__)
                    return (name_pack, id(type(obj)), id(obj))
            elif not inspect.isclass(obj):
                name_pack = "{0}.{1}".format(
                    obj.__class__.__module__, obj.__class__.__name__
                )
                return (name_pack, id(type(obj)), id(obj))
            else:
                name_pack = "{0}.{1}".format(obj.__module__, obj.__name__)
                return (name_pack, id(obj), 0)

    rpyc.lib.get_id_pack = get_id_pack
    rpyc.core.netref.get_id_pack = get_id_pack
    rpyc.core.protocol.get_id_pack = get_id_pack

    if sys.version_info < (2, 7, 5):

        def dump(obj):
            stream = []
            rpyc.core.brine._dump(obj, stream)
            return b"".join(map(bytes, stream))

        rpyc.core.brine.dump = dump

        import socket

        def write(self, data):
            try:
                while data:
                    count = self.sock.send(buffer(data[: self.MAX_IO_CHUNK]))
                    data = data[count:]
            except socket.error:
                ex = sys.exc_info()[1]
                self.close()
                raise EOFError(ex)

        rpyc.core.stream.SocketStream.write = write
else:
    # This is only needed if the local is CPython and the remote is IronPython, doesn't
    # really hurt otherwise
    _netref_factory_orig = rpyc.core.protocol.Connection._netref_factory

    def _netref_factory_str(self, id_pack):
        return _netref_factory_orig(self, (str(id_pack[0]), id_pack[1], id_pack[2]))

    rpyc.core.protocol.Connection._netref_factory = _netref_factory_str
