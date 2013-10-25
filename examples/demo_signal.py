# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from offset import makechan, run, maintask
from offset import os
from offset.os import signal
import sys

from offset.core.proc import current
from offset.core.kernel import kernel

@maintask
def main():
    print(current)
    c = makechan(1)
    signal.notify(c, os.SIGINT, os.SIGTERM, os.SIGQUIT)
    s = c.recv()
    print("got signal: %s" % s)
    print(kernel.runq)

run()
print("after run")
print(kernel.running)
