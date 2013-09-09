
from offset import go, run, maintask
from offset.time import SECOND, sleep, Ticker, Tick, nanotime

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

def test_ticker():
    rlist = []

    @maintask
    def main():
        ticker = Ticker(0.1 * SECOND)
        for i in range(3):
            rlist.append(ticker.c.recv())

        ticker.stop()

    run()

    assert len(rlist) == 3

def test_tick():
    rlist = []

    @maintask
    def main():
        ticker_chan = Tick(0.1 * SECOND)
        for i in range(3):
            rlist.append(ticker_chan.recv())

    run()

    assert len(rlist) == 3

