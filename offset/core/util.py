# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

import multiprocessing
import os
import time


def getmaxthreads():
    if 'OFFSET_MAX_THREADS' in os.environ:
        return int(os.environ['OFFSET_MAX_THREADS'])

    n = 0
    try:
        n = multiprocessing.cpu_count()
    except NotImplementedError:
        pass

    # use a minimum of 2 threads
    return max(n, 2)

def nanotime(s=None):
    """ convert seconds to nanoseconds. If s is None, current time is
    returned """
    if s is not None:
        return s * 1000000000
    return time.time() * 1000000000

def from_nanotime(n):
    """ convert from nanotime to seconds """
    return n / 1.0e9


# TODO: implement this function with libc nanosleep function when
# available.
def nanosleep(n):
    time.sleep(from_nanotime(n))
