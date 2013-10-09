# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


import sys

from .fexec import ForkLock, close_on_exec, setnonblock
from . import proxy

# patch the os module
os = proxy.OsProxy()
sys.modules['offset.syscall.os'] = os

# patch the select module
select = proxy.SelectProxy()
sys.modules['offset.syscall.select'] = select

# patch the socket module
socket = proxy.SocketProxy()
sys.modules['offset.syscall.socket'] = socket
