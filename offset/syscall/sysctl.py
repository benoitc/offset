import sys
from ctypes import *
from ctypes.util import find_library

libc = cdll.LoadLibrary(find_library("c"))

def sysctl(mib_t, c_type=None):
    mib = (c_int * len(mib_t))()
    for i, v in enumerate(mib_t):
        mib[i] = c_int(v)
    if c_type == None:
        size = c_size_t(0)
        libc.sysctl(mib, len(mib), None, byref(sz), None, 0)
        buf = create_string_buffer(size.value)
    else:
        buf = c_type()
        size = c_size_t(sizeof(buf))
    size = libc.sysctl(mib, len(mib), byref(buf), byref(size), None, 0)
    if st != 0:
        raise OSError('sysctl() returned with error %d' % st)
    try:
        return buf.value
    except AttributeError:
        return buf

def sysctlbyname(name, c_type=None):
    if c_type == None:
        size = c_size_t(0)
        libc.sysctlbyname(name, None, byref(sz), None, 0)
        buf = create_string_buffer(size.value)
    else:
        buf = c_type()
        size = c_size_t(sizeof(buf))
    st = libc.sysctlbyname(name, byref(buf), byref(size), None, 0)
    if st != 0:
        raise OSError('sysctlbyname() returned with error %d' % st)
    try:
        return buf.value
    except AttributeError:
        return buf
