import unittest

import docker

from ..helpers import requires_api_version
from .base import TEST_API_VERSION


class ClientTest(unittest.TestCase):
    client = docker.from_env(version=TEST_API_VERSION)

    def test_info(self):
        info = self.client.info()
        assert 'ID' in info
        assert 'Name' in info

    def test_ping(self):
        assert self.client.ping() is True

    def test_version(self):
        assert 'Version' in self.client.version()

    @requires_api_version('1.25')
    def test_df(self):
        data = self.client.df()
        assert 'LayersSize' in data
        assert 'Containers' in data
        assert 'Volumes' in data
        assert 'Images' in data
