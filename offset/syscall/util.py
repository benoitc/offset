# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import inspect
from importlib import import_module

from ..core.kernel import syscall

def inherit_module(src, target, routines=False, sysnbl=[]):
    src_mod = import_module(src)
    target_mod = import_module(target)

    names = []
    for (name, obj) in inspect.getmembers(src_mod):
        if inspect.isfunction(obj) or inspect.isbuiltin(obj):
            if not routines:
                continue

            if name not in sysnbl:
                obj = syscall(obj)

        setattr(target_mod, name, obj)
        names.append(name)

    if hasattr(target_mod, '__all__'):
        target_mod.__all__.extend(names)
