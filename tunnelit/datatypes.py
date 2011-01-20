# coding=utf8

# Copyright (C) 2011 Saúl Ibarra Corretgé <saghul@gmail.com>
#

# Some code borrowed from the SIPSIMPLE SDK project (http://sipsimpleclient.com)

import socket


class IPAddress(str):
    """An IP address in quad dotted number notation"""
    def __new__(cls, value):
        if not value:
            return None
        try:
            socket.inet_aton(value)
        except socket.error:
            raise ValueError("invalid IP address: %r" % value)
        except TypeError:
            raise TypeError("value must be a string")
        return str(value)

class Port(int):
    def __new__(cls, value):
        try:
            value = int(value)
        except ValueError:
            return None
        if not (0 <= value <= 65535):
            raise ValueError("illegal port value: %s" % value)
        return value

class PortRange(object):
    """A port range in the form start:end with start and end being even numbers in the [1024, 65536] range"""
    def __init__(self, value):
        self.start, self.end = [int(p) for p in value.split(':', 1)]
        allowed = xrange(1024, 65537, 2)
        if not (self.start in allowed and self.end in allowed and self.start < self.end):
            raise ValueError("bad range: %r: ports must be even numbers in the range [1024, 65536] with start < end" % value)

