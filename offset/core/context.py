# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from collections import deque
from concurrent import futures
import sys
import threading

try:
    import thread  # py2
except ImportError:
    import _thread as thread  # py3

from .exc import KernelError
from . import proc
from .util import getmaxthreads


# increase the recursion limit
sys.setrecursionlimit(1000000)


class Context(object):

    _instance_lock = threading.Lock()

    def __init__(self):
        self.runq = deque()
        self.running = deque()
        self.sleeping = {}
        self.lock = threading.Lock()
        self._thread_ident = None
        self._run_calls = []

        # initialize the thread executor pool used for background processing
        # like syscall
        self.maxthreads = getmaxthreads()
        self.tpool = futures.ThreadPoolExecutor(self.maxthreads)

    @staticmethod
    def instance():
        """Returns a global `Context` instance.
        """
        if not hasattr(Context, "_instance"):
            with Context._instance_lock:
                if not hasattr(Context, "_instance"):
                    # New instance after double check
                    Context._instance = Context()
        return Context._instance

    def newproc(self, func, *args, **kwargs):
        # wrap the function so we know when it ends
        # create the coroutine
        g = proc.Proc(self, func, args, kwargs)
        # add the coroutine at the end of the runq
        self.runq.append(g)
        # register the goroutine
        self.running.append(g)
        # return the coroutine
        return g

    def removeg(self, g=None):
        # get the current proc
        g = g or proc.current()
        # remove it from the run queue
        try:
            self.runq.remove(g)
        except ValueError:
            pass

        # unregister the goroutine
        try:
            self.running.remove(g)
        except ValueError:
            pass

    def park(self, g=None):
        g = g or proc.current()
        g.sleeping = True
        try:
            self.runq.remove(g)
        except ValueError:
            pass
        self.schedule()

    def ready(self, g):
        if not g.sleeping:
            raise KernelError("bad goroutine status")

        g.sleeping = False
        self.runq.append(g)

    def schedule(self):
        gcurrent = proc.current()

        while True:
            gnext = None
            if len(self.runq):
                if self.runq[0] == gcurrent:
                    self.runq.rotate(-1)
                gnext = self.runq[0]
            elif len(self.sleeping) > 0:
                self.wait_syscalls(0.05)
                continue
            elif self._run_calls:
                gnext = self._run_calls.pop(0)

            if not gnext:
                return

            # switch
            self._last_task = gnext
            if gnext != gcurrent:
                gnext.switch()

            if gcurrent == self._last_task:
                return

    def run(self):
        # append the run to the run calls
        self._run_calls.append(proc.current())
        # set current thread
        self._thread_ident = thread.get_ident()
        # start scheduling
        self.schedule()

    def stop(self):
        # kill all running goroutines
        while True:
            try:
                p = self.running.popleft()
            except IndexError:
                break

            p.terminate()

        # stop the pool
        self.tpool.shutdown(wait=False)

    def wait_syscalls(self, timeout):
        print("wait")
        with self.lock:
            fs = [f for f in self.sleeping]

        futures.wait(fs, timeout, return_when=futures.FIRST_COMPLETED)

    def enter_syscall(self, fn, *args, **kwargs):
        # get current coroutine
        gt = proc.current()
        gt.sleeping = True

        # init the futures
        f = self.tpool.submit(fn, *args, **kwargs)
        f.add_done_callback(self.exit_syscall)

        # add the goroutine to sleeping functions
        with self.lock:
            self.sleeping[f] = gt

        # schedule, switch to another coroutine
        self.park()

        if f.exception() is not None:
            raise f.exception()
        return f.result()

    def exit_syscall(self, f):
        # get the  goroutine associated to this syscall
        with self.lock:
            g = self.sleeping.pop(f)

        # we exited
        if f.cancelled():
            return

        if not g.is_alive():
            return

        g.sleeping = False

        # put the goroutine back at the top of the running queue
        self.runq.appendleft(g)


def park():
    g = proc.current()
    g.park()

def ready(g):
    g.ready(g)

def enter_syscall(fn, *args, **kwargs):
    ctx = Context.instance()
    return ctx.enter_syscall(fn, *args, **kwargs)
