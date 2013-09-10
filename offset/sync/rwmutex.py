# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .atomic import AtomicLong
from .mutex import Locker, Mutex
from .sema import Semaphore

RWMUTEX_MAX_READERS = 1 << 30

class RWMutex(object):
    """ An RWMutex is a reader/writer mutual exclusion lock.

    The lock can be held by an arbitrary number of readers of a single writer
    """

    def __init__(self):
        self.w = Mutex() # held if there are pending writers
        self.writer_sem = Semaphore() # semaphore to wait for completing readers
        self.reader_sem = Semaphore() #semaphore to wait for complering writers
        self.reader_count = AtomicLong(0) # number of pending readers
        self.reader_wait = AtomicLong(0) # number of departing readers

    def rlock(self):
        """ lock reading

        """
        if self.reader_count.add(1) < 0:
            # a writer is pending, wait for it
            self.reader_sem.acquire()

    def runlock(self):
        """ unlock reading

        it does not affect other simultaneous readers.
        """
        if self.reader_count.add(-1) < 0:
            # a writer is pending
            if self.reader_wait.add(-1) == 0:
                # the last reader unblock the writer
                self.writer_sem.release()

    def lock(self):
        """ lock for writing

        If the lock is already locked for reading or writing, it blocks until
        the lock is available. To ensure that the lock eventually becomes
        available, a blocked lock call excludes new readers from acquiring.
        """
        self.w.lock()

        r = self.reader_count.add(-RWMUTEX_MAX_READERS) + RWMUTEX_MAX_READERS
        if r != 0 and self.reader_wait.add(r) != 0:
            self.writer_sem.acquire()

    def unlock(self):
        """ unlock writing

        As with Mutexes, a locked RWMutex is not associated with a particular
        coroutine.  One coroutine may rLock (lock) an RWMutex and then arrange
        for another goroutine to rUnlock (unlock) it.
        """
        r = self.reader_count.add(RWMUTEX_MAX_READERS)
        for i in range(r):
            self.reader_sem.release()

        self.w.unlock()

    def RLocker(self):
        return RLocker(self)

class RLocker(Locker):
    """ RLocker returns a Locker instance that implements the lock and unnlock
    methods of RWMutex. """

    def __init__(self, rw):
        self.rw = rw

    def lock(self):
        return self.rw.lock()

    __enter__ = lock

    def unlock(self):
        return self.rw.unlock()

    def __exit__(self, t, v, tb):
        self.unlock()

