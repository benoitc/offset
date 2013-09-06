
import functools
import inspect
from importlib import import_module
import sys
import os

from .core import syscall

_imported = False

_IMPORTED_MODULES = ("os", "os.path", "socket", "select",)


def _bootstrap():
    global _imported
    if not _imported:
        syscall_mod = sys.modules[__name__]

        for modname in _IMPORTED_MODULES:
            mod = import_module(modname)
            for (name, obj) in inspect.getmembers(mod):
                if inspect.isfunction(obj) and inspect.isbuiltin(obj):
                    f = syscall(obj)
                    setattr(syscall_mod, name, f)
                else:
                    setattr(syscall_mod, name, obj)

    _imported = True

_bootstrap()
