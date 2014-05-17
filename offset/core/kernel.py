# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from concurrent import futures
from collections import deque
import signal
import sys
import time

from .context import Context
from .sigqueue import SigQueue

# increase the recursion limit
sys.setrecursionlimit(1000000)

class Kernel(object):

    def __init__(self):

        # we have for now only one context
        self.ctx = Context.instance()

        # init signals
        self.init_signals()


        # init signal global queue used to handle all signals from the
        # app
        self.sig_queue = SigQueue(self)

    def init_signals(self):
        signal.signal(signal.SIGQUIT, self.handle_quit)
        signal.signal(signal.SIGTERM, self.handle_quit)
        signal.signal(signal.SIGINT, self.handle_quit)

    def handle_quit(self, *args):
        self.ctx.stop()

    def run(self):
        self.ctx.run()

    def signal_enable(self, sig):
        self.sig_queue.signal_enable(sig)

    def signal_disable(self, sig):
        self.sig_queue.signal_disable(sig)

    def signal_recv(self, s):
        self.sig_queue.signal_recv(s)

        def callback():
            while True:
                if s.value != 0:
                    return s.value
                time.sleep(0.05)

        return self.ctx.enter_syscall(callback)


kernel = Kernel()
run = kernel.run


signal_enable = kernel.signal_enable
signal_disable = kernel.signal_disable
signal_recv = kernel.signal_recv
