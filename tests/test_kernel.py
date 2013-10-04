# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from __future__ import absolute_import

import time
from py.test import skip

from offset import makechan, go, gosched, run, maintask

SHOW_STRANGE = False


def dprint(txt):
    if SHOW_STRANGE:
        print(txt)

def test_simple():
    rlist = []

    def f():
        rlist.append('f')

    def g():
        rlist.append('g')
        gosched()

    @maintask
    def main():
        rlist.append('m')
        cg = go(g)
        cf = go(f)
        gosched()
        rlist.append('m')

    run()

    assert rlist == 'm g f m'.split()

def test_run():
    output = []
    def print_(*args):
        output.append(args)

    def f(i):
        print_(i)

    go(f, 1)
    go(f, 2)
    run()

    assert output == [(1,), (2,)]


def test_run_class():
    output = []
    def print_(*args):
        output.append(args)

    class Test(object):

        def __call__(self, i):
            print_(i)

    t = Test()

    go(t, 1)
    go(t, 2)
    run()

    assert output == [(1,), (2,)]


# tests inspired from simple core.com examples

def test_construction():
    output = []
    def print_(*args):
        output.append(args)

    def aCallable(value):
        print_("aCallable:", value)

    go(aCallable, 'Inline using setup')

    run()
    assert output == [("aCallable:", 'Inline using setup')]


    del output[:]
    go(aCallable, 'Inline using ()')

    run()
    assert output == [("aCallable:", 'Inline using ()')]

def test_run():
    output = []
    def print_(*args):
        output.append(args)

    def f(i):
        print_(i)

    @maintask
    def main():
        go(f, 1)
        go(f, 2)

    run()

    assert output == [(1,), (2,)]

def test_schedule():
    output = []
    def print_(*args):
        output.append(args)

    def f(i):
        print_(i)

    go(f, 1)
    go(f, 2)
    gosched()

    assert output == [(1,), (2,)]


def test_cooperative():
    output = []
    def print_(*args):
        output.append(args)

    def Loop(i):
        for x in range(3):
            gosched()
            print_("schedule", i)

    @maintask
    def main():
        go(Loop, 1)
        go(Loop, 2)
    run()

    assert output == [('schedule', 1), ('schedule', 2),
                      ('schedule', 1), ('schedule', 2),
                      ('schedule', 1), ('schedule', 2),]
