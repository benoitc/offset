# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import threading

import _continuation


from .exc import ProcExit

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

        def _run(c):
            _tls.current_proc = self
            self._is_started = 1
            return func(*args, **kwargs)

        self.frame = _continuation.continulet(_run)

        self.sleeping = False
        #self._sleeping = atomic.AtomicLong(0)
        self.param = None
        self._is_started = 0

    def switch(self):
        current = _proc_getcurrent()
        try:
            current.frame.switch(to=self.frame)
        finally:
            _tls.current_proc = current

    def throw(self, *args):
        current = _proc_getcurrent()
        try:
            current.frame.throw(*args, to=self.frame)
        finally:
            _tls.current_proc = current

    def is_alive(self):
        return self._is_started < 0 or (self.frame is not None and
                self.frame.is_pending())

    def __reduce__(self):
        if self._is_started < 0:
            return _proc_getmain, ()
        else:
            return type(self), (), self.__dict__

    def __eq__(self, other):
        return self.frame == other.frame

continulet = _continuation.continulet

class MainProc(Proc):

    def __init__(self):
        self._is_started = -1
        self.frame = continulet.__new__(continulet)
        self.param = None
        self.sleeping = True

current = _proc_getcurrent
