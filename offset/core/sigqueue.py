# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
import signal
import threading
import weakref


class SigQueue(object):

    def __init__(self, kernel):
        self.kernel = kernel
        self.waiters = {}
        self.queue = deque()
        self.lock = threading.Lock()

    def signal_enable(self, sig, handler):
        with self.lock:
            if sig not in self.waiters:
                self.waiters[sig] = set()
                signal.signal(sig, self.signal_recv)

            ref = weakref.ref(handler)
            self.waiters[sig].add(handler)

    def signal_disable(self, sig, handler):
        with self.lock:
            if sig not in self.waiters:
                return

            try:
                self.waiters[sig].remove(handler)
            except KeyError:
                pass

    def signal_recv(self, sig, frame):
        self.queue.append(sig)

        # process signals
        ssig = self.queue.popleft()

        # send the signal to waiters
        self.kernel.enter_syscall(self.signal_send, ssig)

    def signal_send(self, ssig):
        with self.lock:
            if not ssig in self.waiters:
                return

            # get waiters
            waiters = self.waiters[ssig]
            if len(waiters) == 0:
                return

        for waiter in waiters:
            # the waiter has been garbage collected, remove it from the
            # set.
            if waiter is None:
                with self._lock:
                    try:
                        self.waiters[ssig].remove(waiter)
                    except KeyError:
                        pass
                continue

            try:
                waiter(ssig)
            except:
                pass
