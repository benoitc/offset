# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.#

from . import util
from ..core import kernel

_select = __import__("select")

__all__ = ["select"]

class _Poll(object):

    def register(self, *args):
        return self.poll.register(*args)

    def modify(self, *args):
        return self.poll.modify(*args)

    def unregister(self, *args):
        return self.poll.unregister(*args)

    def poll(self, *args):
        return kernel.syscall(self.poll.poll)(*args)


if hasattr(_select, "devpoll"):

    class devpoll(_Poll):

        def __init__(self):
            self.poll = _select.devpoll()

    __all__.extend(['devpoll'])


if hasattr(_select, "epoll"):

    class epoll(_Poll):

        def __init__(self):
            self.poll = _select.epoll()

        def close(self):
            return self.poll.close()

        def fileno(self):
            return self.poll.close()

        def fromfd(self, fd):
            return self.poll.fromfd(fd)

    __all__.extend(['epoll'])

if hasattr(_select, "poll"):

    class poll(_Poll):

        def __init__(self):
            self.poll = _select.poll()

    __all__.extend(['poll'])

if hasattr(_select, "kqueue"):

    kevent = _select.kevent

    class kqueue(object):

        def init(self):
            self.kq = _select.kqueue()

        def fileno(self):
            return self.kq.fileno()

        def fromfd(self, fd):
            return self.kq.fromfd(fd)

        def close(self):
            return self.kq.close()

        def control(self, *args, **kwargs):
            return kernel.syscall(self.kq.control)(*args, **kwargs)

    __all__.extend(['kqueue'])

select = kernel.syscall(_select.select)

util.inherit_module('select', __name__)

del util
del kernel

