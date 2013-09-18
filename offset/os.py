# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.#

import errno
import os

import syscall

import atexit

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
    syscall.close_on_exec(p[0])
    syscall.close_on_exec(p[1])
    syscall.ForckLock.runlock()
    return p
