import datetime
import os
import unittest
from unittest import mock

import pytest

import docker
from docker.constants import (
    DEFAULT_DOCKER_API_VERSION,
    DEFAULT_MAX_POOL_SIZE,
    DEFAULT_NPIPE,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_UNIX_SOCKET,
    IS_WINDOWS_PLATFORM,
)
from docker.utils import kwargs_from_env

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

        base_url = f"{client.api.base_url}/v{client.api._version}/_ping"
        # Extract socket path from DEFAULT_UNIX_SOCKET (remove http+unix:// prefix)
        socket_path = DEFAULT_UNIX_SOCKET.replace('http+unix://', '')

        mock_obj.assert_called_once_with(base_url,
                                         socket_path,
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

        base_url = f"{client.api.base_url}/v{client.api._version}/_ping"
        # Extract socket path from DEFAULT_UNIX_SOCKET (remove http+unix:// prefix)
        socket_path = DEFAULT_UNIX_SOCKET.replace('http+unix://', '')

        mock_obj.assert_called_once_with(base_url,
                                         socket_path,
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
        os.environ.clear()
        os.environ.update(self.os_environ)

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
        os.environ.get('DOCKER_HOST', '').startswith('tcp://') or IS_WINDOWS_PLATFORM,
        reason='Requires a Unix socket'
    )
    @mock.patch("docker.transport.unixconn.UnixHTTPConnectionPool")
    def test_default_pool_size_from_env_unix(self, mock_obj):
        client = docker.from_env(
            version=DEFAULT_DOCKER_API_VERSION, use_context=False,
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        base_url = f"{client.api.base_url}/v{client.api._version}/_ping"
        # Extract socket path from DEFAULT_UNIX_SOCKET (remove http+unix:// prefix)
        socket_path = DEFAULT_UNIX_SOCKET.replace('http+unix://', '')

        mock_obj.assert_called_once_with(base_url,
                                         socket_path,
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
        os.environ.get('DOCKER_HOST', '').startswith('tcp://') or IS_WINDOWS_PLATFORM,
        reason='Requires a Unix socket'
    )
    @mock.patch("docker.transport.unixconn.UnixHTTPConnectionPool")
    def test_pool_size_from_env_unix(self, mock_obj):
        client = docker.from_env(
            version=DEFAULT_DOCKER_API_VERSION,
            max_pool_size=POOL_SIZE,
            use_context=False,
        )
        mock_obj.return_value.urlopen.return_value.status = 200
        client.ping()

        base_url = f"{client.api.base_url}/v{client.api._version}/_ping"
        # Extract socket path from DEFAULT_UNIX_SOCKET (remove http+unix:// prefix)
        socket_path = DEFAULT_UNIX_SOCKET.replace('http+unix://', '')

        mock_obj.assert_called_once_with(base_url,
                                         socket_path,
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


class FromContextTest(unittest.TestCase):
    """from_env / from_context honour Docker CLI contexts so the SDK
    talks to Docker Desktop (or any other current context) by default."""

    def setUp(self):
        self.os_environ = os.environ.copy()
        # Make sure DOCKER_HOST does not short-circuit the context path
        os.environ.pop('DOCKER_HOST', None)
        os.environ.pop('DOCKER_CONTEXT', None)

    def tearDown(self):
        os.environ.clear()
        os.environ.update(self.os_environ)

    @mock.patch('docker.client.ContextAPI.kwargs_from_context')
    def test_from_env_uses_current_context_when_no_docker_host(
            self, mock_ctx):
        mock_ctx.return_value = {
            'base_url': 'unix:///Users/me/.docker/run/docker.sock',
        }
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert mock_ctx.called
        # Unix socket base_urls are rewritten internally; confirm the
        # underlying APIClient picked up the context-supplied socket.
        assert (
            client.api._custom_adapter.socket_path
            == '/Users/me/.docker/run/docker.sock'
        )

    @mock.patch('docker.client.ContextAPI.kwargs_from_context')
    def test_from_env_docker_host_overrides_context(self, mock_ctx):
        mock_ctx.return_value = {
            'base_url': 'unix:///Users/me/.docker/run/docker.sock',
        }
        os.environ['DOCKER_HOST'] = 'tcp://192.168.59.103:2375'
        client = docker.from_env(version=DEFAULT_DOCKER_API_VERSION)
        assert client.api.base_url == 'http://192.168.59.103:2375'
        # When DOCKER_HOST is set we don't need the context fallback.
        assert not mock_ctx.called

    @mock.patch('docker.client.ContextAPI.kwargs_from_context')
    def test_from_env_use_context_false_skips_context(self, mock_ctx):
        client = docker.from_env(
            version=DEFAULT_DOCKER_API_VERSION, use_context=False,
        )
        assert not mock_ctx.called
        # Falls back to APIClient's own platform default.
        assert client.api.base_url in (
            'http+docker://localhost', 'http+docker://localnpipe',
        )

    @mock.patch('docker.client.ContextAPI.kwargs_from_context')
    def test_from_context_uses_named_context(self, mock_ctx):
        mock_ctx.return_value = {
            'base_url': 'unix:///Users/me/.docker/run/docker.sock',
        }
        client = docker.from_context(
            'desktop-linux', version=DEFAULT_DOCKER_API_VERSION,
        )
        mock_ctx.assert_called_once_with(name='desktop-linux')
        assert (
            client.api._custom_adapter.socket_path
            == '/Users/me/.docker/run/docker.sock'
        )

    def test_kwargs_from_context_honours_docker_context_env(self):
        from docker.context import ContextAPI
        # No context with this name exists; helper should return {} rather
        # than raise, leaving APIClient to use its own default.
        params = ContextAPI.kwargs_from_context(
            environment={'DOCKER_CONTEXT': 'does-not-exist'},
        )
        assert params == {}

    def test_kwargs_from_context_default(self):
        from docker.context import ContextAPI
        params = ContextAPI.kwargs_from_context(name='default')
        # The default context always resolves to the local socket / pipe.
        assert 'base_url' in params
        assert params['base_url'] in (
            DEFAULT_UNIX_SOCKET[len('http+'):], DEFAULT_NPIPE,
        )
