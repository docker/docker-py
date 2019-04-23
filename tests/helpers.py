import functools
import os
import os.path
import random
import re
import socket
import tarfile
import tempfile
import time

import docker
import paramiko
import pytest
import six


def make_tree(dirs, files):
    base = tempfile.mkdtemp()

    for path in dirs:
        os.makedirs(os.path.join(base, path))

    for path in files:
        with open(os.path.join(base, path), 'w') as f:
            f.write("content")

    return base


def simple_tar(path):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)

    abs_path = os.path.abspath(path)
    t.add(abs_path, arcname=os.path.basename(path), recursive=False)

    t.close()
    f.seek(0)
    return f


def untar_file(tardata, filename):
    with tarfile.open(mode='r', fileobj=tardata) as t:
        f = t.extractfile(filename)
        result = f.read()
        f.close()
    return result


def requires_api_version(version):
    test_version = os.environ.get(
        'DOCKER_TEST_API_VERSION', docker.constants.DEFAULT_DOCKER_API_VERSION
    )

    return pytest.mark.skipif(
        docker.utils.version_lt(test_version, version),
        reason="API version is too low (< {0})".format(version)
    )


def requires_experimental(until=None):
    test_version = os.environ.get(
        'DOCKER_TEST_API_VERSION', docker.constants.DEFAULT_DOCKER_API_VERSION
    )

    def req_exp(f):
        @functools.wraps(f)
        def wrapped(self, *args, **kwargs):
            if not self.client.info()['ExperimentalBuild']:
                pytest.skip('Feature requires Docker Engine experimental mode')
            return f(self, *args, **kwargs)

        if until and docker.utils.version_gte(test_version, until):
            return f
        return wrapped

    return req_exp


def wait_on_condition(condition, delay=0.1, timeout=40):
    start_time = time.time()
    while not condition():
        if time.time() - start_time > timeout:
            raise AssertionError("Timeout: %s" % condition)
        time.sleep(delay)


def random_name():
    return u'dockerpytest_{0:x}'.format(random.getrandbits(64))


def force_leave_swarm(client):
    """Actually force leave a Swarm. There seems to be a bug in Swarm that
    occasionally throws "context deadline exceeded" errors when leaving."""
    while True:
        try:
            if isinstance(client, docker.DockerClient):
                return client.swarm.leave(force=True)
            return client.leave_swarm(force=True)  # elif APIClient
        except docker.errors.APIError as e:
            if e.explanation == "context deadline exceeded":
                continue
            else:
                return


def swarm_listen_addr():
    return '0.0.0.0:{0}'.format(random.randrange(10000, 25000))


def assert_cat_socket_detached_with_keys(sock, inputs):
    if six.PY3 and hasattr(sock, '_sock'):
        sock = sock._sock

    for i in inputs:
        sock.sendall(i)
        time.sleep(0.5)

    # If we're using a Unix socket, the sock.send call will fail with a
    # BrokenPipeError ; INET sockets will just stop receiving / sending data
    # but will not raise an error
    if isinstance(sock, paramiko.Channel):
        with pytest.raises(OSError):
            sock.sendall(b'make sure the socket is closed\n')
    else:
        if getattr(sock, 'family', -9) == getattr(socket, 'AF_UNIX', -1):
            # We do not want to use pytest.raises here because future versions
            # of the daemon no longer cause this to raise an error.
            try:
                sock.sendall(b'make sure the socket is closed\n')
            except socket.error:
                return

        sock.sendall(b"make sure the socket is closed\n")
        data = sock.recv(128)
        # New in 18.06: error message is broadcast over the socket when reading
        # after detach
        assert data == b'' or data.startswith(
            b'exec attach failed: error on attach stdin: read escape sequence'
        )


def ctrl_with(char):
    if re.match('[a-z]', char):
        return chr(ord(char) - ord('a') + 1).encode('ascii')
    else:
        raise(Exception('char must be [a-z]'))
