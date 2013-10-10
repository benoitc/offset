# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import errno

from .util import fd_
from ..syscall import select


class Pollster(object):

    def __init__(self):
        self.read_fds = {}
        self.write_fds = {}
        self.events = []

    def addfd(self, fd, mode, repeat=True):
        fd = fd_(fd)

        if mode == 'r':
            self.read_fds[fd] = repeat
        else:
            self.write_fds[fd] = repeat

    def delfd(self, fd, mode):
        if mode == 'r' and fd in self.read_fds:
            del self.read_fds[fd]
        elif fd in self.write_fds:
            del self.write_fds[fd]

    def waitfd(self, pollserver, nsec):
        read_fds = [fd for fd in self.read_fds]
        write_fds = [fd for fd in self.write_fds]

        while len(self.events) == 0:
            pollserver.unlock()
            try:
                r, w, e = select.select(read_fds, write_fds, [], nsec)
            except select.error as e:
                if e.args[0] == errno.EINTR:
                    continue
                raise
            finally:
                pollserver.lock()

            events = []
            for fd in r:
                if fd in self.read_fds:
                    if self.read_fds[fd] == False:
                        del self.read_fds[fd]
                    events.append((fd, 'r'))

            for fd in w:
                if fd in self.write_fds:
                    if self.write_fds[fd] == False:
                        del self.write_fds[fd]
                    events.append((fd, 'w'))

            self.events.extend(events)

        return self.evens.pop(0)

    def close(self):
        self.read_fds = []
        self.write_fds = []
