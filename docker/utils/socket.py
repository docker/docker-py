import errno
import os
import select
import struct

import six

try:
    from ..transport import NpipeSocket
except ImportError:
    NpipeSocket = type(None)


class SocketError(Exception):
    pass


def read(socket, n=4096):
    """
    Reads at most n bytes from socket
    """

    recoverable_errors = (errno.EINTR, errno.EDEADLK, errno.EWOULDBLOCK)

    # wait for data to become available
    if not isinstance(socket, NpipeSocket):
        select.select([socket], [], [])

    try:
        if hasattr(socket, 'recv'):
            return socket.recv(n)
        return os.read(socket.fileno(), n)
    except EnvironmentError as e:
        if e.errno not in recoverable_errors:
            raise


def read_exactly(socket, n):
    """
    Reads exactly n bytes from socket
    Raises SocketError if there isn't enough data
    """
    data = six.binary_type()
    while len(data) < n:
        next_data = read(socket, n - len(data))
        if not next_data:
            raise SocketError("Unexpected EOF")
        data += next_data
    return data


def next_frame_size(socket):
    """
    Returns the size of the next frame of data waiting to be read from socket,
    according to the protocol defined here:

    https://docs.docker.com/engine/reference/api/docker_remote_api_v1.24/#/attach-to-a-container
    """
    try:
        data = read_exactly(socket, 8)
    except SocketError:
        return 0

    _, actual = struct.unpack('>BxxxL', data)
    return actual


def frames_iter(socket):
    """
    Returns a generator of frames read from socket
    """
    n = next_frame_size(socket)
    while n > 0:
        yield read(socket, n)
        n = next_frame_size(socket)
