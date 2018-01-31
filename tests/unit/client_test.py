import datetime
import docker
from docker.utils import kwargs_from_env
from docker.constants import (
    DEFAULT_DOCKER_API_VERSION, DEFAULT_TIMEOUT_SECONDS
)
import os
import unittest

from . import fake_api
import pytest

try:
    from unittest import mock
except ImportError:
    import mock


TEST_CERT_DIR = os.path.join(os.path.dirname(__file__), 'testdata/certs')


class ClientTest(unittest.TestCase):

    @mock.patch('docker.api.APIClient.events')
    def test_events(self, mock_func):
        since = datetime.datetime(2016, 1, 1, 0, 0)
        mock_func.return_value = fake_api.get_fake_events()[1]
        client = docker.from_env()
        assert client.events(since=since) == mock_func.return_value
        mock_func.assert_called_with(since=since)

    @mock.patch('docker.api.APIClient.info')
    def test_info(self, mock_func):
        mock_func.return_value = fake_api.get_fake_info()[1]
        client = docker.from_env()
        assert client.info() == mock_func.return_value
        mock_func.assert_called_with()

    @mock.patch('docker.api.APIClient.ping')
    def test_ping(self, mock_func):
        mock_func.return_value = True
        client = docker.from_env()
        assert client.ping() is True
        mock_func.assert_called_with()

    @mock.patch('docker.api.APIClient.version')
    def test_version(self, mock_func):
        mock_func.return_value = fake_api.get_fake_version()[1]
        client = docker.from_env()
        assert client.version() == mock_func.return_value
        mock_func.assert_called_with()

    def test_call_api_client_method(self):
        client = docker.from_env()
        with pytest.raises(AttributeError) as cm:
            client.create_container()
        s = cm.exconly()
        assert "'DockerClient' object has no attribute 'create_container'" in s
        assert "this method is now on the object APIClient" in s

        with pytest.raises(AttributeError) as cm:
            client.abcdef()
        s = cm.exconly()
        assert "'DockerClient' object has no attribute 'abcdef'" in s
        assert "this method is now on the object APIClient" not in s

    def test_call_containers(self):
        client = docker.DockerClient(**kwargs_from_env())

        with pytest.raises(TypeError) as cm:
            client.containers()

        s = cm.exconly()
        assert "'ContainerCollection' object is not callable" in s
        assert "docker.APIClient" in s


class FromEnvTest(unittest.TestCase):

    def setUp(self):
        self.os_environ = os.environ.copy()

    def tearDown(self):
        os.environ = self.os_environ

    def test_from_env(self):
        """Test that environment variables are passed through to
        utils.kwargs_from_env(). KwargsFromEnvTest tests that environment
        variables are parsed correctly."""
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='1')
        client = docker.from_env()
        assert client.api.base_url == "https://192.168.59.103:2376"

    def test_from_env_with_version(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='1')
        client = docker.from_env(version='2.32')
        assert client.api.base_url == "https://192.168.59.103:2376"
        assert client.api._version == '2.32'

    def test_from_env_without_version_uses_default(self):
        client = docker.from_env()

        assert client.api._version == DEFAULT_DOCKER_API_VERSION

    def test_from_env_without_timeout_uses_default(self):
        client = docker.from_env()

        assert client.api.timeout == DEFAULT_TIMEOUT_SECONDS
