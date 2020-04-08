"""
Copyright (c) 2011-2013 Robert McNeel & Associates. All Rights Reserved.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software.

THIS SOFTWARE IS PROVIDED "AS IS" WITHOUT EXPRESS OR IMPLIED WARRANTY.
ALL IMPLIED WARRANTIES OF FITNESS FOR ANY PARTICULAR PURPOSE AND OF
MERCHANTABILITY ARE HEREBY DISCLAIMED.
"""

import sys

if sys.platform != "cli":
    raise(RuntimeError, "This module is only intended to be run in Rhino Python")

from collections import namedtuple
import clr

clr.AddReference('Grasshopper, Culture=neutral, PublicKeyToken=dda4f5ec2cd80803')

import System
import Rhino
import Grasshopper as gh
import sys
import re


class namespace_object(object):
    pass


def __make_function_uo__(helper):
    def component_function(*args, **kwargs):
        comp = helper.proxy.CreateInstance()
        comp.ClearData()
        if args:
            for i, arg in enumerate(args):
                if arg is None: continue
                param = comp.Params.Input[i]
                param.PersistentData.Clear()
                if hasattr(arg, '__iter__'):  # TODO deal with polyline, str
                    [param.AddPersistentData(a) for a in arg]
                else:
                    param.AddPersistentData(arg)
        if kwargs:
            for param in comp.Params.Input:
                name = param.Name.lower()
                if name in kwargs:
                    param.PersistentData.Clear()
                    arg = kwargs[name]
                    if hasattr(arg, '__iter__'):  # TODO deal with polyline, str
                        [param.AddPersistentData(a) for a in arg]
                    else:
                        param.AddPersistentData(arg)
        doc = gh.Kernel.GH_Document()
        doc.AddObject(comp, False, 0)
        comp.CollectData()
        comp.ComputeData()
        output = helper.create_output(comp.Params)
        comp.ClearData()
        doc.Dispose()
        return output

    return component_function


class function_helper(object):
    def __init__(self, proxy, name):
        self.proxy = proxy
        self.return_type = None

    def create_output(self, params, output_values=None):
        if not output_values:
            output_values = []
            for output in params.Output:
                data = output.VolatileData.AllData(True)
                # We could call Value, but ScriptVariable seems to do a better job
                v = [x.ScriptVariable() for x in data]
                if len(v) < 1:
                    output_values.append(None)
                elif len(v) == 1:
                    output_values.append(v[0])
                else:
                    output_values.append(v)
        if len(output_values) == 1: return output_values[0]
        if self.return_type is None:
            names = [output.Name.lower() for output in params.Output]
            try:
                self.return_type = namedtuple('Output', names, rename=True)
            except:
                self.return_type = False
        if not self.return_type: return output_values
        return self.return_type(*output_values)

    def runfast(self, args, kwargs):
        return False, None


def __build_module_uo():
    core_module = sys.modules[__name__]
    translate_from = u"|+-*\u2070\u00B9\u00B2\u00B3\u2074\u2075\u2076\u2077\u2078\u2079"
    translate_to = "X__x0123456789"
    transl = dict(zip(translate_from, translate_to))

    def regex_helper(match):
        if match.group() in transl:
            return transl[match.group()]
        return ''

    def function_description(description, params):
        rc = ['', description, "Input:"]
        for param in params.Input:
            s = "\t{0} [{1}] - {2}"
            if param.Optional:
                s = "\t{0} (in, optional) [{1}] - {2}"
            rc.append(s.format(param.Name.lower(), param.TypeName, param.Description))
        if params.Output.Count == 1:
            param = params.Output[0]
            rc.append("Returns: [{0}] - {1}".format(param.TypeName, param.Description))
        elif params.Output.Count > 1:
            rc.append("Returns:")
            for out in params.Output:
                s = "\t{0} [{1}] - {2}"
                rc.append(s.format(out.Name.lower(), out.TypeName, out.Description))
        return '\n'.join(rc)

    for obj in gh.Instances.ComponentServer.ObjectProxies:
        if obj.Exposure == gh.Kernel.GH_Exposure.hidden or obj.Obsolete:
            continue

        library_id = obj.LibraryGuid
        assembly = gh.Instances.ComponentServer.FindAssembly(library_id)
        name = obj.Desc.Name

        if "LEGACY" in name or "#" in name:
            continue
        name = re.sub("[^_a-zA-Z0-9]", regex_helper, name)
        if not name[0].isalpha():
            name = 'x' + name

        if assembly is not None:
            # Compiled components, leave them to ghpythonlib
            continue

        function = __make_function_uo__(function_helper(obj, name))
        m = core_module
        try:
            setattr(m, name, function)
            a = m.__dict__[name]
            a.__name__ = name
            comp = obj.CreateInstance()
            a.__doc__ = function_description(obj.Desc.Description, comp.Params)
        except Exception as err:
            Rhino.RhinoApp.WriteLine(str(err))
            Rhino.Runtime.HostUtils.ExceptionReport("ghpythonlib.components.py|" + name,
                                                    err.clsException)


__build_module_uo()
