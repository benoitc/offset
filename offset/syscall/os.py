# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


from . import util

# sys blocking calls
SYS_BLOCKING = ("chown", "fchown", "close", "dup", "dup2", "read", "pread",
    "write", "pwrite", "sendfile", "readv", "writev", "stat", "lstat",
    "truncate", "sync", "lseek", "open", "posix_fallocate",
    "posix_fadvise", "chmod", "chflags", "getcwd", )

# get os module and patch blocking functions to call syscall

util.inherit_module('os', __name__, True, SYS_BLOCKING)

del util
del SYS_BLOCKING
