import docker
import pytest

from ..base import requires_api_version
from .. import helpers


BUSYBOX = helpers.BUSYBOX


class SwarmTest(helpers.BaseTestCase):
    def setUp(self):
        super(SwarmTest, self).setUp()
        try:
            self.client.leave_swarm(force=True)
        except docker.errors.APIError:
            pass

    def tearDown(self):
        super(SwarmTest, self).tearDown()
        try:
            self.client.leave_swarm(force=True)
        except docker.errors.APIError:
            pass

    @requires_api_version('1.24')
    def test_init_swarm_simple(self):
        assert self.client.init_swarm('eth0')

    @requires_api_version('1.24')
    def test_init_swarm_force_new_cluster(self):
        pytest.skip('Test stalls the engine on 1.12.0')

        assert self.client.init_swarm('eth0')
        version_1 = self.client.inspect_swarm()['Version']['Index']
        assert self.client.init_swarm('eth0', force_new_cluster=True)
        version_2 = self.client.inspect_swarm()['Version']['Index']
        assert version_2 != version_1

    @requires_api_version('1.24')
    def test_init_already_in_cluster(self):
        assert self.client.init_swarm('eth0')
        with pytest.raises(docker.errors.APIError):
            self.client.init_swarm('eth0')

    @requires_api_version('1.24')
    def test_init_swarm_custom_raft_spec(self):
        spec = self.client.create_swarm_spec(
            snapshot_interval=5000, log_entries_for_slow_followers=1200
        )
        assert self.client.init_swarm(
            advertise_addr='eth0', swarm_spec=spec
        )
        swarm_info = self.client.inspect_swarm()
        assert swarm_info['Spec']['Raft']['SnapshotInterval'] == 5000
        assert swarm_info['Spec']['Raft']['LogEntriesForSlowFollowers'] == 1200

    @requires_api_version('1.24')
    def test_leave_swarm(self):
        assert self.client.init_swarm('eth0')
        with pytest.raises(docker.errors.APIError) as exc_info:
            self.client.leave_swarm()
        exc_info.value.response.status_code == 500
        assert self.client.leave_swarm(force=True)
        with pytest.raises(docker.errors.APIError) as exc_info:
            self.client.inspect_swarm()
        exc_info.value.response.status_code == 406