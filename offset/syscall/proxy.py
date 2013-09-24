# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


__os_mod__ = __import__("os")
__select_mod__ = __import__("select")

import inspect
import wrapt
from ..core import kernel


__all__ = ['OsProxy', 'SelectProxy']


# proxy the OS module

class OsProxy(wrapt.ObjectProxy):
    """ proxy the os module """

    _OS_SYSCALLS =  ("chown", "fchown", "close", "dup", "dup2", "read",
            "pread","write", "pwrite", "sendfile", "readv", "writev", "stat",
            "lstat", "truncate", "sync", "lseek", "open", "posix_fallocate",
            "posix_fadvise", "chmod", "chflags", )

    def __init__(self):
        super(OsProxy, self).__init__(__os_mod__)

    def __getattr__(self, name):
        # wrap syscalls
        if name in self._OS_SYSCALLS:
            return kernel.syscall(getattr(self.__wrapped__, name))

        return getattr(self.__wrapped__, name)


# proxy the socket proxy


class _Poll(object):

    def register(self, *args):
        return self.poll.register(*args)

    def modify(self, *args):
        return self.poll.modify(*args)

    def unregister(self, *args):
        return self.poll.unregister(*args)

    def poll(self, *args):
        return kernel.enter_syscall(self.poll.poll, *args)


if hasattr(__select_mod__, "devpoll"):

    class devpoll(_Poll):

        def __init__(self):
            self.poll = __select_mod__.devpoll()

if hasattr(__select_mod__, "epoll"):

    class epoll(_Poll):

        def __init__(self):
            self.poll = __select_mod__.epoll()

        def close(self):
            return self.poll.close()

        def fileno(self):
            return self.poll.fileno()

        def fromfd(self, fd):
            return self.poll.fromfd(fd)

if hasattr(__select_mod__, "poll"):

    class poll(_Poll):

        def __init__(self):
            self.poll = __select_mod__.poll()

    __all__.extend(['poll'])

if hasattr(__select_mod__, "kqueue"):

    class kqueue(object):

        def __init__(self):
            self.kq = __select_mod__.kqueue()

        def fileno(self):
            return self.kq.fileno()

        def fromfd(self, fd):
            return self.kq.fromfd(fd)

        def close(self):
            return self.kq.close()

        def control(self, *args, **kwargs):
            return kernel.enter_syscall(self.kq.control, *args, **kwargs)



class SelectProxy(wrapt.ObjectProxy):

    def __init__(self):
        super(SelectProxy, self).__init__(__select_mod__)

    if hasattr(__select_mod__, "devpoll"):
        def devpoll(self):
            return devpoll()

    if hasattr(__select_mod__, "epoll"):
        def epoll(self):
            return epoll()

    if hasattr(__select_mod__, "poll"):
        def poll(self):
            return poll()

    if hasattr(__select_mod__, "kqueue"):
        def kqueue(self):
            return kqueue()

    def select(self, *args, **kwargs):
        return kernel.syscall(self.__wrapped__.select)(*args, **kwargs)
