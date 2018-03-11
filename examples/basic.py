#!/usr/bin/env python3

from rtorrent_xmlrpc import SCGIServerProxy

server = SCGIServerProxy('scgi://localhost:8000')

print('Available methods:')

for method_name in server.system.listMethods():
    print('\t', method_name, sep='')

