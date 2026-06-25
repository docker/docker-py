Streaming endpoints
===================

Several SDK methods can stream data from the Docker daemon, for example
``container.logs(stream=True)``, ``client.events()``, ``container.stats()``,
``container.attach(stream=True)`` and ``client.api.build()``. These return
iterators backed by an open socket to the daemon.

The SDK closes the underlying socket and file descriptor automatically when:

* the iterator is fully consumed,
* you ``break`` out of the loop early or an exception is raised,
* you call ``.close()`` on the iterator (where supported), or
* the iterator is garbage collected.

You no longer need to drain a stream to completion just to avoid leaking a file
descriptor. Consume what you need and let the iterator go out of scope:

.. code-block:: python

    for line in container.logs(stream=True):
        if done(line):
            break  # the socket is closed for you

The ``benchmarks/stream_leak.py`` script in the repository reproduces the leak
this fixed (`#2766 <https://github.com/docker/docker-py/issues/2766>`_) without
a daemon. Opening 200 streams and stopping each after a single chunk, the
pre-fix generators leak every socket, while the current code closes all of
them::

    impl       streams  sockets leaked   ESTABLISHED conns
    ------------------------------------------------------
    old            200             200                 200
    fixed          200               0                   0
