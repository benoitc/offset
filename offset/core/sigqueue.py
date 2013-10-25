# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


from collections import deque
import copy
import signal
import threading
import weakref


NUMSIG=65

class SigQueue(object):

    def __init__(self, kernel):
        self.kernel = kernel
        self.queue = deque()
        self.receivers = []
        self.lock = threading.Lock()

        self.sigtable = {}
        for i in range(NUMSIG):
            self.sigtable[i] = 0

    def signal_enable(self, sig):
        print("enable %s" % sig)
        with self.lock:
            if not self.sigtable[sig]:
                print("register")
                signal.signal(sig, self.signal_handler)

            self.sigtable[sig] += 1


    def signal_disable(self, sig):
        print("disable")
        with self.lock:
            if self.sigtable[sig] == 0:
                return

            self.sigtable[sig] -= 1

            if self.sigtable[sig] == 0:
                signal.signal(sig, signal.SIG_DFL)

    def signal_recv(self, s):
        with self.lock:
            print("append")
            self.receivers.append(s)

    def signal_handler(self, sig, frame):
        print("got %s" % s)
        with self.lock:
            receivers = copy.copy(self.receivers)
            self.receivers = []

        for recv in receivers:
            recv.value = sig
