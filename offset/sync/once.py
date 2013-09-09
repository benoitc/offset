# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import functools

from .atomic import AtomicLong
from .mutex import Mutex

class Once(object):
    """ Once is an object that will perform exactly one action. """

    def __init__(self):
        self.m = Mutex()
        self.done = AtomicLong(0)

    def do(self, func):
        """ Do calls the function f if and only if the method is being called for the

        ex::

            once = Once

            @once.do
            def f():
                return

            # or
            once.do(f)()

        if once.do(f) is called multiple times, only the first call will invoke
        f.
        """

        @functools.wraps(func)
        def _wrapper(*args, **kwargs):
            if self.done == 1:
                return

            with self.m:
                if self.done == 0:
                    func(*args, **kwargs)
                    self.done.value = 1

        return _wrapper
