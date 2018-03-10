#!/usr/bin/env python3

# rtorrent_xmlrpc
# (c) 2011 Roger Que <alerante@bellsouth.net>
# Updated for python3 by Daniel Bowring <contact@danielb.codes>
#
# Python module for interacting with rtorrent's XML-RPC interface
# directly over SCGI, instead of through an HTTP server intermediary.
# Inspired by Glenn Washburn's xmlrpc2scgi.py [1], but subclasses the
# built-in xmlrpclib classes so that it is compatible with features
# such as MultiCall objects.
#
# [1] <http://libtorrent.rakshasa.no/wiki/UtilsXmlrpc2scgi>
#
# Usage: server = SCGIServerProxy('scgi://localhost:7000/')
#        server = SCGIServerProxy('scgi:///path/to/scgi.sock')
#        print(server.system.listMethods())
#        mc = xmlrpclib.MultiCall(server)
#        mc.get_up_rate()
#        mc.get_down_rate()
#        print(mc())
#
#
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
# In addition, as a special exception, the copyright holders give
# permission to link the code of portions of this program with the
# OpenSSL library under certain conditions as described in each
# individual source file, and distribute linked combinations
# including the two.
#
# You must obey the GNU General Public License in all respects for
# all of the code used other than OpenSSL.  If you modify file(s)
# with this exception, you may extend this exception to your version
# of the file(s), but you are not obligated to do so.  If you do not
# wish to do so, delete this exception statement from your version.
# If you delete this exception statement from all source files in the
# program, then also delete it here.
#
#
#
# Portions based on Python's xmlrpclib:
#
# Copyright (c) 1999-2002 by Secret Labs AB
# Copyright (c) 1999-2002 by Fredrik Lundh
#
# By obtaining, using, and/or copying this software and/or its
# associated documentation, you agree that you have read, understood,
# and will comply with the following terms and conditions:
#
# Permission to use, copy, modify, and distribute this software and
# its associated documentation for any purpose and without fee is
# hereby granted, provided that the above copyright notice appears in
# all copies, and that both that copyright notice and this permission
# notice appear in supporting documentation, and that the name of
# Secret Labs AB or the author not be used in advertising or publicity
# pertaining to distribution of the software without specific, written
# prior permission.
#
# SECRET LABS AB AND THE AUTHOR DISCLAIMS ALL WARRANTIES WITH REGARD
# TO THIS SOFTWARE, INCLUDING ALL IMPLIED WARRANTIES OF MERCHANT-
# ABILITY AND FITNESS.  IN NO EVENT SHALL SECRET LABS AB OR THE AUTHOR
# BE LIABLE FOR ANY SPECIAL, INDIRECT OR CONSEQUENTIAL DAMAGES OR ANY
# DAMAGES WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS,
# WHETHER IN AN ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS
# ACTION, ARISING OUT OF OR IN CONNECTION WITH THE USE OR PERFORMANCE
# OF THIS SOFTWARE.

import re
import socket
import string
import collections
import xmlrpc.client



NULL = b'\x00'


class SCGITransport(xmlrpc.client.Transport):
    def encode_scgi_headers(self, content_length, **others):
        # Need to use an ordered dict because content length MUST be the first
        #  key present in the encoded headers.
        headers = collections.OrderedDict((
            (b'CONTENT_LENGTH', str(content_length).encode('utf-8')),
            (b'SCGI', b'1'),
        ))
        headers.update(others)  # Assume already bytes for keys and values

        encoded = NULL.join( k + NULL + v for k, v in headers.items() ) + NULL
        length = str(len(encoded)).encode('utf-8')
        return length + b':' + encoded


    def single_request(self, host, handler, request_body, verbose=0):
        # Add SCGI headers to the request.
        header = self.encode_scgi_headers(len(request_body))
        scgi_request = header + b',' + request_body

        sock = None

        try:
            if host:
                host, port = splitport(host)
                addrinfo = socket.getaddrinfo(host, port, socket.AF_INET,
                                              socket.SOCK_STREAM)
                sock = socket.socket(*addrinfo[0][:3])
                sock.connect(addrinfo[0][4])
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(handler)

            self.verbose = verbose

            sock.send(scgi_request)
            return self.parse_response(sock.makefile())
        finally:
            if sock:
                sock.close()

    def parse_response(self, response):
        p, u = self.getparser()

        response_body = ''
        while True:
            data = response.read(1024)
            if not data:
                break
            response_body += data

        # Remove SCGI headers from the response.
        response_header, response_body = re.split(r'\n\s*?\n', response_body,
                                                  maxsplit=1)

        if self.verbose:
            print('body:', repr(response_body))

        p.feed(response_body)
        p.close()

        return u.close()


class SCGIServerProxy(xmlrpc.client.ServerProxy):
    def __init__(self, uri, transport=None, use_datetime=False,
                 use_builtin_types=False, **kwargs):
        if transport is None:
            transport = SCGITransport(use_datetime=use_datetime,
                                      use_builtin_types=use_builtin_types)

        # Feed some junk in here, but we'll fix it afterwards
        super().__init__('http://thiswillbe/overwritten', transport=transport, **kwargs)

        # Fix the result of the junk above
        scheme, uri = splittype(uri)

        if scheme != 'scgi':
            raise IOError('unsupported XML-RPC protocol')

        # The weird names here are because name mangling. See:
        #  https://docs.python.org/3/tutorial/classes.html#private-variables
        self._ServerProxy__host, self._ServerProxy__handler = splithost(uri)

        if not self._ServerProxy__handler:
            self._ServerProxy__handler = '/'


def splittype(url):
    '''
    splittype('type:opaquestring') --> 'type', 'opaquestring'.

    If type is unknown, it will be `None`. Type will always be returned
     in lowercase.
    This functionality use to (sort of) be provided by urllib as
     `urllib.splittype` in python2, but has since been removed.
    '''
    try:
        split_at = url.index(':')
    except ValueError:
        return None, url  # Can't tell what the type is

    # Don't include the colon in either value.
    return url[:split_at].lower(), url[split_at+1:]


def splithost(url):
    '''
    splithost('//host[:port]/path') --> 'host[:port]', '/path'.

    This functionality use to (sort of) be provided by urllib as
     `urllib.splithost` in python2, but has since been removed.
    '''

    if not url.startswith('//'):
        return None, url  # Probably a relative path

    hostpath = url[2:]  # remove the '//'

    try:
        split_from = hostpath.index('/')
    except ValueError:
        return url, None  # Seems to contain host only

    # Unlike `splittype`, we want the separating character in the path
    return hostpath[:split_from], hostpath[split_from:]


def is_non_digit(character):
    return not character in string.digits

def splitport(hostport):
    '''
    splitport('host:port') --> 'host', 'port'.
    '''

    try:
        host, port = hostport.split(':', 1)  # ValueError if there is no colon
        if any(is_non_digit, port):
            raise ValueError('Port must contain only digits')
    except ValueError:
        return hostport, None

    return host, port


