# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


__os_mod__ = __import__("os")
__select_mod__ = __import__("select")
__socket_mod__ = __import__("socket")
_socket = __import__("socket")

import io
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


if hasattr(_socket, "SocketIO"):
    SocketIO = _socket.SocketIO
else:
    from _socketio import SocketIO

class socket(_socket.socket):
    """A subclass of _socket.socket wrapping the makefile() method and
    patching blocking calls. """

    __slots__ = ["_io_refs", "_closed"]

    _BL_SYSCALLS = ('accept', 'getpeername', 'getsockname',
            'getsockopt', 'ioctl', 'recv', 'recvfrom', 'recvmsg',
            'recvmsg_into', 'recvfrom_into', 'recv_into', 'send',
            'sendall', 'sendto', 'sendmsg', )

    def __init__(self, family=_socket.AF_INET, type=_socket.SOCK_STREAM,
            proto=0, fileno=None):
        _socket.socket.__init__(self, family, type, proto, fileno)
        self._io_refs = 0
        self._closed = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if not self._closed:
            self.close()

    def __getattr__(self, name):
        # wrap syscalls
        if name in self._BL_SYSCALLS:
            return kernel.syscall(getattr(_socket.socket, name))
        return getattr(_socket.socket, name)


    def makefile(self, mode="r", buffering=None, encoding=None,
            errors=None, newline=None):
        """makefile(...) -> an I/O stream connected to the socket

        The arguments are as for io.open() after the filename,
        except the only mode characters supported are 'r', 'w' and 'b'.
        The semantics are similar too.  (XXX refactor to share code?)
        """
        for c in mode:
            if c not in {"r", "w", "b"}:
                raise ValueError("invalid mode %r (only r, w, b allowed)")
        writing = "w" in mode
        reading = "r" in mode or not writing
        assert reading or writing
        binary = "b" in mode
        rawmode = ""
        if reading:
            rawmode += "r"
        if writing:
            rawmode += "w"
        raw = SocketIO(self, rawmode)
        self._io_refs += 1
        if buffering is None:
            buffering = -1
        if buffering < 0:
            buffering = io.DEFAULT_BUFFER_SIZE
        if buffering == 0:
            if not binary:
                raise ValueError("unbuffered streams must be binary")
            return raw
        if reading and writing:
            buffer = io.BufferedRWPair(raw, raw, buffering)
        elif reading:
            buffer = io.BufferedReader(raw, buffering)
        else:
            assert writing
            buffer = io.BufferedWriter(raw, buffering)
        if binary:
            return buffer
        text = io.TextIOWrapper(buffer, encoding, errors, newline)
        text.mode = mode
        return text

    def _decref_socketios(self):
        if self._io_refs > 0:
            self._io_refs -= 1
        if self._closed:
            self.close()

    def _real_close(self, _ss=_socket.socket):
        # This function should not reference any globals. See issue #808164.
        _ss.close(self)

    def close(self):
        # This function should not reference any globals. See issue #808164.
        self._closed = True
        if self._io_refs <= 0:
            self._real_close()

    def detach(self):
        self._closed = True
        if hasattr(_socket.socket, 'detach'):
            return super().detach()

        # python 2.7 has no detach method, fake it
        return self.fileno()


class SocketProxy(wrapt.ObjectProxy):

    def __init__(self):
        super(SocketProxy, self).__init__(__socket_mod__)

    def socket(self, *args, **kwargs):
        return socket(*args, **kwargs)

    def fromfd(self, fd, family, type, proto=0):
        if hasattr(self.__wrapped__, 'dup'):
            nfd = self.__wrapped__.dup(fd)
        else:
            nfd = __os_mod__.dup(fd)

        return socket(family, type, proto, nfd)

    if hasattr(socket, "share"):
        def fromshare(self, info):
            return socket(0, 0, 0, info)

    if hasattr(_socket, "socketpair"):
        def socketpair(self, family=None, type=__socket_mod__.SOCK_STREAM,
                proto=0):

            if family is None:
                try:
                    family = self.__wrapped__.AF_UNIX
                except NameError:
                    family = self.__wrapped__.AF_INET
            a, b = self.__wrapped__.socketpair(family, type, proto)

            if hasattr(a, 'detach'):
                a = socket(family, type, proto, a.detach())
                b = socket(family, type, proto, b.detach())
            else:
                a = socket(family, type, proto, a.fileno())
                b = socket(family, type, proto, b.fileno())

            return a, b


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
