# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
import copy
import random
import threading

from .kernel import kernel
from .exc import ChannelError
from ..util import six
from . import proc


class bomb(object):
    def __init__(self, exp_type=None, exp_value=None, exp_traceback=None):
        self.type = exp_type
        self.value = exp_value
        self.traceback = exp_traceback

    def raise_(self):
        six.reraise(self.type, self.value, self.traceback)


class SudoG(object):

    def __init__(self, g, elem):
        self.g = g
        self.elem = elem

class scase(object):
    """ select case.

    op = 0 if recv, 1 if send, -1 if default
    """

    def __init__(self, op, chan, elem=None):
        self.op = op
        self.ch = chan
        self.elem = elem
        self.sg = None
        self.ok = True
        self.value = None

    def __str__(self):
        if self.op == 0:
            cas_str = "recv"
        elif self.op == 1:
            cas_str = "send"
        else:
            cas_str = "default"

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
        if other is None:
            return

        if self.elem is not None:
            return (self.ch == other.ch and self.op == other.op
                    and self.elem == other.elem)

        return self.ch == other.ch and self.op == other.op

    def __ne__(self, other):
        if other is None:
            return

        if self.elem is not None:
            return not (self.ch == other.ch and self.op == other.op
                    and self.elem == other.elem)

        return not(self.ch == other.ch and self.op == other.op)

class CaseDefault(scase):

    def __init__(self):
        self.op = - 1
        self.chan = None
        self.elem = None
        self.ch = None
        self.value = None
        self.sg = None

default = CaseDefault()

class Channel(object):

    def __init__(self, size=None, label=None):
        self.size = size or 0

        self._buf = None
        if self.size > 0:
            self._buf = deque()

        self.closed = False
        self.label = label

        self.recvq = deque() # list of receive waiters
        self.sendq = deque() # list of send waiters

    def __str__(self):
        if self.label is not None:
            return "<channel:%s>" % self.label
        return object.__str__(self)

    def close(self):
        self.closed = True

        # release all receivers
        while True:
            try:
                sg = self.recvq.popleft()
            except IndexError:
                break

            gp = sg.g
            gp.param = None
            kernel.ready(gp)

        # release all senders
        while True:
            try:
                sg = self.sendq.popleft()
            except IndexError:
                break

            gp = sg.g
            gp.param = None
            kernel.ready(gp)

    def open(self):
        self.closed = False

    def send(self, val):
        g = proc.current()

        if self.closed:
            raise ChannelError("send on a closed channel")

        if self.size > 0:
            # the buffer is full, wait until we can fill it
            while len(self._buf) >= self.size:
                mysg = SudoG(g, None)
                self.sendq.append(mysg)
                kernel.park()

            # fill the buffer
            self._buf.append(val)

            # eventually trigger a receiver
            sg = None
            try:
                sg = self.recvq.popleft()
            except IndexError:
                return

            if sg is not None:
                gp = sg.g
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
                sg.elem = val
                gp.param = sg

                # activate the receive process
                kernel.ready(gp)
                return

            # noone is receiving, add the process to sendq and remove us from
            # the receive q
            mysg = SudoG(g, val)
            g.param = None
            self.sendq.append(mysg)
            kernel.park()

            if g.param is None:
                if not self.closed:
                    raise ChannelError("chansend: spurious wakeup")

    def recv(self):
        sg = None
        g = proc.current()

        if self.size > 0:
            while len(self._buf) <= 0:
                mysg = SudoG(g, None)
                self.recvq.append(mysg)
                kernel.park()

            val = self._buf.popleft()

            # thread safe way to recv on a buffered channel
            try:
                sg = self.sendq.popleft()
            except IndexError:
                pass

            if sg is not None:
                # yes someone is sending, unblock it and return the result
                gp = sg.g
                kernel.ready(gp)

                if sg.elem is not None:
                    self._buf.append(sg.elem)

            kernel.schedule()

            if isinstance(val, bomb):
                val.raise_()

            return val

        # sync recv
        try:
            sg = self.sendq.popleft()
        except IndexError:
            pass

        if sg is not None:
            gp = sg.g
            gp.param = sg
            kernel.ready(gp)

            if isinstance(sg.elem, bomb):
                sg.elem.raise_()

            return sg.elem

        # noone is sending, we have to wait. Append the current process to
        # receiveq, remove us from the run queue and switch
        mysg = SudoG(g, None)
        g.param = None
        self.recvq.append(mysg)
        kernel.park()

        if g.param is None:
            if not self.closed:
                raise ChannelError("chanrecv: spurious wakeup")
            return

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

    while True:
        # pass 1 - look for something already waiting
        for cas in cases:
            if cas.op == 0:
                # RECV
                if cas.ch.size > 0 and len(cas.ch._buf) > 0:
                    # buffered channel
                    cas.value = cas.ch._buf.popleft()

                    # dequeue from the sendq
                    sg = None
                    try:
                        sg = cas.ch.sendq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        kernel.ready(gp)

                    # return the case
                    return cas
                else:
                    #
                    sg = None
                    try:
                        sg = cas.ch.sendq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        gp.param = sg
                        kernel.ready(gp)
                        cas.elem = sg.elem
                        return cas

                    if cas.ch.closed:
                        return

            elif cas.op == 1:
                if cas.ch.closed:
                    return

                # SEND
                if cas.ch.size > 0 and len(cas.ch._buf) < cas.ch.size:
                    # buffered channnel, we can fill the buffer
                    cas.ch._buf.append(cas.elem)

                    # eventually trigger a receiver
                    sg = None
                    try:
                        sg = cas.ch.recvq.popleft()
                    except IndexError:
                        pass

                    if sg is not None:
                        gp = sg.g
                        kernel.ready(gp)

                    # return
                    return cas
                else:
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
            else:
                # default case
                return cas

        # pass 2 - enqueue on all channels
        g = proc.current()
        g.param = None
        g.sleeping = True
        for cas in cases:
            sg = SudoG(g, cas.elem)
            cas.sg = sg
            if cas.op == 0:
                cas.ch.recvq.append(sg)
            else:
                cas.ch.sendq.append(sg)

        # sleep until a communication happen
        kernel.park()

        sg = g.param

        # pass 3 - dequeue from unsucessful channels
        # to not iddle in them
        selected = None
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
                selected = cas

        if sg is None:
            continue

        if selected.ch.size > 0:
            raise RuntimeError("select shouldn't happen")

        if selected.op == 0:
            selected.value = sg.elem

        return selected

def makechan(size=None, label=None):
    return Channel(size=size, label=label)
