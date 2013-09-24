# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


import threading
import _continuation


_tls = threading.local()

continulet = _continuation.continulet


def current():
    try:
        return _tls.current_fiber
    except AttributeError:
        return _main_fiber()

def _main_fiber():
    try:
        return _tls.main_fiber
    except AttributeError:
        _tls.main_fiber = Fiber(_frame=continulet.__new__(continulet))
        return _tls.main_fiber


class errors(Exception):
    """ error raised """


class Fiber(object):

    def __init__(self, target=None, args=[], kwargs={}, parent=None,
            _frame=None):

        if _frame is not None:
            self.frame = _frame
        else:
            def _run(c):
                _tls.current_fiber = self
                try:
                    target(*args, **kwargs)
                finally:
                    self._is_started = False

            self._func = _run
            self.frame = None

            if parent is None:
                self.parent = current()

        self._is_started = True


    def switch(self):
        if not self._is_started:
            raise errors("Fiber has ended")

        self._maybe_bind()

        # switch
        curr = current()
        try:
            curr.frame.switch(to=self.frame)
        finally:
            _tls.current_fiber = curr


    def throw(self, *args):
        if not self._is_started:
            raise errors("Fiber has ended")

        self._maybe_bind()

        # switch
        curr = current()
        try:
            curr.frame.throw(*args, to=self.frame)
        finally:
            _tls.current_fiber = curr


    def is_alive(self):
        return self._is_started

    @classmethod
    def current(cls):
        return _tls.current_fiber

    def _maybe_bind(self):
        if self.frame is None:
            self.frame = _continuation.continulet(self._func)
