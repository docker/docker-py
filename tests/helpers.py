import os
import os.path
import shutil
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
