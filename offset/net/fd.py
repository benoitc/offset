# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


_os = __import__('os')

import errno

from .. import os
from .. import syscall
from ..syscall import socket
from ..sync import Mutex
from ..time import sleep

from .fd_pollserver import PollDesc
from .exc import FdClosing


class NetFd(object):

    def __init__(self, sock, familly, sotype, net):
        self.sysfd = sock.fileno()
        self.familly = familly
        self.sotype = sotype
        self.net = net

        # socket object
        self.sock = sock
        #_os.close(fd)

        self.pd = PollDesc(self)

        self.closing = False
        self.isConnected = False
        self.rio = Mutex()
        self.wio = Mutex()
        self.sysmu = Mutex()
        self.sysref = 0
        self.addr = None
        self.sysfile = None

    def name(self):
        return "%s: %s -> %s" % (self.net, self.addr[0], self.addr[1])

    def setaddr(self, addr):
        self.addr = addr

    def connect(self, address):
        with self.wio:
            self.pd.prepare_write()
            while True:
                try:
                    self._sock.connect(address)
                except socket.error as e:
                    if e.args[0] == errno.EISCONN:
                        break
                    if e.args[0] not in (errno.EINPROGRESS, errno.EALREADY,
                            errno.EINTR,):
                        raise

                    self.pd.wait_write()
                    continue

                break

            self.isConnected = True

    def incref(self, closing=False):
        with self.sysmu:
            if self.closing:
                raise FdClosing()

            self.sysref += 1
            if closing:
                self.closing = True

    def decref(self):
        with self.sysmu:
            self.sysref -= 1
            if self.closing and self.sysref == 0:
                self.pd.close()

                # close the socket
                self.sock.close()
                self.sysfd = -1

    def close(self):
        self.pd.lock()
        try:
            self.incref(True)
            self.pd.evict()
        finally:
            self.pd.unlock()

        self.decref()

    def shutdown(self, how):
        self.incref()

        try:
            self.sock.shutdown(how)
        finally:
            self.decref()

    def close_read(self):
        self.shutdown(socket.SHUT_RD)

    def close_write(self):
        self.shutdown(socket.SHUT_WR)

    def read(self, n):
        with self.rio:
            self.incref()
            try:
                self.pd.prepare_read()
                while True:
                    try:
                        return self.sock.recv(n)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_read()
                            continue
                        else:
                            raise
            finally:
                self.decref()

    def readfrom(self, n, *flags):
        with self.rio:
            self.incref()
            try:
                self.pd.prepare_read()
                while True:
                    try:
                        return self.sock.recvfrom(n, **flags)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_read()
                            continue
                        else:
                            raise
            finally:
                self.decref()


    if hasattr(socket, 'recvmsg'):
        def readmsg(self, p, oob):
            with self.rio:
                self.incref()
                try:
                    self.pd.prepare_read()
                    while True:
                        try:
                            return self.sock.recvmsg(p, oob, 0)
                        except socket.error as e:
                            if e.args[0] == errno.EAGAIN:
                                self.pd.wait_read()
                                continue
                            else:
                                raise
                finally:
                    self.decref()


    def write(self, data):
        with self.wio:
            self.incref()
            try:
                self.pd.prepare_write()
                while True:
                    try:
                        return self.sock.send(data)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_write()
                            continue
                        else:
                            raise
            finally:
                self.decref()

    def writeto(self, data, addr):
        with self.wio:
            self.incref()
            try:
                self.pd.prepare_write()
                while True:
                    try:
                        return self.sock.sendto(data, addr)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_write()
                            continue
                        else:
                            raise
            finally:
                self.decref()

    if hasattr(socket, 'sendmsg'):
        def writemsg(self, p, oob, addr):
            with self.wio:
                self.incref()
                try:
                    self.pd.prepare_write()
                    while True:
                        try:
                            return self.sock.sendmsg(p, oob, 0, addr)
                        except socket.error as e:
                            if e.args[0] == errno.EAGAIN:
                                self.pd.wait_write()
                                continue
                            else:
                                raise
                finally:
                    self.decref()


    def accept(self):
        with self.rio:
            self.incref()
            try:
                self.pd.prepare_read()
                while True:
                    try:
                        fd, addr = accept(self.sock)
                    except socket.error as e:
                        if e.args[0] == errno.EAGAIN:
                            self.pd.wait_read()
                            continue
                        elif e.args[0] == errno.ECONNABORTED:
                            continue
                        else:
                            raise

                    break

                cls = self.__class__
                obj = cls(fd, self.familly, self.sotype,
                        self.net)
                obj.setaddr(addr)
                return obj
            finally:
                self.decref()

    def dup(self):
        syscall.ForkLock.rlock()
        try:
            fd = _os.dup(self.sock.fileno())
            syscall.closeonexec(fd)

        finally:
            syscall.ForkLock.runlock()

        syscall.setnonblock(fd)
        return os.File(fd, self.name())


def accept(sock):
    conn, addr = sock.accept()
    syscall.ForkLock.rlock()
    try:
        syscall.closeonexec(conn.fileno())

    finally:
        syscall.ForkLock.runlock()

    conn.setblocking(0)
    return conn, addr
