# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
import copy
import threading

from .kernel import kernel
from . import six
from . import proc

class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        six.reraise(self.type, self.value, self.traceback)


class ChannelError(Exception):
    """ excption raised on channel error """


class SudoG(object):

    def __init__(self, g, elem):
        self.g = g
        self.elem = elem

class Channel(object):

    def __init__(self, size=None):
        self.size = size or 0
        self.closed = False

        self.recvq = deque() # list of receive waiters
        self.sendq = deque() # list of send waiters

        self._lock = threading.Lock()

    def close(self):
        self.closed = True

    def open(self):
        self.closed = False

    def send(self, elem):
        g = proc.current()

        if self.closed:
            raise ChannelError("send on a closed channel")

        if self.size > 0:
            if len(self.sendq) < self.size:
                mysg = SudoG(g, elem)
                self.sendq.append(mysg)
                kernel.park()

            sg = None
            try:
                sg = self.recvq.popleft()
            except IndexError:
                return

            gp = sg.g
            sg.elem = elem
            gp.param = sg
            kernel.ready(gp)
        else:
            sg = None
            # is the someone receiving?
            try:
                sg = self.recvq.popleft()
            except IndexError:
                pass

            if sg is not None:
                # yes, add the result and activate it
                gp = sg.g
                sg.elem = elem
                gp.param = sg

                # activate the receive process
                kernel.ready(gp)
                return

            # noone is receiving, add the process to sendq and remove us from
            # the receive q
            mysg = SudoG(g, elem)
            self.sendq.append(mysg)
            kernel.park()

    def recv(self):
        sg = None
        g = proc.current()

        if self.size > 0:
            # async case
            if len(self.sendq) <= 0:
                mysg = SudoG(g, None)
                self.recvq.append(mysg)
                kernel.park()

            try:
                sg = self.sendq.popleft()
            except IndexError:
                pass

            if sg is not None:
                gp = sg.g
                gp.param = None
                kernel.ready(gp)

                if isinstance(sg.elem, bomb):
                    sg.elem.raise_()

                return sg.elem
        else:
            # is there someone sending some data

            try:
                sg = self.sendq.popleft()
            except IndexError:
                pass

            if sg is not None:
                # yes someone is sending, unblock it and return the result
                gp = sg.g
                gp.param = None
                kernel.ready(gp)

                if isinstance(sg.elem, bomb):
                    sg.elem.raise_()

                return sg.elem


            # noone is sending, we have to wait. Append the current process to
            # receiveq, remove us from the run queue and switch
            mysg = SudoG(g, None)
            self.recvq.append(mysg)
            kernel.park()

            # we are back in the process, return the current value
            if isinstance(g.param.elem, bomb):
                g.param.elem.raise_()

            return g.param.elem

    def send_exception(self, exp_type, msg):
        self.send(bomb(exp_type, exp_type(msg)))

def makechan(size=None):
    return Channel(size=size)
