# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from concurrent import futures
from collections import deque
import functools
import multiprocessing
import os
import sys
import threading

from .exc import KernelError, PanicError
from . import proc

# increase the recurision limit
sys.setrecursionlimit(1000000)

try:
    DEFAULT_MAX_THREADS = multiprocessing.cpu_count()
except NotImplementedError:
    DEFAULT_MAX_THREADS = 2


def _gwrap(sched, func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except proc.ProcExit:
            pass
        finally:
            sched.removeg()
    return _wrapper


class Kernel(object):

    def __init__(self):
        self.runq = deque()
        self.sleeping = {}
        self._run_calls = []
        self._last_task = proc.MainProc()

        # get the default number of threads
        if 'OFFSET_MAX_THREADS' in os.environ:
            self._max_threads = os.environ['OFFSET_MAX_THREADS']
        else:
            self._max_threads = DEFAULT_MAX_THREADS

        # initialize the thread executor pool used for background processing
        # like syscall
        self.tpool = futures.ThreadPoolExecutor(self._max_threads)

    def newproc(self, func, *args, **kwargs):
        # wrap the function so we know when it ends
        wrapped = _gwrap(self, func)
        # create the coroutine
        g = proc.Proc(wrapped, args, kwargs)
        # add the coroutine at the end of the runq
        self.runq.append(g)

        return g

    def removeg(self, g=None):
        # get the current proc
        g = g or proc.current()
        # remove it from the run queue
        try:
            self.runq.remove(g)
        except:
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
            if self.runq:
                if self.runq[0] == gcurrent:
                    self.runq.rotate(-1)

                gnext = self.runq[0]

            elif len(self.sleeping) > 0:
                # we dont't have any proc running but a future may come back.
                # just wait for the first one.
                futures.wait([fs for fs in self.sleeping], timeout=.2,
                        return_when=futures.FIRST_COMPLETED)
                continue
            elif self._run_calls:
                gnext = self._run_calls.pop()
            else:
                return

            if not gnext.is_alive():
                self.runq.popleft()
                continue

            self._last_task = gnext
            if gnext != gcurrent:
                gnext.switch()

            if gcurrent is self._last_task:
                return

    def run(self):
        self._run_calls.append(proc.current())
        self.schedule()

    def enter_syscall(self, fn, *args, **kwargs):
        # get current coroutine
        gt = proc.current()
        gt.sleeping = True

        f = self.tpool.submit(fn, *args, **kwargs)
        self.sleeping[f] = gt
        f.add_done_callback(self.exit_syscall)

        # schedule, switch to another coroutine
        self.park()

        if f.exception() is not None:
            raise f.exception()
        return f.result()

    def exit_syscall(self, f):
        # get the  goroutine associated to this syscall
        g = self.sleeping.pop(f)

        # we exited
        if f.cancelled():
            return

        if not g.is_alive():
            return

        # append to the run queue
        # we append to the left so the syscall will be handled in priority
        g.sleeping = False
        self.runq.appendleft(g)


kernel = Kernel()
run = kernel.run
newproc = kernel.newproc
gosched = kernel.schedule
enter_syscall = kernel.enter_syscall

def syscall(func):
    """ wrap a function to handle its result asynchronously

    This function is useful when you don't want to block the scheduler
    and execute the other goroutine while the function is processed
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # enter the functions in syscall
        ret = kernel.enter_syscall(func, *args, **kwargs)
        return ret
    return _wrapper

def maintask(func):
    kernel.newproc(func)
    return func

def go(func, *args, **kwargs):
    """ starts the execution of a function call as an independent goroutine,
    within the same address space. """

    # add the function to scheduler. if the schedule is on anoter process the
    # function will be sent to it using a pipe
    kernel.newproc(func, *args, **kwargs)
