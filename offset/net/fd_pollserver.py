# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno

from .. import os
from ..core.chan import makechan
from ..core.kernel import DEFAULT_MAX_THREADS, go
from ..syscall import select
from ..syscall import fexec
from ..sync import Mutex, Once
from ..time import nano

from .exc import Timeout
from .util import Deadline

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
        fexec.setnonblock(self.pr)
        fexec.setnonblock(self.pw)
        self.poll.addfd(self.pr, 'r')

        self.pending = {}
        self.deadline = 0

        go(self.run)

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
        if t > 0 and (self.deadline == 0 or self.deadline < t):
            self.deadline = t
            do_wakeup = True

        self.poll.addfd(pd.sysfd, mode, False)
        self.unlock()

        if do_wakeup:
            self.wakeup()

    def evict(self, pd):
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
            os.write(self.pw, b'.')
        except IOError as e:
            if e.errno not in [errno.EAGAIN, errno.EINTR]:
                raise

    def lookupfd(self, fd, mode):
        key = fd << 1
        if mode == 'w':
           key += 1

        try:
            netfd = self.pending.pop(key)
        except KeyError:
            return None

        return netfd

    def wakefd(self, pd, mode):
        if mode == 'r':
            while pd.ncr > 0:
                pd.ncr -= 1
                pd.cr.send(True)
        else:
            while pd.ncw > 0:
                pd.ncw -= 1
                pd.cw.send(True)

    def check_deadline(self):
        now = nano()

        next_deadline = 0
        pending = self.pending.copy()
        for key, pd in pending.items():
            if key & 1 == 0:
                mode = 'r'
            else:
                mode = 'w'

            if mode == 'r':
                t = pd.rdeadline.value()
            else:
                t = pd.wdeadline.value()

            if t > 0:
                if t <= now:
                    del self.pending[key]
                    self.poll.delfd(pd.sysfd, mode)
                    self.wakefd(pd, mode)
                elif next_deadline == 0 or t < next_deadline:
                    next_deadline = t

        self.deadline = next_deadline

    def run(self):
        with self.m:
            while True:
                timeout = 0
                if self.deadline > 0:
                    timeout = self.deadline - nano()
                    if timeout <= 0:
                        self.check_deadline()
                        continue

                fd, mode = self.poll.waitfd(self, timeout)
                if fd < 0:
                    self.check_deadline()
                    continue

                if fd == self.pr.fileno():
                    os.read(self.pr, 1)
                    self.check_deadline()

                else:
                    pd = self.lookupfd(fd, mode)
                    if not pd:
                        continue
                    self.wakefd(pd, mode)


pollservers = {}
startserveronce = Once()

@startserveronce.do
def sysinit():
    global pollservers

    for i in range(DEFAULT_MAX_THREADS):
        pollservers[i] = PollServer()


class PollDesc(object):

    def __init__(self, fd):

        # init pollservers
        sysinit()

        polln = len(pollservers)
        k = fd.sysfd % polln
        self.sysfd = fd.sysfd
        self.pollserver = pollservers[k]

        self.cr = makechan(1)
        self.cw = makechan(1)
        self.ncr = 0
        self.ncw = 0
        self.rdeadline = Deadline()
        self.wdeadline = Deadline()

    def close(self):
        pass

    def lock(self):
        self.pollserver.lock()

    def unlock(self):
        self.pollserver.unlock()

    def wakeup(self):
        self.pollserver.wakeup()

    def prepare_read(self):
        if self.rdeadline.expired():
            raise Timeout

    def prepare_write(self):
        if self.wdeadline.expired():
            raise Timeout

    def wait_read(self):
        self.pollserver.addfd(self, 'r')
        return self.cr.recv()

    def wait_write(self):
        self.pollserver.addfd(self, 'w')
        return self.cw.recv()

    def evict(self):
        return self.pollserver.evict(self)
