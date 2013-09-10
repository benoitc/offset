
from collections import deque
import time

from .atomic import AtomicLong
from ..core.kernel import kernel
from ..core import proc


class Semaphore(object):
    """ Semaphore implementation exposed to offset

    Intended use is provide a sleep and wakeup primitive that can be used in the
    contended case of other synchronization primitives.

    Thus it targets the same goal as Linux's futex, but it has much simpler
    semantics.

    That is, don't think of these as semaphores. Think of them as a way to
    implement sleep and wakeup such that every sleep is paired with a single
    wakeup, even if, due to races, the wakeup happens before the sleep.

    See Mullender and Cox, ``Semaphores in Plan 9,''
    http://swtch.com/semaphore.pdf

    Comment and code based on the Go code:
    http://golang.org/src/pkg/runtime/sema.goc
    """

    def __init__(self, value):
        self.sema = AtomicLong(value)
        self.nwait = AtomicLong(1)
        self.waiters = deque()

    def can_acquire(self):
        if self.sema > 0:
            self.sema -= 1
            return True
        return False

    def acquire(self):
        if self.can_acquire():
            return

        t0 = 0
        releasetime = 0

        while True:
            self.nwait += 1
            self.waiters.append(proc.current())

            if self.can_acquire():
                self.nwait -= 1
                self.waiters.remove(proc.current())
                return

            kernel.park()

    __enter__ = acquire

    def release(self):
        self.sema += 1

        if self.nwait == 0:
            return

        try:
            waiter = self.waiters.pop()
        except IndexError:
            return

        self.nwait -= 1
        kernel.ready(waiter)

    def __exit__(self, t, v, tb):
        return self.release()
