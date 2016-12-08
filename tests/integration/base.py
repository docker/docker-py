import shutil
import unittest

import docker
from docker.utils import kwargs_from_env
import six

from .. import helpers

BUSYBOX = 'busybox:buildroot-2014.02'


class BaseIntegrationTest(unittest.TestCase):
    """
    A base class for integration test cases. It cleans up the Docker server
    after itself.
    """

    def setUp(self):
        if six.PY2:
            self.assertRegex = self.assertRegexpMatches
            self.assertCountEqual = self.assertItemsEqual
        self.tmp_imgs = []
        self.tmp_containers = []
        self.tmp_folders = []
        self.tmp_volumes = []
        self.tmp_networks = []

    def tearDown(self):
        client = docker.from_env()
        for img in self.tmp_imgs:
            try:
                client.api.remove_image(img)
            except docker.errors.APIError:
                pass
        for container in self.tmp_containers:
            try:
                client.api.remove_container(container, force=True)
            except docker.errors.APIError:
                pass
        for network in self.tmp_networks:
            try:
                client.api.remove_network(network)
            except docker.errors.APIError:
                pass
        for volume in self.tmp_volumes:
            try:
                client.api.remove_volume(volume)
            except docker.errors.APIError:
                pass

        for folder in self.tmp_folders:
            shutil.rmtree(folder)


class BaseAPIIntegrationTest(BaseIntegrationTest):
    """
    A test case for `APIClient` integration tests. It sets up an `APIClient`
    as `self.client`.
    """

    def setUp(self):
        super(BaseAPIIntegrationTest, self).setUp()
        self.client = docker.APIClient(timeout=60, **kwargs_from_env())

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

    def init_swarm(self, **kwargs):
        return self.client.init_swarm(
            'eth0', listen_addr=helpers.swarm_listen_addr(), **kwargs
        )
