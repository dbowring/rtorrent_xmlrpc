=========================
rtorrent xmlrpc over SCGI
=========================

A library providing the ability to communicate with rtorrent directly over SCGI using `xmlrpc.client` from the standard library.

`Originally written`_ by Roger Que (`query`_ on github), this is a port to Python 3.

-----
Usage
-----
.. highlight: python

Basic usage::

    from rtorrent_xmlrpc import SCGIServerProxy

    server = SCGIServerProxy('scgi:///var/run/rtorrent.sock')
    print('Download rate:', server.get_down_rate())

See the `examples/` directory for more examples.

.. _Originally written: https://gist.github.com/query/899683
.. _query: https://gist.github.com/query

