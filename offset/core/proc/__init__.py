# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

try:
    import _continuation
    fibers = None
except ImportError:
    try:
        import fibers
    except ImportError:
        raise RuntimeError("platform not supported")


if fibers is not None:
    from .proc_fiber import Proc, MainProc, current
else:
    from .proc_continulet import Proc, MainProc, current
