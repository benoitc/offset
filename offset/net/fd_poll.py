# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

from .fd_poll_base import PollerBase
from ..syscall import select

if hasattr(select, "devpoll"):
    # solaris

    class Poller(PollerBase):
        POLL_IMPL = select.devpoll

elif hasattr(select, "poll"):
    # other posix system supporting poll
    class Poller(PollerBase):
        POLL_IMPL = select.poll
else:
    raise RuntimeError("poll is not supported")
