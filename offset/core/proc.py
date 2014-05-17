# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import threading
import time

try:
    import fibers
except ImportError:
    raise RuntimeError("Platform not supported")

_tls = threading.local()


class ProcExit(Exception):
    """ exception raised when the proc is asked to exit """

def current():
    try:
        return _tls.current_proc
    except AttributeError:
        _create_main_proc()
        return _tls.current_proc


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
        curr = current()
        try:
            self.fiber.switch()
        finally:
            _tls.current_proc = curr

    def throw(self, *args):
        curr = current()
        try:
            self.fiber.throw(*args)
        finally:
            _tls.current_proc = curr

    def park(self):
        self.m.park(self)

    def ready(self):
        self.m.ready(self)

    def is_alive(self):
        return self._is_started < 0 or self.fiber.is_alive()

    def terminate(self):
        self.throw(ProcExit, ProcExit("exit"))
        time.sleep(0.1)

    def __eq__(self, other):
        return self.fiber == other.fiber


def _create_main_proc():
    main_proc = Proc.__new__(Proc)
    main_proc.fiber = fibers.current()
    main_proc._is_started = True
    main_proc.sleeping = True

    _tls.main_proc = main_proc
    _tls.current_proc = main_proc
