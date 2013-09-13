# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.

def fd_(fd):
    if hasattr(fd, "fileno"):
        return int(fd.fileno())
    return fd
