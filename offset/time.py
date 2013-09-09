# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .core.util import nanotime, from_nanotime
from .core.timer import sleep, Timer
from .core.chan import makechan, select


NANOSECOND = 1
MICROSECOND = 1000 * NANOSECOND
MILLISECOND = 1000 * MICROSECOND
SECOND = 1000 * MILLISECOND
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

nano = nanotime
sleep = sleep

def _sendtime(now, t, c):
    select(c.if_send(from_nanotime(now)))


class Ticker(object):
    """ returns a new Ticker containing a channel that will send the
    time with a period specified by the duration argument.

    It adjusts the intervals or drops ticks to make up for slow receivers.
    The duration d must be greater than zero.
    """

    def __init__(self, interval):
        if interval < 0:
            raise ValueError("non-positive interval")

        self.c = makechan(1)

        # set the runtime timer
        self.t = Timer(_sendtime, interval, interval, args=(self.c,))
        self.t.start()

    def stop(self):
        self.c.close()
        self.t.stop()


def Tick(interval):
    """ Tick is a convenience wrapper for Ticker providing access
    to the ticking channel. Useful for clients that no need to shutdown
    the ticker """

    if interval <= 0:
        return

    return Ticker(interval).c
