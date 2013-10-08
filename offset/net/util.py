# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from ..sync import Mutex
from ..sync.atomic import AtomicLong
from ..time import nano

def fd_(fd):
    if hasattr(fd, "fileno"):
        return int(fd.fileno())
    return fd

class Deadline(Mutex):

    def __init__(self):
        self.val = 0

    def expired(self):
        t = self.value()
        return t > 0 and nano() >= t

    def value(self):
        self.lock()
        v = self.val
        self.unlock()
        return v

    def set(self, v):
        self.lock()
        self.val = v
        self.unlock()

    def settime(self, t=None):
        self.val = t or nano()
