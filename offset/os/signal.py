
import weakref

from ..core import default, go, gosched, select
from ..core.kernel import signal_enable, signal_disable
from ..core.sigqueue import NUMSIG
from ..sync import Mutex
from ..sync.atomic import AtomicLong
from ..syscall import signal

class Handler(object):

    def __init__(self):
        self.mask = set()

    def set(self, sig):
        self.mask.add(sig)

    def want(self, sig):
        return sig in self.mask


class Handlers(object):

    def __init__(self):
        self.m = Mutex()
        self.handlers = {}
        self.ref = {}

        # init signals
        for i in range(NUMSIG):
            self.ref[i] = 0

        self.signal_recv = AtomicLong(0)
        go(self.loop)


    def notify(self, c, *sigs):
        with self.m:
            if c not in self.handlers:
                h = Handler()
            else:
                h = self.handlers[c]

            for sig in sigs:
                h.set(sig)
                if not self.ref[sig]:
                    signal_enable(sig)

                self.ref[sig] += 1
            self.handlers[c] = h


    def stop(self, c):
        with self.m:
            if c not in self.handlers:
                return

            h = self.handlers.pop(c)
            for sig in h.mask:
                self.ref[sig] -= 1
                if self.ref[sig] == 0:
                    signal_disable(sig)


    def loop(self):
        while True:
            self.process(signal(self.signal_recv))

    def process(self, sig):
        with self.m:
            for c, h in self.handlers.items():
                if h.want(sig):
                    ret = select(c.if_send(sig))
                    if ret:
                        continue

            self.signal_recv.value = 0

_handlers = Handlers()
notify = _handlers.notify
stop = _handlers.stop
