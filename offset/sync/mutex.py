# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .atomic import ffi, lib
from .sema import Semaphore

MUTEX_LOCKED = 1
MUTEX_WOKEN = 2
MUTEX_WAITER_SHIFT = 2


class Mutex(object):
    """  A Mutex is a mutual exclusion lock. """

    def __init__(self):
        self.state =  ffi.new('long *', 0)
        self.sema = Semaphore(0)


    def lock(self):
        """ locks the coroutine """

        if lib.long_bool_compare_and_swap(self.state, 0, 1):
            return

        awoke = False
        while True:
            old = self.state[0]
            new = old | MUTEX_LOCKED

            if old & MUTEX_LOCKED:
                new = old + 1<<MUTEX_WAITER_SHIFT

            if awoke:
                new &= ~(1<<MUTEX_WOKEN)

            if lib.long_bool_compare_and_swap(self.state, old, new):
                if old & MUTEX_LOCKED == 0:
                    break

                self.sema.acquire()
                awoke = True

    __enter__ = lock

    def unlock(self):
        new = lib.long_add_and_fetch(self.state, -MUTEX_LOCKED)
        if (new + MUTEX_LOCKED) & MUTEX_LOCKED == 0:
            raise RuntimeError("sync: unlock of unlocked mutex")

        old = new
        while True:
            if (old >> MUTEX_WAITER_SHIFT == 0
                    or old & (MUTEX_LOCKED | MUTEX_WOKEN) != 0):
                return

            new = (old - 1 << MUTEX_WAITER_SHIFT) | MUTEX_WOKEN
            if lib.long_bool_compare_and_swap(self.state, old, new):
                self.sema.release()
                return
            old = self.state[0]

    def __exit__(self, t, v, tb):
        self.unlock()
