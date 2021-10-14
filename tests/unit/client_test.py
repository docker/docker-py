import datetime
import os
import unittest

import docker
import pytest
from docker.constants import (
    DEFAULT_DOCKER_API_VERSION, DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_MAX_POOL_SIZE, IS_WINDOWS_PLATFORM
)
from docker.utils import kwargs_from_env
from unittest import mock

from . import fake_api

TEST_CERT_DIR = os.path.join(os.path.dirname(__file__), 'testdata/certs')
POOL_SIZE = 20


class ClientTest(unittest.TestCase):

    @mock.patch('docker.api.APIClient.events')
    def test_events(self, mock_func):
        since = datetime.datetime(2016, 1, 1, 0, 0)
        mock_func.return_value = fake_api.get_fake_events()[1]
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert client.events(since=since) == mock_func.return_value
        mock_func.assert_called_with(since=since)

    @mock.patch('docker.api.APIClient.info')
    def test_info(self, mock_func):
        mock_func.return_value = fake_api.get_fake_info()[1]
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert client.info() == mock_func.return_value
        mock_func.assert_called_with()

    @mock.patch('docker.api.APIClient.ping')
    def test_ping(self, mock_func):
        mock_func.return_value = True
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert client.ping() is True
        mock_func.assert_called_with()

    @mock.patch('docker.api.APIClient.version')
    def test_version(self, mock_func):
        mock_func.return_value = fake_api.get_fake_version()[1]
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert client.version() == mock_func.return_value
        mock_func.assert_called_with()

    def test_call_api_client_method(self):
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
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
        client = docker.DockerClient(
            version=DEFAULT_DOCKER_API_VERSION,
            **kwargs_from_env())

        with pytest.raises(TypeError) as cm:
            client.containers()

        s = cm.exconly()
        assert "'ContainerCollection' object is not callable" in s
        assert "docker.APIClient" in s

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='Unix Connection Pool only on Linux'
    )
    @mock.patch("docker.transport.unixconn.UnixHTTPConnectionPool")
    def test_default_pool_size_unix(self, mock_obj):
        client = docker.DockerClient(
            version=DEFAULT_DOCKER_API_VERSION
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        base_url = "{base_url}/v{version}/_ping".format(
            base_url=client.api.base_url,
            version=client.api._version
        )

        mock_obj.assert_called_once_with(base_url,
                                         "/var/run/docker.sock",
                                         60,
                                         maxsize=DEFAULT_MAX_POOL_SIZE
                                         )

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Npipe Connection Pool only on Windows'
    )
    @mock.patch("docker.transport.npipeconn.NpipeHTTPConnectionPool")
    def test_default_pool_size_win(self, mock_obj):
        client = docker.DockerClient(
            version=DEFAULT_DOCKER_API_VERSION
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        mock_obj.assert_called_once_with("//./pipe/docker_engine",
                                         60,
                                         maxsize=DEFAULT_MAX_POOL_SIZE
                                         )

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='Unix Connection Pool only on Linux'
    )
    @mock.patch("docker.transport.unixconn.UnixHTTPConnectionPool")
    def test_pool_size_unix(self, mock_obj):
        client = docker.DockerClient(
            version=DEFAULT_DOCKER_API_VERSION,
            max_pool_size=POOL_SIZE
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        base_url = "{base_url}/v{version}/_ping".format(
            base_url=client.api.base_url,
            version=client.api._version
        )

        mock_obj.assert_called_once_with(base_url,
                                         "/var/run/docker.sock",
                                         60,
                                         maxsize=POOL_SIZE
                                         )

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Npipe Connection Pool only on Windows'
    )
    @mock.patch("docker.transport.npipeconn.NpipeHTTPConnectionPool")
    def test_pool_size_win(self, mock_obj):
        client = docker.DockerClient(
            version=DEFAULT_DOCKER_API_VERSION,
            max_pool_size=POOL_SIZE
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        mock_obj.assert_called_once_with("//./pipe/docker_engine",
                                         60,
                                         maxsize=POOL_SIZE
                                         )


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
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert client.api.base_url == "https://192.168.59.103:2376"

    def test_from_env_with_version(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='1')
        client = docker.from_env(version='2.32')
        assert client.api.base_url == "https://192.168.59.103:2376"
        assert client.api._version == '2.32'

    def test_from_env_without_version_uses_default(self):
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)

        assert client.api._version == DEFAULT_DOCKER_API_VERSION

    def test_from_env_without_timeout_uses_default(self):
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)

        assert client.api.timeout == DEFAULT_TIMEOUT_SECONDS

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='Unix Connection Pool only on Linux'
    )
    @mock.patch("docker.transport.unixconn.UnixHTTPConnectionPool")
    def test_default_pool_size_from_env_unix(self, mock_obj):
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        base_url = "{base_url}/v{version}/_ping".format(
            base_url=client.api.base_url,
            version=client.api._version
        )

        mock_obj.assert_called_once_with(base_url,
                                         "/var/run/docker.sock",
                                         60,
                                         maxsize=DEFAULT_MAX_POOL_SIZE
                                         )

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Npipe Connection Pool only on Windows'
    )
    @mock.patch("docker.transport.npipeconn.NpipeHTTPConnectionPool")
    def test_default_pool_size_from_env_win(self, mock_obj):
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        mock_obj.assert_called_once_with("//./pipe/docker_engine",
                                         60,
                                         maxsize=DEFAULT_MAX_POOL_SIZE
                                         )

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='Unix Connection Pool only on Linux'
    )
    @mock.patch("docker.transport.unixconn.UnixHTTPConnectionPool")
    def test_pool_size_from_env_unix(self, mock_obj):
        client = docker.from_env(
            version=DEFAULT_DOCKER_API_VERSION,
            max_pool_size=POOL_SIZE
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        base_url = "{base_url}/v{version}/_ping".format(
            base_url=client.api.base_url,
            version=client.api._version
        )

        mock_obj.assert_called_once_with(base_url,
                                         "/var/run/docker.sock",
                                         60,
                                         maxsize=POOL_SIZE
                                         )

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Npipe Connection Pool only on Windows'
    )
    @mock.patch("docker.transport.npipeconn.NpipeHTTPConnectionPool")
    def test_pool_size_from_env_win(self, mock_obj):
        client = docker.from_env(
            version=DEFAULT_DOCKER_API_VERSION,
            max_pool_size=POOL_SIZE
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        mock_obj.assert_called_once_with("//./pipe/docker_engine",
                                         60,
                                         maxsize=POOL_SIZE
                                         )
