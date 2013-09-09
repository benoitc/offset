# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import go, run, maintask, makechan
from offset.sync.mutex import Mutex
from offset.sync.once import Once


class One(object):

    def __init__(self):
        self.o = 0

    def incr(self):
        self.o += 1

    def __eq__(self, other):
        return self.o == other

    def __ne__(self, other):
        return not self.o == other


def test_Mutex():

    def hammer_mutex(m, loops, cdone):
        for i in range(loops):
            m.lock()
            m.unlock()

        cdone.send(True)

    @maintask
    def main():
        m = Mutex()
        c = makechan()
        for i in range(10):
            go(hammer_mutex, m, 1000, c)

        for i in range(10):
            c.recv()

    run()


def test_Once():

    def f(o):
        o.incr()

    def test(once, o, c):
        once.do(f)(o)
        assert o == 1
        c.send(True)

    @maintask
    def main():
        c = makechan()
        once = Once()
        o = One()
        for i in range(10):
            go(test, once, o, c)

        for i in range(10):
            c.recv()

        assert o == 1

    run()
