#!/usr/bin/env python
"""Demonstrate the streaming socket/fd leak from docker/docker-py#2766.

The streaming helpers in ``docker.api.client`` hand the caller a generator that
reads from a long-lived socket. Before this change, abandoning that generator
early (``break``, an exception, or simply dropping the reference) never closed
the underlying response, so the socket/fd leaked.

This script reproduces the leak without a Docker daemon, at the raw socket
level so the result does not depend on connection pooling or garbage-collection
timing. It serves an endless chunked HTTP response from a local thread, then
repeatedly:

    1. opens a streaming connection,
    2. reads a single chunk,
    3. stops the iterator early (``generator.close()``),

while holding every connection open for the whole run.

``leaky`` is a generator with no cleanup (the pre-fix behaviour). ``fixed``
wraps the same loop in ``try/finally: connection.close()`` -- the analogue of
``response.close()`` that ``APIClient._stream_raw_result`` now performs. Each
``connection.close()`` here closes exactly one socket, the same way
``requests.Response.close()`` releases the docker daemon socket.

Usage:
    python benchmarks/stream_leak.py [--iterations N]
"""
import argparse
import http.client
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import psutil


class _StreamingHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.1'  # keep-alive: socket stays open until closed

    # Stream chunks forever so the connection stays open until the client
    # closes it -- the follow=True case.
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Transfer-Encoding', 'chunked')
        self.end_headers()
        try:
            while True:
                payload = b'log line\n'
                self.wfile.write(
                    f'{len(payload):x}\r\n'.encode() + payload + b'\r\n')
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass  # client went away -- the whole point of the benchmark

    def handle(self):
        try:
            super().handle()
        except (ConnectionError, OSError):
            pass  # client closed mid-stream -- expected here

    def log_message(self, *args):
        pass  # keep the benchmark output clean


def _start_server():
    server = ThreadingHTTPServer(('127.0.0.1', 0), _StreamingHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


class Stream:
    """Minimal stand-in for a streaming docker response over a raw socket.

    ``close()`` releases the socket, mirroring ``requests.Response.close()``.
    """

    def __init__(self, host, port):
        self._conn = http.client.HTTPConnection(host, port)
        self._conn.request('GET', '/')
        self._resp = self._conn.getresponse()

    def read(self, n=16):
        return self._resp.read(n)

    def close(self):
        # Closing the response releases the socket -- the same call
        # APIClient now makes in its streaming generators' finally block.
        self._resp.close()
        self._conn.close()

    @property
    def open(self):
        # http.client moves the socket into the response object, so check the
        # response rather than conn.sock. close() sets isclosed() True.
        return not self._resp.isclosed()


def leaky(stream):
    """Pre-fix behaviour: yields chunks, never closes the socket."""
    while True:
        data = stream.read()
        if not data:
            break
        yield data


def fixed(stream):
    """Post-fix behaviour, mirroring APIClient._stream_raw_result."""
    try:
        while True:
            data = stream.read()
            if not data:
                break
            yield data
    finally:
        stream.close()


def established_to(proc, port):
    try:
        return sum(
            1 for c in proc.net_connections(kind='tcp')
            if c.raddr and c.raddr.port == port and c.status == 'ESTABLISHED'
        )
    except (psutil.AccessDenied, NotImplementedError):
        return -1


def run(make_stream, host, port, iterations, proc):
    streams = []
    generators = []
    for _ in range(iterations):
        stream = Stream(host, port)
        gen = make_stream(stream)
        next(gen)        # read a single chunk
        gen.close()      # consumer stops early -> GeneratorExit
        streams.append(stream)
        generators.append(gen)

    leaked = sum(1 for s in streams if s.open)
    established = established_to(proc, port)

    for s in streams:    # tidy up before the next run
        s.close()
    return leaked, established


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=200,
                        help='streams opened and abandoned per run')
    args = parser.parse_args()

    server = _start_server()
    host, port = server.server_address
    proc = psutil.Process()

    print(f'opening {args.iterations} streams, reading one chunk, then '
          f'stopping each early\n')
    header = (f'{"impl":<8}{"streams":>10}{"sockets leaked":>16}'
              f'{"ESTABLISHED conns":>20}')
    print(header)
    print('-' * len(header))

    results = {}
    for name, fn in (('old', leaky), ('fixed', fixed)):
        leaked, established = run(fn, host, port, args.iterations, proc)
        results[name] = leaked
        print(f'{name:<8}{args.iterations:>10}{leaked:>16}{established:>20}')

    server.shutdown()
    print()
    if results['old'] == args.iterations and results['fixed'] == 0:
        print(f'PASS: old leaks all {args.iterations} sockets on early stop; '
              f'fixed closes every one.')
    else:
        print('NOTE: compare the "sockets leaked" column for the two impls.')


if __name__ == '__main__':
    main()
