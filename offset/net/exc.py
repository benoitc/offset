# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


class Timeout(Exception):
    """ error raised when a timeout happen """

class FdClosing(Exception):
    """ Error raised while trying to achieve an FD closing """
