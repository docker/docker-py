import errno
import os
import select
import struct

import six


class SocketError(Exception):
    pass


def read_socket(socket, n=4096):
    """ Code stolen from dockerpty to read the socket """
    recoverable_errors = (errno.EINTR, errno.EDEADLK, errno.EWOULDBLOCK)

    # wait for data to become available
    select.select([socket], [], [])

    try:
        if hasattr(socket, 'recv'):
            return socket.recv(n)
        return os.read(socket.fileno(), n)
    except EnvironmentError as e:
        if e.errno not in recoverable_errors:
            raise


def next_packet_size(socket):
    """ Code stolen from dockerpty to get the next packet size """

    try:
        data = read_data(socket, 8)
    except SocketError:
        return 0

    _, actual = struct.unpack('>BxxxL', data)
    return actual


def read_data(socket, n):
    data = six.binary_type()
    while len(data) < n:
        next_data = read_socket(socket, n - len(data))
        if not next_data:
            raise SocketError("Unexpected EOF")
        data += next_data
    return data


def read_iter(socket):
    n = next_packet_size(socket)
    while n > 0:
        yield read_socket(socket, n)
        n = next_packet_size(socket)
