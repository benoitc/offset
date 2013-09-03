import heapq
import operator
import threading
import time

from . import six

from .proc import runtime, currproc
from .util import nanotime


def _ready(now, t, g):
    runtime.ready(g)

def sleep(d):
    curr = currproc()
    curr.sleeping = True
    t = Timer(_ready, interval=d, args=(curr,))
    t.start()
    runtime.park()

class Timer(object):

    def __init__(self, callback, interval=None, period=None, args=None,
            kwargs=None):
        if not six.callable(callback):
            raise ValueError("callback must be a callable")

        self.callback = callback
        self.interval = interval
        self.period = period
        self.args = args or []
        self.kwargs = kwargs or {}
        self.when = 0
        self.active = False

    def start(self):
        global timers
        self.active = True
        self.when = nanotime() + self.interval
        add_timer(self)

    def stop(self):
        remove_timer(self)
        self.active = False

    def __lt__(self, other):
        return self.when < other.when

    __cmp__ = __lt__

class Timers(object):

    __slots__ = ['__dict__', '_lock', 'sleeping']

    __shared_state__ = dict(
            _timers = {},
            _heap = [],
            _timerproc = None
    )

    def __init__(self):
        self.__dict__ = self.__shared_state__
        self._lock = threading.RLock()
        self.sleeping = False
        self.rescheduling = False


    def add(self, t):
        with self._lock:
            self._add_timer(t)

            if self.sleeping:
                self.sleeping = False
                runtime.ready(self._timerproc)

            if self._timerproc is None or not self._timerproc.is_alive:
                self._timerproc = runtime.newproc(self.timerproc)

    def _add_timer(self, t):
        if not t.interval:
            return
        heapq.heappush(self._heap, t)


    def remove(self, t):
        with self._lock:
            try:
                del self._heap[operator.indexOf(self._heap, t)]
            except (KeyError, IndexError):
                pass

    def timerproc(self):
        while True:
            self._lock.acquire()

            while True:
                if not len(self._heap):
                    delta = -1
                    break

                t = heapq.heappop(self._heap)
                now = nanotime()
                delta = t.when - now
                if delta > 0:
                    heapq.heappush(self._heap, t)
                    break
                else:
                    # repeat ? reinsert the timer
                    if t.period is not None and t.period > 0:
                        np = nanotime(t.period)
                        t.when += np * (1 - delta/np)
                        heapq.heappush(self._heap, t)

                    # run
                    self._lock.release()
                    t.callback(now, t, *t.args, **t.kwargs)
                    self._lock.acquire()

            if delta < 0:
                self.sleeping = True
                self._lock.release()
                runtime.park()
            else:
                self._lock.release()
                runtime.schedule()

timers = Timers()
add_timer = timers.add
remove_timer = timers.remove

