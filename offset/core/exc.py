# -*- coding: utf-8 -
#
# This file is part of offset. See the NOTICE for more information.


class PanicError(Exception):
    """ panic error raised """

class ChannelError(Exception):
    """ excption raised on channel error """

class KernelError(Exception):
    """ unexpected error in the kernel """
