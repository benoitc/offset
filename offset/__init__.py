# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

version_info = (0, 1, 0)
__version__ = ".".join([str(v) for v in version_info])

# scheduler functions
from .core import go, run, gosched, maintask

# channel functions
from .core.chan import makechan, select, default

# exceptions
from .core.exc import PanicError
