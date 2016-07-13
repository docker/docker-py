import errno
import os
import select
import struct

import six


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
    data = six.binary_type()
    while len(data) < 8:
        next_data = read_socket(socket, 8 - len(data))
        if not next_data:
            return 0
        data = data + next_data

    if data is None:
        return 0

    if len(data) == 8:
        _, actual = struct.unpack('>BxxxL', data)
        return actual


def read_data(socket, packet_size):
    data = six.binary_type()
    while len(data) < packet_size:
        next_data = read_socket(socket, packet_size - len(data))
        if not next_data:
            assert False, "Failed trying to read in the data"
        data += next_data
    return data


def read_iter(socket):
    n = next_packet_size(socket)
    while n > 0:
        yield read_socket(socket, n)
        n = next_packet_size(socket)
