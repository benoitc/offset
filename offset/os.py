# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.#

from . import syscall


class File(object):

    def __init__(self, fd, name):
        self.fd = fd
        self.name = name

    def close(self):
        syscall.close(self.fd)
        self.fd = -1

    def read(self):
        return syscall.read(self.fd)


def pipe():
    syscall.ForckLock.rlock()
    p = syscall.pipe()
    syscall.closeonexec(p[0])
    syscall.closeonexec(p[1])
    syscall.ForckLock.runlock()
    return p
