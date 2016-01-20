import errno
import os
import os.path
import select
import shutil
import struct
import tarfile
import tempfile
import unittest

import docker
import six

BUSYBOX = 'busybox:buildroot-2014.02'
EXEC_DRIVER = []


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


def exec_driver_is_native():
    global EXEC_DRIVER
    if not EXEC_DRIVER:
        c = docker_client()
        EXEC_DRIVER = c.info()['ExecutionDriver']
        c.close()
    return EXEC_DRIVER.startswith('native')


def docker_client(**kwargs):
    return docker.Client(**docker_client_kwargs(**kwargs))


def docker_client_kwargs(**kwargs):
    client_kwargs = docker.utils.kwargs_from_env(assert_hostname=False)
    client_kwargs.update(kwargs)
    return client_kwargs


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
            assert False, "Failed trying to read in the dataz"
        data += next_data
    return data


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []
    tmp_folders = []
    tmp_volumes = []

    def setUp(self):
        if six.PY2:
            self.assertRegex = self.assertRegexpMatches
            self.assertCountEqual = self.assertItemsEqual
        self.client = docker_client(timeout=60)
        self.tmp_imgs = []
        self.tmp_containers = []
        self.tmp_folders = []
        self.tmp_volumes = []
        self.tmp_networks = []

    def tearDown(self):
        for img in self.tmp_imgs:
            try:
                self.client.remove_image(img)
            except docker.errors.APIError:
                pass
        for container in self.tmp_containers:
            try:
                self.client.stop(container, timeout=1)
                self.client.remove_container(container)
            except docker.errors.APIError:
                pass
        for network in self.tmp_networks:
            try:
                self.client.remove_network(network)
            except docker.errors.APIError:
                pass
        for folder in self.tmp_folders:
            shutil.rmtree(folder)

        for volume in self.tmp_volumes:
            try:
                self.client.remove_volume(volume)
            except docker.errors.APIError:
                pass

        self.client.close()

    def run_container(self, *args, **kwargs):
        container = self.client.create_container(*args, **kwargs)
        self.tmp_containers.append(container)
        self.client.start(container)
        exitcode = self.client.wait(container)

        if exitcode != 0:
            output = self.client.logs(container)
            raise Exception(
                "Container exited with code {}:\n{}"
                .format(exitcode, output))

        return container

    def create_and_start(self, image='busybox', command='top', **kwargs):
        container = self.client.create_container(
            image=image, command=command, **kwargs)
        self.tmp_containers.append(container)
        self.client.start(container)
        return container

    def execute(self, container, cmd, exit_code=0, **kwargs):
        exc = self.client.exec_create(container, cmd, **kwargs)
        output = self.client.exec_start(exc)
        actual_exit_code = self.client.exec_inspect(exc)['ExitCode']
        msg = "Expected `{}` to exit with code {} but returned {}:\n{}".format(
            " ".join(cmd), exit_code, actual_exit_code, output)
        assert actual_exit_code == exit_code, msg
