# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .core.util import nanotime, from_nanotime
from .core import timer
from .core.chan import makechan, select


NANOSECOND = 1
MICROSECOND = 1000 * NANOSECOND
MILLISECOND = 1000 * MICROSECOND
SECOND = 1000 * MILLISECOND
MINUTE = 60 * SECOND
HOUR = 60 * MINUTE

nano = nanotime
sleep = timer.sleep

def _sendtime(now, t, c):
    select(c.if_send(from_nanotime(now)))

class Timer(object):
    """ The Timer instance represents a single event.
    When the timer expires, the current time will be sent on c """

    def __init__(self, interval):
        self.c = makechan(1)
        self.t = timer.Timer(_sendtime, interval, args=(self.c,))
        self.t.start()

    def reset(self, interval):
        """ reset the timer interval """
        w = nanotime() + interval
        self.t.stop()
        self.t.when = w
        self.t.start()

def After(interval):
    """ After waits for the duration to elapse and then sends the current time
    on the returned channel.
    It is equivalent to Timer(interval).c
    """

    return Timer(interval).c

def AfterFunc(interval, func, args=None, kwargs=None):
    """ AfterFunc waits for the duration to elapse and then calls f in its own
    goroutine. It returns a Timer that can be used to cancel the call using its
    Stop method. """

    t = timer.Timer(func, interval, args=args, kwargs=kwargs)
    t.start()
    return t


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
        self.t = timer.Timer(_sendtime, interval, interval, args=(self.c,))
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
