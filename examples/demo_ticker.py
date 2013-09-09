from offset import run, maintask
from offset.time import Ticker, SECOND

from offset.core.kernel import kernel

@maintask
def main():
    ticker = Ticker(0.1 * SECOND)
    for i in range(3):
        print(ticker.c.recv())
    ticker.stop()

run()
