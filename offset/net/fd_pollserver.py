# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .. import os
from ..syscall import select
from ..syscall import fexec
from ..sync import Mutex


if hasattr(select, "kqueue"):
    from .fd_bsd import Pollster
elif hasattr(select, "epoll"):
    from .fd_epoll import Pollster
elif hasattr(select, "poll") or hasattr(select, "devpoll"):
    from .fd_poll import Pollster
else:
    from .fd_select import Pollster


class PollServer(object):

    def __init__(self):
        self.m = Mutex()

        self.poll = Pollster()

        self.pr, self.pw = os.pipe()
        fexec.set_non_block(self.pr)
        fexec.set_non_block(self.pw)
        self.poll.addfd(self.pr, 'r')

        self.pending = {}
        self.deadline = 0

    def lock(self):
        self.m.lock()

    def unlock(self):
        self.m.unlock()

    def addfd(self, pd, mode):
        self.lock()
        if pd.sysfd < 0 or pd.closing:
            self.unlock()
            raise ValueError("fd closing")

        key = pd.sysfd << 1
        t = 0
        if mode == 'r':
            pd.ncr += 1
            t = pd.rdeadline.value
        else:
            pd.ncw += 1
            key += 1
            t = pd.wdeadline.value

        self.pending[key] = pd
        do_wakeup = False
        if t > 0 and (self.deadline == 0 or s.deadline < t):
            self.deadline = t
            do_wakeup = True

        self.poll.addfd(pd.sysfd, mode, False)
        self.unlock()

        if do_wakeup:
            self.wakeup()

    def evictfd(self, pd):
        pd.closing = True

        try:
            if self.pending[pd.sysfd << 1] == pd:
                self.wakefd(pd, 'r')
                self.poll.delfd(pd.sysfd)
                del self.pending[pd.sysfd << 1]
        except KeyError:
            pass

        try:
            if self.pending[pd.sysfd << 1 | 1]:
                self.wakefd(pd, 'w')
                self.poll.delfd(pd.sysfd, 'w')
                del self.pending[pd.sysfd << 1 | 1]
        except KeyError:
            pass

    def wakeup(self):
        self.pw.write(b'.')

        try:
            os.write(self.PIPE[1], b'.')
        except IOError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise






