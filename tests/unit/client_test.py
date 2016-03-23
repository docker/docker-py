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
