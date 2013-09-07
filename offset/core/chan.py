# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
import copy
import random
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

class scase(object):
    """ select case.

    op = 0 if recv, 1 if send
    """

    def __init__(self, op, chan, elem=None):
        self.op = op
        self.ch = chan
        self.elem = elem
        self.sg = None
        self.ok = True

    def __str__(self):
        if self.op == 0:
            cas_str = "recv"
        else:
            cas_str = "send"

        return "scase:%s %s(%s)" % (str(self.ch), cas_str,
                str(self.elem))

    @classmethod
    def recv(cls, chan):
        """ case recv

        in go: ``val  <- elem``
        """
        return cls(0, chan)

    @classmethod
    def send(cls, chan, elem):
        """ case send

        in go: ``chan <- elem``
        """
        return cls(1, chan, elem=elem)

    def __eq__(self, other):
        if self.elem is not None:
            return (self.ch == other.ch and self.op == other.op
                    and self.elem == other.elem)

        return self.ch == other.ch and self.op == other.op

    def __ne__(self, other):
        if self.elem is not None:
            return not (self.ch == other.ch and self.op == other.op
                    and self.elem == other.elem)

        return not(self.ch == other.ch and self.op == other.op)

class Channel(object):

    def __init__(self, size=None, label=None):
        self.size = size or 0
        self.closed = False
        self.label = label

        self.recvq = deque() # list of receive waiters
        self.sendq = deque() # list of send waiters

        self._lock = threading.Lock()

    def __str__(self):
        if self.label is not None:
            return "<channel:%s>" % self.label
        return object.__str__(self)

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
            kernel.schedule()
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
                kernel.schedule()
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

                if mysg.elem is not None:
                    if isinstance(mysg.elem, bomb):
                        mysg.elem.raise_()

                    return mysg.elem

            try:
                sg = self.sendq.popleft()
            except IndexError:
                pass


            if sg is not None:
                gp = sg.g
                gp.param = sg
                kernel.ready(gp)
                kernel.schedule()
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
                gp.param = sg
                kernel.ready(gp)
                kernel.schedule()

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

    def if_recv(self):
        return scase.recv(self)

    def if_send(self, elem):
        return scase.send(self, elem)


def select(*cases):
    """ A select function lets a goroutine wait on multiple
    communication operations.

    A select blocks until one of its cases can run, then it
    executes that case. It chooses one at random if multiple are ready"""

    # reorder cases
    c_ordered = [(i, cas) for i, cas in enumerate(cases)]
    random.shuffle(c_ordered)
    cases = [cas for _, cas in c_ordered]

    # pass 1 - look for something already waiting
    for cas in cases:
        if cas.op == 0:
            # RECV
            sg = None
            try:
                sg = cas.ch.sendq.popleft()
            except IndexError:
                pass

            if sg is not None:
                gp = sg.g
                gp.param = None
                kernel.ready(gp)
                cas.elem = sg.elem
                # append the case to the found results
                return cas

        else:
            # SEND
            sg = None
            try:
                sg = cas.ch.recvq.popleft()
            except IndexError:
                pass

            if sg is not None:
                gp = sg.g
                sg.elem = cas.elem
                gp.param = sg
                kernel.ready(gp)
                return cas

    # pass 2 - enqueue on all channels
    g = proc.current()
    g.param = None
    for cas in cases:
        g.sleeping = True
        sg = SudoG(g, cas.elem)
        cas.sg = sg
        if cas.op == 0:
            cas.ch.recvq.append(sg)
        else:
            cas.ch.sendq.append(sg)

    kernel.park()

    sg = g.param

    # pass 3 - dequeue from unsucessful channels
    # to not iddle in them
    result = None
    for cas in cases:
        if cas.sg != sg:
            try:
                if cas.op == 0:
                    cas.ch.recvq.remove(cas.sg)
                else:
                    cas.ch.sendq.remove(cas.sg)
            except ValueError:
                pass
        else:
            result = cas

    if result.op == 0:
        result.elem = sg.elem
    return result

def makechan(size=None, label=None):
    return Channel(size=size, label=label)
