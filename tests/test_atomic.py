# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.
# copyright (c) 2013 David Reid under the MIT License.


from offset.sync.atomic import AtomicLong, ffi, lib

def test_long_add_and_fetch():
    l = ffi.new('long *', 0)
    assert lib.long_add_and_fetch(l, 1) == 1
    assert lib.long_add_and_fetch(l, 10) == 11

def test_long_sub_and_fetch():
    l = ffi.new('long *', 0)
    assert lib.long_sub_and_fetch(l, 1) == -1
    assert lib.long_sub_and_fetch(l, 10) == -11

def test_long_bool_compare_and_swap():
    l = ffi.new('long *', 0)
    assert lib.long_bool_compare_and_swap(l, 0, 10) == True
    assert lib.long_bool_compare_and_swap(l, 1, 20) == False

def test_atomiclong_repr():
    l = AtomicLong(123456789)
    assert '<AtomicLong at ' in repr(l)
    assert '123456789>' in repr(l)

def test_atomiclong_value():
    l = AtomicLong(0)
    assert l.value == 0
    l.value = 10
    assert l.value == 10

def test_atomiclong_iadd():
    l = AtomicLong(0)
    l += 10
    assert l.value == 10

def test_atomiclong_isub():
    l = AtomicLong(0)
    l -= 10
    assert l.value == -10

def test_atomiclong_eq():
    l1 = AtomicLong(0)
    l2 = AtomicLong(1)
    l3 = AtomicLong(0)
    assert l1 == 0
    assert l1 != 1
    assert not (l2 == 0)
    assert not (l2 != 1)
    assert l1 == l3
    assert not (l1 != l3)
    assert l1 != l2
    assert not (l1 == l2)

def test_atomiclong_ordering():
    l1 = AtomicLong(0)
    l2 = AtomicLong(1)
    l3 = AtomicLong(0)

    assert l1 < l2
    assert l1 <= l2
    assert l1 <= l3
    assert l2 > l1
    assert l2 >= l3
    assert l2 >= l2

    assert l1 < 1
    assert l1 <= 0
    assert l1 <= 1
    assert l1 > -1
    assert l1 >= -1
    assert l1 >= 0
