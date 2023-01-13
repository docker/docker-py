import os
import shutil
import unittest

import pytest

import docker
from .. import helpers
from docker.utils import kwargs_from_env

TEST_IMG = 'alpine:3.10'
TEST_API_VERSION = os.environ.get('DOCKER_TEST_API_VERSION')


class BaseIntegrationTest(unittest.TestCase):
    """
    A base class for integration test cases. It cleans up the Docker server
    after itself.
    """

    def setUp(self):
        self.tmp_imgs = []
        self.tmp_containers = []
        self.tmp_folders = []
        self.tmp_volumes = []
        self.tmp_networks = []
        self.tmp_plugins = []
        self.tmp_secrets = []
        self.tmp_configs = []

    def tearDown(self):
        client = docker.from_env(version=TEST_API_VERSION, use_ssh_client=True)
        try:
            for img in self.tmp_imgs:
                try:
                    client.api.remove_image(img)
                except docker.errors.APIError:
                    pass
            for container in self.tmp_containers:
                try:
                    client.api.remove_container(container, force=True, v=True)
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

            for secret in self.tmp_secrets:
                try:
                    client.api.remove_secret(secret)
                except docker.errors.APIError:
                    pass

            for config in self.tmp_configs:
                try:
                    client.api.remove_config(config)
                except docker.errors.APIError:
                    pass

            for folder in self.tmp_folders:
                shutil.rmtree(folder)
        finally:
            client.close()


@pytest.mark.skipif(not os.environ.get('DOCKER_HOST', '').startswith('ssh://'),
                    reason='DOCKER_HOST is not an SSH target')
class BaseAPIIntegrationTest(BaseIntegrationTest):
    """
    A test case for `APIClient` integration tests. It sets up an `APIClient`
    as `self.client`.
    """
    @classmethod
    def setUpClass(cls):
        cls.client = cls.get_client_instance()
        cls.client.pull(TEST_IMG)

    def tearDown(self):
        super().tearDown()
        self.client.close()

    @staticmethod
    def get_client_instance():
        return docker.APIClient(
            version=TEST_API_VERSION,
            timeout=60,
            use_ssh_client=True,
            **kwargs_from_env()
        )

    @staticmethod
    def _init_swarm(client, **kwargs):
        return client.init_swarm(
            '127.0.0.1', listen_addr=helpers.swarm_listen_addr(), **kwargs
        )

    def run_container(self, *args, **kwargs):
        container = self.client.create_container(*args, **kwargs)
        self.tmp_containers.append(container)
        self.client.start(container)
        exitcode = self.client.wait(container)['StatusCode']

        if exitcode != 0:
            output = self.client.logs(container)
            raise Exception(
                "Container exited with code {}:\n{}"
                .format(exitcode, output))

        return container

    def create_and_start(self, image=TEST_IMG, command='top', **kwargs):
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
        return self._init_swarm(self.client, **kwargs)
