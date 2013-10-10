
import sys

from ..syscall import socket

try:
    from ..syscall.sysctl import sysctlbyname
    from ctypes import c_int
except ImportError:
    sysctlbyname = None

from .fd import NetFd
from . import util

def maxListenerBacklog():
    if sys.platform.startswith('linux'):
        try:
            f = open("/proc/sys/net/core/somaxconn")
        except OSError:
            return socket.SOMAXCONN

        try:
            n = int(f.read().split('\n')[0])
        except ValueError:
            return socket.SOMAXCONN

        if n > 1<<16-1:
		    n = 1<<16 - 1

        return n
    elif sysctlbyname is not None:
        n = 0
        if (sys.platform.startswith('darwin') or
                sys.platform.startswith('freebsd')):
            n = sysctlbyname('kern.ipc.somaxconn', c_int)
        elif sys.platform.startswith('openbsd'):
            n = sysctlbyname('kern.somaxconn', c_int)

        if n == 0:
            return socket.SOMAXCONN

        if n > 1<<16-1:
		    n = 1<<16 - 1

        return n
    else:
        return socket.SOMAXCONN

# return a bounded socket
def socket(net, addr):
    if net == "tcp" or net == "udp":
        if util.is_ipv6(addr[0]):
            family = socket.AF_INET6
        else:
            family = socket.AF_INET
    else:
        # net == "unix"
        family = socket.AF_UNIX

    if net == "udp":
        sotype = socket.socket.SOCK_DGRAM
    else:
        # net == "unix" or net == "tcp"
        sotype = socket.SOCK_STREAM


    # bind and listen the socket
    sock = socket.socket(family, sotype)
    sock.bind(addr)
    sock.listen(maxListenerBacklog())

    # return the NetFd instance
    netfd = NetFd(sock.fileno(), family, sotype, net)
    netfd.setaddr(sock.getpeername())
    return netfd
