# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.#

import sys

__all__ = []

from .file import File, pipe

os_mod = sys.modules[__name__]


_signal = __import__('signal')

for name in dir(_signal):
    if name[:3] == "SIG" and name[3] != "_":
        setattr(os_mod, name, getattr(_signal, name))
        __all__.append(name)

del _signal

