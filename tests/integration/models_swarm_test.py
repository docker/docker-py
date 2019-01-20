import unittest

import docker

from .. import helpers
from .base import TEST_API_VERSION
import pytest


class SwarmTest(unittest.TestCase):
    def setUp(self):
        helpers.force_leave_swarm(docker.from_env(version=TEST_API_VERSION))

    def tearDown(self):
        helpers.force_leave_swarm(docker.from_env(version=TEST_API_VERSION))

    def test_init_update_leave(self):
        client = docker.from_env(version=TEST_API_VERSION)
        client.swarm.init(
            advertise_addr='127.0.0.1', snapshot_interval=5000,
            listen_addr=helpers.swarm_listen_addr()
        )
        assert client.swarm.attrs['Spec']['Raft']['SnapshotInterval'] == 5000
        client.swarm.update(snapshot_interval=10000)
        assert client.swarm.attrs['Spec']['Raft']['SnapshotInterval'] == 10000
        assert client.swarm.id
        assert client.swarm.leave(force=True)
        with pytest.raises(docker.errors.APIError) as cm:
            client.swarm.reload()
        assert (
            cm.value.response.status_code == 406 or
            cm.value.response.status_code == 503
        )
