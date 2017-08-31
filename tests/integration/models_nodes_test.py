import unittest

import docker

from .. import helpers
from .base import TEST_API_VERSION


class NodesTest(unittest.TestCase):
    def setUp(self):
        helpers.force_leave_swarm(docker.from_env(version=TEST_API_VERSION))

    def tearDown(self):
        helpers.force_leave_swarm(docker.from_env(version=TEST_API_VERSION))

    def test_list_get_update(self):
        client = docker.from_env(version=TEST_API_VERSION)
        client.swarm.init('127.0.0.1', listen_addr=helpers.swarm_listen_addr())
        nodes = client.nodes.list()
        assert len(nodes) == 1
        assert nodes[0].attrs['Spec']['Role'] == 'manager'

        node = client.nodes.get(nodes[0].id)
        assert node.id == nodes[0].id
        assert node.attrs['Spec']['Role'] == 'manager'
        assert node.version > 0

        node = client.nodes.list()[0]
        assert not node.attrs['Spec'].get('Labels')
        node.update({
            'Availability': 'active',
            'Name': 'node-name',
            'Role': 'manager',
            'Labels': {'foo': 'bar'}
        })
        node.reload()
        assert node.attrs['Spec']['Labels'] == {'foo': 'bar'}
