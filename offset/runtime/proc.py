from concurrent import futures
from collections import deque
import functools
import multiprocessing
import os
import threading

import fibers

_tls = threading.local()

try:
    DEFAULT_MAX_THREADS = multiprocessing.cpu_count()
except NotImplementedError:
    DEFAULT_MAX_THREADS = 2


def _proc_getcurrent():
    try:
        return _tls.current_proc
    except AttributeError:
        return _proc_getmain()

def _proc_getmain():
    try:
        return _tls.main_proc
    except AttributeError:
        _tls.main_proc = MainProc()
        return _tls.main_proc

class Proc(object):

    def __init__(self, func, args, kwargs):

        def _run():
            _tls.current_proc = self
            self._is_started = 1
            return func(*args, **kwargs)

        self.fiber = fibers.Fiber(_run)
        self.waiting = False
        self.sleeping = False
        self._is_started = 0

    def switch(self):
        current = _proc_getcurrent()
        try:
            self.fiber.switch()
        finally:
            _tls.current_proc = current

    def throw(self, *args):
        current = _proc_getcurrent()
        try:
            self.fiber.throw(*args)
        finally:
            _tls.current_proc = current

    def is_alive(self):
        return self.started < 0 or self.fiber.is_alive()

class MainProc(Proc):

    def __init__(self):
        self._is_started = -1
        self.fiber = fibers.current()


currproc = _proc_getcurrent

def _gwrap(sched, func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        finally:
            sched.removeg()
    return _wrapper


class Runtime(object):

    def __init__(self):
        self.runq = deque()
        self.sleeping = {}
        self._run_calls = []
        self._last_task = MainProc()

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
        g = Proc(wrapped, args, kwargs)
        # add the coroutine at the end of the runq
        self.runq.append(g)

        return g

    def removeg(self, g=None):
        # get the current proc
        g = g or currproc()
        # remove it from the run queue
        try:
            self.runq.remove(g)
        except:
            pass

    def park(self, g=None):
        g = g or currproc()
        g.sleeping = True
        try:
            self.runq.remove(g)
        except ValueError:
            pass
        self.schedule()

    def ready(self, g):
        if not g.sleeping:
            raise RuntimeError("bad goroutine status")

        g.sleeping = False
        self.runq.append(g)

    def schedule(self):
        gcurrent = currproc()

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

            self._last_task = gnext
            if gnext != gcurrent:
                gnext.switch()

            if gcurrent is self._last_task:
                return

    def run(self):
        self._run_calls.append(currproc())
        self.schedule()

    def enter_syscall(self, fn, *args, **kwargs):
        # get current coroutine
        gt = currproc()
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

        # append to the run queue
        self.ready(g)


runtime = Runtime()
run = runtime.run
newproc = runtime.newproc
gosched = runtime.schedule

def maintask(func):
    runtime.newproc(func)
    return func


def go(func, *args, **kwargs):
    """ starts the execution of a function call as an independent goroutine,
    within the same address space. """

    # add the function to scheduler. if the schedule is on anoter process the
    # function will be sent to it using a pipe
    runtime.newproc(func, *args, **kwargs)
