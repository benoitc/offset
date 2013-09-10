# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import go, run, maintask, makechan, select, default


from offset.sync.atomic import AtomicLong
from offset.sync.cond import Cond
from offset.sync.mutex import Mutex
from offset.sync.once import Once
from offset.sync.rwmutex import RWMutex

def test_Mutex():

    def hammer_mutex(m, loops, cdone):
        for i in range(loops):
            m.lock()
            m.unlock()

        cdone.send(True)

    @maintask
    def main():
        m = Mutex()
        c = makechan()
        for i in range(10):
            go(hammer_mutex, m, 1000, c)

        for i in range(10):
            c.recv()

    run()

def test_Mutex():

    def hammer_mutex(m, loops, cdone):
        for i in range(loops):
            m.lock()
            m.unlock()

        cdone.send(True)

    @maintask
    def main():
        m = Mutex()
        c = makechan()
        for i in range(10):
            go(hammer_mutex, m, 1000, c)

        for i in range(10):
            c.recv()

    run()

def test_Once():

    def f(o):
        o += 1

    def test(once, o, c):
        once.do(f)(o)
        assert o == 1
        c.send(True)

    @maintask
    def main():
        c = makechan()
        once = Once()
        o = AtomicLong(0)
        for i in range(10):
            go(test, once, o, c)

        for i in range(10):
            c.recv()

        assert o == 1

    run()

def test_RWMutex_concurrent_readers():

    def reader(m, clocked, cunlock, cdone):
        m.rlock()
        clocked.send(True)
        cunlock.recv()
        m.runlock()
        cdone.send(True)

    def test_readers(num):
        m = RWMutex()
        clocked = makechan()
        cunlock = makechan()
        cdone = makechan()

        for i in range(num):
            go(reader, m, clocked, cunlock, cdone)

        for i in range(num):
            clocked.recv()

        for i in range(num):
            cunlock.send(True)

        for i in range(num):
            cdone.recv()

    @maintask
    def main():
        test_readers(1)
        test_readers(3)
        test_readers(4)

    run()

def test_RWMutex():

    activity = AtomicLong(0)

    def reader(rwm, num_iterations, activity, cdone):
        print("reader")
        for i in range(num_iterations):
            rwm.rlock()
            n = activity.add(1)
            assert n >= 1 and n < 10000, "rlock %d" % n

            for i in range(100):
                continue

            activity.add(-1)
            rwm.runlock()
        cdone.send(True)

    def writer(rwm, num_iterations, activity, cdone):
        for i in range(num_iterations):
            rwm.lock()
            n = activity.add(10000)
            assert n == 10000, "wlock %d" % n
            for i in range(100):
                continue
            activity.add(-10000)
            rwm.unlock()
        cdone.send(True)

    def hammer_rwmutex(num_readers, num_iterations):
        activity = AtomicLong(0)
        rwm = RWMutex()
        cdone = makechan()

        go(writer, rwm, num_iterations, activity, cdone)

        for i in range(int(num_readers / 2)):
            go(reader, rwm, num_iterations, activity, cdone)

        go(writer, rwm, num_iterations, activity, cdone)

        for i in range(num_readers):
            go(reader, rwm, num_iterations, activity, cdone)

        for i in range(2 + num_readers):
            cdone.recv()

    @maintask
    def main():
        n = 1000
        hammer_rwmutex(1, n)
        hammer_rwmutex(3, n)
        hammer_rwmutex(10, n)

    run()

def test_RLocker():
    wl = RWMutex()
    rl = wl.RLocker()
    wlocked = makechan(1)
    rlocked = makechan(1)

    n = 10

    def test():
        for i in range(n):
            rl.lock()
            rl.lock()
            rlocked.send(True)
            wl.lock()
            wlocked.send(True)

    @maintask
    def main():
        go(test)
        for i in range(n):
            rlocked.recv()
            rl.unlock()
            ret = select(wlocked.if_recv(), default)
            assert ret != wlocked.if_recv(), "RLocker didn't read-lock it"
            rl.unlock()
            wlocked.recv()
            ret = select(rlocked.if_recv(), default)
            assert ret != rlocked.if_recv(), "RLocker didn't respect the write lock"
            wl.unlock()

    run()

def test_Cond_signal():

    def test(m, c, running, awake):
        with m:
            running.send(True)
            c.wait()
            awake.send(True)


    @maintask
    def main():
        m = Mutex()
        c = Cond(m)
        n = 2
        running = makechan(n)
        awake = makechan(n)

        for i in range(n):
            go(test, m, c, running, awake)

        for i in range(n):
            running.recv()

        while n > 0:
            ret = select(awake.if_recv(), default)
            assert ret != awake.if_recv(), "coroutine not asleep"

            m.lock()
            c.signal()
            awake.recv()
            ret = select(awake.if_recv(), default)
            assert ret != awake.if_recv(), "too many coroutines awakes"
            n -= 1
        c.signal()

    run()

def test_Cond_signal_generation():

    def test(i, m, c, running, awake):
        m.lock()
        running.send(True)
        c.wait()
        awake.send(i)
        m.unlock()

    @maintask
    def main():
        m = Mutex()
        c = Cond(m)
        n = 100
        running = makechan(n)
        awake = makechan(n)

        for i in range(n):
            go(test, i, m, c, running, awake)

            if i > 0:
                a = awake.recv()
                assert a == (i - 1), "wrong coroutine woke up: want %d, got %d" % (i-1, a)

            running.recv()
            with m:
                c.signal()

    run()

def test_Cond_broadcast():
    m = Mutex()
    c = Cond(m)
    n = 200
    running = makechan(n)
    awake = makechan(n)
    exit = False

    def test(i):
        m.lock()
        while not exit:
            running.send(i)
            c.wait()
            awake.send(i)
        m.unlock()

    @maintask
    def main():
        for i in range(n):
            go(test, i)

        for i in range(n):
            for i in range(n):
                running.recv()
            if i == n -1:
                m.lock()
                exit = True
                m.unlock()

            ret = select(awake.if_recv(), default)
            assert ret != awake.if_recv(), "coroutine not asleep"

            m.lock()
            c.broadcast()
            m.unlock()

            seen = {}
            for i in range(n):
                g = awake.recv()
                assert g not in seen, "coroutine woke up twice"
                seen[g] = True

        ret = select(running.if_recv(), default)
        assert ret != running.if_recv(), "coroutine did not exist"
        c.broadcast()

    run()


