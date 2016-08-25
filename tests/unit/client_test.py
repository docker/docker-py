import os
from docker.client import Client
from .. import base

TEST_CERT_DIR = os.path.join(
    os.path.dirname(__file__),
    'testdata/certs',
)


class ClientTest(base.BaseTestCase):
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
        client = Client.from_env()
        self.assertEqual(client.base_url, "https://192.168.59.103:2376")

    def test_from_env_with_version(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='1')
        client = Client.from_env(version='2.32')
        self.assertEqual(client.base_url, "https://192.168.59.103:2376")
        self.assertEqual(client._version, '2.32')


class DisableSocketTest(base.BaseTestCase):
    class DummySocket(object):
        def __init__(self, timeout=60):
            self.timeout = timeout

        def settimeout(self, timeout):
            self.timeout = timeout

        def gettimeout(self):
            return self.timeout

    def setUp(self):
        self.client = Client()

    def test_disable_socket_timeout(self):
        """Test that the timeout is disabled on a generic socket object."""
        socket = self.DummySocket()

        self.client._disable_socket_timeout(socket)

        self.assertEqual(socket.timeout, None)

    def test_disable_socket_timeout2(self):
        """Test that the timeouts are disabled on a generic socket object
        and it's _sock object if present."""
        socket = self.DummySocket()
        socket._sock = self.DummySocket()

        self.client._disable_socket_timeout(socket)

        self.assertEqual(socket.timeout, None)
        self.assertEqual(socket._sock.timeout, None)

    def test_disable_socket_timout_non_blocking(self):
        """Test that a non-blocking socket does not get set to blocking."""
        socket = self.DummySocket()
        socket._sock = self.DummySocket(0.0)

        self.client._disable_socket_timeout(socket)

        self.assertEqual(socket.timeout, None)
        self.assertEqual(socket._sock.timeout, 0.0)
