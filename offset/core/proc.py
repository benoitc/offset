# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import threading

try:
    import fibers
except ImportError:
    raise RuntimeError("Platform not supported")

_tls = threading.local()


class ProcExit(Exception):
    """ exception raised when the proc is asked to exit """

def _proc_getcurrent():
    try:
        return _tls.current_proc
    except AttributeError:
        return _proc_getmain()


def _proc_getmain():
    try:
        return _tls.main_proc
    except AttributeError:
        _tls.main_proc = MainProc()
        return _tls.main_proc


class Proc(object):

    def __init__(self, m, func, args, kwargs):


        def _run():
            _tls.current_proc = self
            self._is_started = 1
            try:
                return func(*args, **kwargs)
            except ProcExit:
                pass
            finally:
                m.removeg()

        self.m = m
        self.fiber = fibers.Fiber(_run)
        self.waiting = False
        self.sleeping = False
        self.param = None
        self._is_started = 0

    def switch(self):
        current = _proc_getcurrent()
        try:
            self.fiber.switch()
        finally:
            _tls.current_proc = current

    def throw(self, *args):
        current = _proc_getcurrent()
        try:
            self.fiber.throw(*args)
        finally:
            _tls.current_proc = current

    def is_alive(self):
        return self._is_started < 0 or self.fiber.is_alive()

    def __eq__(self, other):
        return self.fiber == other.fiber

class MainProc(Proc):

    def __init__(self):
        self._is_started = -1
        self.param = None
        self.fiber = fibers.current()
        self.sleeping = True

current = _proc_getcurrent
