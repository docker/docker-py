"""Regression tests for the streaming socket/fd leak (docker/docker-py#2766).

Streaming generators returned by APIClient must close their underlying
response (and therefore the socket / file descriptor) when the consumer
stops iterating early, raises, or drops the generator. These tests assert
that contract without depending on any particular HTTP transport's
internals.
"""
import struct
from unittest import mock

from docker.api import APIClient
from docker.constants import DEFAULT_DOCKER_API_VERSION


def make_client():
    # Passing an explicit version avoids the daemon round-trip in __init__.
    return APIClient(version=DEFAULT_DOCKER_API_VERSION)


class FakeRaw:
    """Minimal stand-in for requests' raw response body."""

    def __init__(self, frames=b''):
        self._buf = frames
        self._pos = 0

    def read(self, n=-1):
        if n is None or n < 0:
            chunk = self._buf[self._pos:]
            self._pos = len(self._buf)
            return chunk
        chunk = self._buf[self._pos:self._pos + n]
        self._pos += len(chunk)
        return chunk


class FakeResponse:
    """Observable response: records whether close() was called."""

    def __init__(self, chunks=None, raw_frames=b''):
        self.status_code = 200
        self.closed = False
        self._chunks = chunks or [b'a', b'b', b'c', b'd', b'e']
        self.raw = FakeRaw(raw_frames)

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size=1, decode=False):
        yield from self._chunks

    def close(self):
        self.closed = True


def _patch_socket(client):
    """Stub the transport plumbing that digs into raw socket internals."""
    client._get_raw_response_socket = mock.Mock(return_value=mock.Mock())
    client._disable_socket_timeout = mock.Mock()


def test_stream_raw_result_closes_response_on_early_break():
    client = make_client()
    _patch_socket(client)
    resp = FakeResponse()

    gen = client._stream_raw_result(resp, 1, False)
    next(gen)          # consume a single chunk
    gen.close()        # consumer stops early (mirrors GC / break)

    assert resp.closed is True


def test_stream_raw_result_closes_response_on_exception():
    client = make_client()
    _patch_socket(client)
    resp = FakeResponse()

    gen = client._stream_raw_result(resp, 1, False)
    next(gen)
    # Inject an exception into the running generator.
    try:
        gen.throw(RuntimeError("consumer blew up"))
    except RuntimeError:
        pass

    assert resp.closed is True


def test_multiplexed_response_stream_helper_closes_on_early_break():
    client = make_client()
    _patch_socket(client)
    # One stdout frame: header (8 bytes) + 3-byte payload.
    frame = struct.pack('>BxxxL', 1, 3) + b'abc'
    resp = FakeResponse(raw_frames=frame * 5)

    gen = client._multiplexed_response_stream_helper(resp)
    next(gen)
    gen.close()

    assert resp.closed is True


def test_read_from_socket_stream_closes_response_on_early_break():
    client = make_client()
    _patch_socket(client)
    resp = FakeResponse()

    frames = [(1, b'one'), (1, b'two'), (1, b'three')]
    with mock.patch('docker.api.client.frames_iter', return_value=iter(frames)):
        gen = client._read_from_socket(resp, stream=True, tty=False)
        next(gen)
        gen.close()

    assert resp.closed is True
