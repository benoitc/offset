
from offset import go, run, maintask, makechan
from offset.time import (SECOND, sleep, Ticker, Tick, nanotime, Timer, After,
        AfterFunc)

DELTA0 = 0.06 * SECOND
DELTA = 0.06 * SECOND


def test_sleep():
    @maintask
    def main():
        PERIOD = 0.1 * SECOND

        start = nanotime()
        sleep(PERIOD)
        diff = nanotime() - start
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()

def test_Ticker():
    rlist = []

    @maintask
    def main():
        ticker = Ticker(0.1 * SECOND)
        for i in range(3):
            rlist.append(ticker.c.recv())

        ticker.stop()

    run()

    assert len(rlist) == 3

def test_Tick():
    rlist = []

    @maintask
    def main():
        ticker_chan = Tick(0.1 * SECOND)
        for i in range(3):
            rlist.append(ticker_chan.recv())

    run()

    assert len(rlist) == 3


def test_Timer():
    rlist = []

    @maintask
    def main():
        PERIOD = 0.1 * SECOND
        now = nanotime()
        t = Timer(PERIOD)
        rlist.append(t.c.recv())

        diff = nanotime() - rlist[0]
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()

def test_Timer_reset():
    rlist = []

    @maintask
    def main():
        PERIOD = 10 * SECOND
        t = Timer(PERIOD)
        now = nanotime()
        t.reset(0.1 * SECOND)

        rlist.append(t.c.recv())

        diff = nanotime() - rlist[0]
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()


def test_After():
    rlist = []

    @maintask
    def main():
        PERIOD = 0.1 * SECOND
        now = nanotime()
        c = After(PERIOD)
        rlist.append(c.recv())

        diff = nanotime() - rlist[0]
        assert PERIOD - DELTA0 <= diff <= PERIOD + DELTA

    run()

def test_AfterFunc():
    rlist = []

    @maintask
    def main():
        i = 10
        c = makechan()

        def f():
            i -= 1
            if i >= 0:
                AfterFunc(0, f)
                sleep(1 * SECOND)
            else:
                c.send(True)

        AfterFunc(0, f)
        c.recv()

        assert i == 0

    run()
