# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import time

from offset import run, go, maintask
from offset.core.context import park
from offset.core import proc
from offset.core.util import nanotime
from offset.core.timer import Timer, sleep
from offset.time import SECOND

DELTA0 = 0.06 * SECOND
DELTA = 0.06 * SECOND


def _wait():
    time.sleep(0.01)


def test_simple_timer():

    def _func(now, t, rlist, g):
        rlist.append(now)
        g.ready()

    @maintask
    def main():
        rlist = []
        period = 0.1 * SECOND
        t = Timer(_func, period, args=(rlist, proc.current()))
        now = nanotime()
        t.start()
        park()
        delay = rlist[0]

        assert (now + period - DELTA0) <= delay <= (now + period + DELTA), delay

    run()


def test_multiple_timer():
    r1 = []
    def f1(now, t, g):
        r1.append(now)
        g.ready()

    r2 = []
    def f2(now, t):
        r2.append(now)

    @maintask
    def main():
        T1 = 0.4 * SECOND
        T2 = 0.1 * SECOND
        t1 = Timer(f1, T1, args=(proc.current(),))
        t2 = Timer(f2, T2)

        now = nanotime()
        t1.start()
        t2.start()

        park()

        assert r1[0] > r2[0]

        assert (now + T1 - DELTA0) <= r1[0] <= (now + T1 + DELTA), r1[0]
        assert (now + T2 - DELTA0) <= r2[0] <= (now + T2 + DELTA), r2[0]

    run()


def test_repeat():
    r = []
    def f(now, t, g):
        if len(r) == 3:
            t.stop()
            g.ready()
        else:
            r.append(now)


    @maintask
    def main():
        t = Timer(f, 0.01 * SECOND, 0.01 * SECOND, args=(proc.current(),))
        t.start()
        park()

        assert len(r) == 3
        assert r[2] > r[1]
        assert r[1] > r[0]

    run()


def test_sleep():
    @maintask
    def main():
        PERIOD = 0.1 * SECOND
        start = nanotime()
        sleep(PERIOD)
        diff = nanotime() - start
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()


def test_multiple_sleep():
    T1 = 0.4 * SECOND
    T2 = 0.1 * SECOND

    r1 = []
    def f1():
        sleep(T1)
        r1.append(nanotime())

    r2 = []
    def f2():
        sleep(T2)
        r2.append(nanotime())

    go(f1)
    go(f2)
    now = nanotime()
    run()
    assert r1[0] > r2[0]
    assert (now + T1 - DELTA0) <= r1[0] <= (now + T1 + DELTA), r1[0]
    assert (now + T2 - DELTA0) <= r2[0] <= (now + T2 + DELTA), r2[0]
