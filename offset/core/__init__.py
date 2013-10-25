# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .context import Context, enter_syscall
from .kernel import run
from .chan import Channel, makechan, select, default
from .exc import PanicError, ChannelError, KernelError


def go(func, *args, **kwargs):
    """ starts the execution of a function call as an independent goroutine,
        within the same address space. """
    Context.instance().newproc(func, *args, **kwargs)

def gosched():
    """ force scheduling """
    Context.instance().schedule()

def maintask(func):
    Context.instance().newproc(func)
    return func

def syscall(func):
    """ wrap a function to handle its result asynchronously

    This function is useful when you don't want to block the scheduler
    and execute the other goroutine while the function is processed
    """

    ctx = Context.instance()

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        # enter the functions in syscall

        ret = ctx.enter_syscall(func, *args, **kwargs)
        return ret
    return _wrapper
