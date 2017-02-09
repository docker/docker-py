import unittest

import docker

from .base import TEST_API_VERSION
from ..helpers import requires_api_version


class ClientTest(unittest.TestCase):

    def test_info(self):
        client = docker.from_env(version=TEST_API_VERSION)
        info = client.info()
        assert 'ID' in info
        assert 'Name' in info

    def test_ping(self):
        client = docker.from_env(version=TEST_API_VERSION)
        assert client.ping() is True

    def test_version(self):
        client = docker.from_env(version=TEST_API_VERSION)
        assert 'Version' in client.version()

    @requires_api_version('1.25')
    def test_df(self):
        client = docker.from_env()
        assert 'LayersSize' in client.df()
