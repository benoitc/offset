# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from importlib import import_module
import inspect
import sys

from ..core.kernel import syscall
from .util import inherit_module

select_mod = import_module("select")

__all__ = ['devpoll', 'epoll', 'poll', 'kqueue', 'select']

class _Poll(object):

    def register(self, *args):
        return self.poll.register(*args)

    def modify(self, *args):
        return self.poll.modify(*args)

    def unregister(self, *args):
        return self.poll.unregister(*args)

    def poll(self, *args):
        return syscall(self.poll.poll)(*args)


if hasattr(select_mod, "devpoll"):

    class devpoll(_Poll):

        def __init__(self):
            self.poll = select_mod.devpoll()


if hasattr(select_mod, "epoll"):

    class epoll(_Poll):

        def __init__(self):
            self.poll = select_mod.epoll()

        def close(self):
            return self.poll.close()

        def fileno(self):
            return self.poll.close()

        def fromfd(self, fd):
            return self.poll.fromfd(fd)


if hasattr(select_mod, "poll"):

    class poll(_Poll):

        def __init__(self):
            self.poll = select_mod.poll()


if hasattr(select_mod, "kqueue"):

    kevent = select_mod.kevent

    class kqueue(object):

        def init(self):
            self.kq = select_mod.kqueue()

        def fileno(self):
            return self.kq.fileno()

        def fromfd(self, fd):
            return self.kq.fromfd(fd)

        def close(self):
            return self.kq.close()

        def control(self, *args, **kwargs):
            return syscall(self.kq.control)(*args, **kwargs)

select = select_mod.select

# import select variables
inherit_module("select", __name__)
