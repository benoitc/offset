# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip


from offset import makechan, go, gosched, run, maintask, select
from offset.core.chan import bomb

SHOW_STRANGE = False

from offset.util import six

def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

class Test_Channel:

    def test_simple_channel(self):
        output = []
        def print_(*args):
            output.append(args)

        def sending(channel):
            print_("sending")
            channel.send("foo")

        def receiving(channel):
            print_("receiving")
            print_(channel.recv())

        @maintask
        def main():
            ch = makechan()
            go(sending, ch)
            go(receiving, ch)

        run()

        assert output == [('sending',), ('receiving',), ('foo',)]


    def test_send_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        def counter(n, ch):
            ch.send(n)

        rlist = []


        @maintask
        def main():
            ch = makechan()
            for each in numbers:
                go(counter, each, ch)
            for each in numbers:
                rlist.append(ch.recv())

        run()

        rlist.sort()
        numbers.sort()
        assert rlist == numbers

    def test_recv_counter(self):
        import random

        numbers = list(range(20))
        random.shuffle(numbers)

        rlist = []
        def counter(n, ch):
            ch.recv()
            rlist.append(n)

        @maintask
        def main():
            ch = makechan()

            for each in numbers:
                go(counter, each, ch)

            for each in numbers:
                ch.send(None)
        run()

        numbers.sort()
        rlist.sort()
        assert rlist == numbers

    def test_bomb(self):
        try:
            1/0
        except:
            import sys
            b = bomb(*sys.exc_info())
        assert b.type is ZeroDivisionError
        if six.PY3:
            assert (str(b.value).startswith('division by zero') or
                    str(b.value).startswith('int division'))
        else:
            assert str(b.value).startswith('integer division')
        assert b.traceback is not None

    def test_send_exception(self):
        def exp_sender(chan):
            chan.send_exception(Exception, 'test')

        def exp_recv(chan):
            try:
                val = chan.recv()
            except Exception as exp:
                assert exp.__class__ is Exception
                assert str(exp) == 'test'

        @maintask
        def main():
            chan = makechan()
            go(exp_recv, chan)
            go(exp_sender, chan)
        run()


    def test_simple_pipe(self):
        def pipe(X_in, X_out):
            foo = X_in.recv()
            X_out.send(foo)

        @maintask
        def main():
            X, Y = makechan(), makechan()
            go(pipe, X, Y)

            X.send(42)
            assert Y.recv() == 42
        run()


    def test_nested_pipe(self):
        dprint('tnp ==== 1')
        def pipe(X, Y):
            dprint('tnp_P ==== 1')
            foo = X.recv()
            dprint('tnp_P ==== 2')
            Y.send(foo)
            dprint('tnp_P ==== 3')

        def nest(X, Y):
            X2, Y2 = makechan(), makechan()
            go(pipe, X2, Y2)
            dprint('tnp_N ==== 1')
            X_Val = X.recv()
            dprint('tnp_N ==== 2')
            X2.send(X_Val)
            dprint('tnp_N ==== 3')
            Y2_Val = Y2.recv()
            dprint('tnp_N ==== 4')
            Y.send(Y2_Val)
            dprint('tnp_N ==== 5')


        @maintask
        def main():
            X, Y = makechan(), makechan()
            go(nest, X, Y)
            X.send(13)
            dprint('tnp ==== 2')
            res = Y.recv()
            dprint('tnp ==== 3')
            assert res == 13
            if SHOW_STRANGE:
                raise Exception('force prints')

        run()

    def test_wait_two(self):
        """
        A tasklets/channels adaptation of the test_wait_two from the
        logic object space
        """
        def sleep(X, Y):
            dprint('twt_S ==== 1')
            value = X.recv()
            dprint('twt_S ==== 2')
            Y.send((X, value))
            dprint('twt_S ==== 3')

        def wait_two(X, Y, Ret_chan):
            Barrier = makechan()
            go(sleep, X, Barrier)
            go(sleep, Y, Barrier)
            dprint('twt_W ==== 1')
            ret = Barrier.recv()
            dprint('twt_W ==== 2')
            if ret[0] == X:
                Ret_chan.send((1, ret[1]))
            else:
                Ret_chan.send((2, ret[1]))
            dprint('twt_W ==== 3')

        @maintask
        def main():
            X, Y = makechan(), makechan()
            Ret_chan = makechan()

            go(wait_two, X, Y, Ret_chan)

            dprint('twt ==== 1')
            Y.send(42)

            dprint('twt ==== 2')
            X.send(42)
            dprint('twt ==== 3')
            value = Ret_chan.recv()
            dprint('twt ==== 4')
            assert value == (2, 42)

        run()


    def test_async_channel(self):

        @maintask
        def main():
            c = makechan(100)

            unblocked_sent = 0
            for i in range(100):
                c.send(True)
                unblocked_sent += 1

            assert unblocked_sent == 100

            unblocked_recv = []
            for i in range(100):
                unblocked_recv.append(c.recv())

            assert len(unblocked_recv) == 100

        run()

    def test_async_with_blocking_channel(self):

        def sender(c):
            unblocked_sent = 0
            for i in range(10):
                c.send(True)
                unblocked_sent += 1

            assert unblocked_sent == 10

            c.send(True)

        @maintask
        def main():
            c = makechan(10)

            go(sender, c)
            unblocked_recv = []
            for i in range(11):
                unblocked_recv.append(c.recv())


            assert len(unblocked_recv) == 11


        run()

    def test_multiple_sender(self):
        rlist = []
        sent = []

        def f(c):
            c.send("ok")

        def f1(c):
            c.send("eof")

        def f2(c):
            while True:
                data = c.recv()
                sent.append(data)
                if data == "eof":
                    return
                rlist.append(data)

        @maintask
        def main():
            c = makechan()
            go(f, c)
            go(f1, c)
            go(f2, c)

        run()

        assert rlist == ['ok']
        assert len(sent) == 2
        assert "eof" in sent


def test_select_simple():
    rlist = []
    def fibonacci(c, quit):
        x, y = 0, 1
        while True:
            ret = select(c.if_send(x), quit.if_recv())
            if ret == c.if_send(x):
                x, y = y, x+y
            elif ret == quit.if_recv():
                return

    @maintask
    def main():
        c = makechan()
        quit = makechan()
        def f():
            for i in range(10):
                rlist.append(c.recv())
            print(rlist)
            quit.send(0)

        go(f)
        fibonacci(c, quit)

    run()

    assert rlist == [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]

def test_select_buffer():
    rlist = []
    def test(c, quit):
        x = 0
        while True:
            ret = select(c.if_send(x), quit.if_recv())
            if ret == c.if_send(x):
                x = x + 1
            elif ret == quit.if_recv():
                return

    @maintask
    def main():
        c = makechan(5, label="c")
        quit = makechan(label="quit")
        def f():
            for i in range(5):
                v = c.recv()
                rlist.append(v)
            quit.send(0)

        go(f)
        test(c, quit)
    run()

    assert rlist == [0, 1, 2, 3, 4]

def test_select_buffer2():
    rlist = []

    def test(c):
        while True:
            ret = select(c.if_recv())
            if ret == c.if_recv():

                if ret.value == "QUIT":
                    break
                rlist.append(ret.value)

    @maintask
    def main():
        c = makechan(5, label="c")
        go(test, c)

        for i in range(5):
            c.send(i)

        c.send("QUIT")

    run()
    assert rlist == [0, 1, 2, 3, 4]
