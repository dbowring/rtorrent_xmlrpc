#!/usr/bin/env python3

from xmlrpc.client import MultiCall

from rtorrent_xmlrpc import SCGIServerProxy


server = SCGIServerProxy('scgi://localhost:7000')

mc = MultiCall(server)
mc.get_up_rate()
mc.get_down_rate()

up_rate, down_rate = mc()

print('{} up, {} down'.format(up_rate, down_rate))

