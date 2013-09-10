# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from ..core import PanicError

from .atomic import AtomicLong
from .mutex import Mutex
from .sema import Semaphore


class WaitGroup(object):
    """ A WaitGroup waits for a collection of goroutines to finish.
    The main goroutine calls ``add`` to set the number of goroutines to wait for.
    Then each of the goroutines  runs and calls Done when finished.  At the same
    time, ``wait`` can be used to block until all goroutines have finished.
    """

    def __init__(self):
        self.m = Mutex()
        self.counter = AtomicLong(0)
        self.waiters = AtomicLong(0)
        self.sema = Semaphore()

    def add(self, delta):
        """  Add adds delta, which may be negative, to the WaitGroup counter. If
        the counter becomes zero, all goroutines blocked on Wait are released.
        If the counter goes negative, raise an error.

        Note that calls with positive delta must happen before the call to
        ``wait``, or else ``wait`` may wait for too small a group. Typically
        this means the calls to add should execute before the statement creating
        the goroutine or other event to be waited for. See the WaitGroup example.
        """
        v = self.counter.add(delta)
        if v < 0:
            raise PanicError("sync: negative waitgroup counter")

        if v > 0 or self.waiters == 0:
            return

        with self.m:
            for i in range(self.waiters.value):
                self.sema.release()
            self.waiters = 0
            self.sema = None

    def done(self):
        """ decrement the WaitGroup counter """
        self.add(-1)

    def wait(self):
        """ blocks until the WaitGroup counter is zero. """
        if self.counter == 0:
            return

        self.m.lock()
        self.waiters += 1
        if self.counter == 0:
            self.waiters -= 1
            self.m.unlock()
            return

        if self.sema is None:
            self.sema = Semaphore()

        self.m.unlock()
        self.sema.acquire()
