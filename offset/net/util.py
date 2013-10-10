# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from ..sync import Mutex
from ..sync.atomic import AtomicLong
from ..syscall import socket
from ..time import nano

def fd_(fd):
    if hasattr(fd, "fileno"):
        return int(fd.fileno())
    return fd


class Deadline(object):

    def __init__(self):
        self.m = Mutex()
        self.val = 0

    def expired(self):
        t = self.value()
        return t > 0 and nano() >= t

    def value(self):
        with self.m:
            v = self.val

        return v

    def set(self, v):
        with self.m:
            self.val = v

    def settime(self, t=None):
        self.set(t or nano())


def is_ipv6(addr):
    try:
        socket.inet_pton(socket.AF_INET6, addr)
    except socket.error:  # not a valid address
        return False
    except ValueError: # ipv6 not supported on this platform
        return False
    return True
