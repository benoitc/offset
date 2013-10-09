# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .util import fd
from ..syscall import select


if not hasattr(select, "epoll"):
    raise RuntimeError("epoll is not supported")

class Poller(object):

    def __init__(self):
        self.poll = select.epoll()
        syscall.closeonexec(self.poll.fileno())
        self.fds = []
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        if mode == 'r':
            mode = (select.EPOLLIN, repeat)
        else:
            mode = (select.EPOLLOUT, repeat)

        if fd in self.fds:
            modes = self.fds[fd]
            if mode in self.fds[fd]:
                # already registered for this mode
                return
            modes.append(mode)
            addfd_ = self.poll.modify
        else:
            modes = [mode]
            addfd_ = self.poll.register

        # append the new mode to fds
        self.fds[fd] = modes

        mask = 0
        for mode, r in modes:
            mask |= mode

        if not repeat:
            mask |= select.EPOLLONESHOT

        addfd_(fd, mask)

    def delfd(self, fd, mode):
        if mode == 'r':
            mode = select.POLLIN | select.POLLPRI
        else:
            mode = select.POLLOUT

        if fd not in self.fds:
            return

        modes = []
        for m, r in self.fds[fd]:
            if mode != m:
                modes.append((m, r))

        if not modes:
            # del the fd from the poll
            self.poll.unregister(fd)
            del self.fds[fd]
        else:
            # modify the fd in the poll
            self.fds[fd] = modes
            m, r = modes[0]
            mask = m[0]
            if r:
                mask |= select.EPOLLONESHOT

            self.poll.modify(fd, mask)

    def waitfd(self, pollserver, nsec=0):
        # wait for the events
        while len(self.events) == 0:
            pollserver.lock()
            try:
                events = self.poll.poll(nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.unlock()

            self.events.extend(event)

        (fd, ev) = self.events.pop(0)
        fd = to_fd(fd)

        if ev == select.EPOLLIN:
            mode = 'r'
        else:
            mode = 'w'

        # eventually remove the mode from the list if repeat was set to
        # False and modify the poll if needed.
        modes = []
        for m, r in self.fds[fd]:
            if not r:
                continue
            modes.append(m, r)

        if modes != self.fds[fd]:
            self.fds[fd] = mode

            mask = 0
            for m, r in modes:
                mask |= m

            self.poll.modify(fd, mask)

        return (fd_(fd), mode)

    def close(self):
        self.poll.close()
