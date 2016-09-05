import shutil
import unittest

import docker
from docker.utils import kwargs_from_env
import six


BUSYBOX = 'busybox:buildroot-2014.02'


class BaseIntegrationTest(unittest.TestCase):
    """
    A base class for integration test cases.

    It sets up a Docker client and cleans up the Docker server after itself.
    """
    tmp_imgs = []
    tmp_containers = []
    tmp_folders = []
    tmp_volumes = []

    def setUp(self):
        if six.PY2:
            self.assertRegex = self.assertRegexpMatches
            self.assertCountEqual = self.assertItemsEqual
        self.client = docker.APIClient(timeout=60, **kwargs_from_env())
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
