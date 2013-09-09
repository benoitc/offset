# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import go, run, maintask, makechan
from offset.sync.mutex import Mutex


def test_mutext():

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

