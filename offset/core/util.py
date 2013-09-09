# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import fcntl
import os
import time


def nanotime(s=None):
    """ convert seconds to nanoseconds. If s is None, current time is
    returned """
    if s is not None:
        return s * 1000000000
    return time.time() * 1000000000

def from_nanotime(n):
    """ convert from nanotime to seconds """
    return n / 1.0e9

def nanosleep(n):
    time.sleep(from_nanotime(n))

def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)
