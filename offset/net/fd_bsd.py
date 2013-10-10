# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno
import sys

from .util import fd_
from .. import syscall
from ..syscall import select

if not hasattr(select, "kqueue"):
    raise RuntimeError('kqueue is not supported')


class Pollster(object):

    def __init__(self):
        self.kq = select.kqueue()
        syscall.closeonexec(self.kq.fileno())
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        if mode == 'r':
            kmode = select.KQ_FILTER_READ
        else:
            kmode = select.KQ_FILTER_WRITE

        flags = select.KQ_EV_ADD

        if sys.platform.startswith("darwin"):
            flags |= select.KQ_EV_ENABLE

        if not repeat:
            flags |= select.KQ_EV_ONESHOT

        ev = select.kevent(fd_(fd), kmode, flags)
        self.kq.control([ev], 0)

    def delfd(self, fd, mode):
        if mode == 'r':
            kmode = select.KQ_FILTER_READ
        else:
            kmode = select.KQ_FILTER_WRITE

        ev = select.kevent(fd_(fd), select.KQ_FILTER_READ,
                select.KQ_EV_DELETE)
        self.kq.control([ev], 0)

    def waitfd(self, pollserver, nsec=0):
        while len(self.events) == 0:
            pollserver.unlock()
            try:
                events = self.kq.control(None, 0, nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.lock()

            self.events.extend(events)

        ev = self.events.pop(0)
        if ev.filter == select.KQ_FILTER_READ:
            mode = 'r'
        else:
            mode = 'w'

        return (fd_(ev.ident), mode)

    def close(self):
        self.kq.close()
