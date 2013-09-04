
import functools
import inspect
from importlib import import_module
import sys
import os

from offset.runtime.proc import runtime

_imported = False

_IMPORTED_MODULES = ("os", "os.path", "socket", "select",)

def syscall(func):
    """ wrap a function to handle its result asynchronously

    This function is useful when you don't want to block the scheduler
    and execute the other goroutine while the function is processed
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # enter the functions in syscall
        ret = runtime.enter_syscall(func, *args, **kwargs)
        return ret
    return _wrapper


def _bootstrap():
    global _imported
    if not _imported:
        syscall_mod = sys.modules[__name__]

        for modname in _IMPORTED_MODULES:
            mod = import_module(modname)
            for (name, obj) in inspect.getmembers(mod):
                if inspect.isroutine(obj):
                    f = syscall(obj)
                    setattr(syscall_mod, name, f)
                else:
                    setattr(syscall_mod, name, obj)

    _imported = True

_bootstrap()
