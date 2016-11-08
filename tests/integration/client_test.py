import unittest

import docker


class ClientTest(unittest.TestCase):

    def test_info(self):
        client = docker.from_env()
        info = client.info()
        assert 'ID' in info
        assert 'Name' in info

    def test_ping(self):
        client = docker.from_env()
        assert client.ping() is True

    def test_version(self):
        client = docker.from_env()
        assert 'Version' in client.version()
