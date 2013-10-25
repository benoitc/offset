# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import run, maintask
from offset.time import Ticker, SECOND


@maintask
def main():
    ticker = Ticker(0.1 * SECOND)
    for i in range(3):
        print(ticker.c.recv())
    ticker.stop()

run()
