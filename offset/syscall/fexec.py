# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import fcntl
import os

from ..sync import RWMutex

ForkLock = RWMutex()

def closeonexec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def setnonblock(fd, nonblocking=True):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL)
    if nonblocking:
        flags |= os.O_NONBLOCK
    else:
        flags &= ~os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)
