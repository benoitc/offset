

from .mutex import Mutex
from .sema import Semaphore

class Cond(object):
    """ Cond implements a condition variable, a rendezvous point for coroutines
    waiting for or announcing the occurrence of an event.

    Each Cond has an associated Locker L (often a Mutex or RWMutex), which
    must be held when changing the condition and when calling the ``wait`` method.
    """


    def __init__(self, l):
        self.l = l
        self.m = Mutex()

        # We must be careful to make sure that when ``signal``
        # releases a semaphore, the corresponding acquire is
        # executed by a coroutine that was already waiting at
        # the time of the call to ``signal``, not one that arrived later.
        # To ensure this, we segment waiting coroutines into
        # generations punctuated by calls to ``signal``.  Each call to
        # ``signal`` begins another generation if there are no coroutines
        # left in older generations for it to wake.  Because of this
        # optimization (only begin another generation if there
        # are no older coroutines left), we only need to keep track
        # of the two most recent generations, which we call old
        # and new.

        self.old_waiters = 0 # number of waiters in old generation...
        self.old_sema = Semaphore() # ... waiting on this semaphore

        self.new_waiters = 0 # number of waiters in new generation...
        self.new_sema = Semaphore() # ... waiting on this semaphore

    def wait(self):
        """``wait`` atomically unlocks cond.l and suspends execution of the calling
        coroutine.  After later resuming execution, ``wait`` locks cond.l before
        returning.  Unlike in other systems, ``wait`` cannot return unless awoken by
        Broadcast or ``signal``.

        Because cond.l is not locked when ``wait`` first resumes, the caller typically
        cannot assume that the condition is true when ``wait`` returns.  Instead,
        the caller should ``wait`` in a loop::

            with m:
                while True:
                    if not condition():
                        cond.wait()

                    # ... handle the condition

        """

        self.m.lock()

        if self.new_sema is None:
            self.new_sema = Semaphore()

        self.new_waiters += 1
        self.m.unlock()
        self.l.unlock()
        self.new_sema.acquire()
        self.l.lock()

    def signal(self):
        """  ``signal`` wakes one coroutine waiting on cond, if there is any.

        It is allowed but not required for the caller to hold cond.l
        during the call.
        """
        self.m.lock()

        if self.old_waiters == 0 and self.new_waiters > 0:
            self.old_waiters = self.new_waiters
            self.old_sema = self.new_sema
            self.new_waiters = 0
            self.new_sema = None

        if self.old_waiters > 0:
            self.old_waiters -= 1
            self.old_sema.release()

        self.m.unlock()

    def broadcast(self):
        """  Broadcast wakes all coroutines waiting on cond.

        It is allowed but not required for the caller to hold cond.l
        during the call.
        """
        self.m.lock()

        if self.old_waiters > 0:
            for i in range(self.new_waiters):
                self.new_sema.release()
            self.new_waiters = 0
            self.new_sema = None

        self.m.unlock()
