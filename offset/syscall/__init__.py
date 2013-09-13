# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import fcntl

__all__ = ["close_on_exec", "set_non_blocking"]

def close_on_exec(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFD)
    flags |= fcntl.FD_CLOEXEC
    fcntl.fcntl(fd, fcntl.F_SETFD, flags)


def set_non_blocking(fd):
    flags = fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK
    fcntl.fcntl(fd, fcntl.F_SETFL, flags)
