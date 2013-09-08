# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import threading

import fibers

from .. import atomic

_tls = threading.local()

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

    def __init__(self, func, args, kwargs):

        def _run():
            _tls.current_proc = self
            self._is_started = 1
            return func(*args, **kwargs)

        self.fiber = fibers.Fiber(_run)
        self.waiting = False
        self._sleeping = atomic.AtomicLong(0)
        self.param = None
        self._is_started = 0

    def __get_sleeping(self):
        return bool(self._sleeping)

    def __set_sleeping(self, v):
        self._sleeping.value = int(v)
    sleeping = property(__get_sleeping, __set_sleeping)

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

current = _proc_getcurrent
