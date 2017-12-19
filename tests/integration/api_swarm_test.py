import copy
import docker
import pytest

from ..helpers import force_leave_swarm, requires_api_version
from .base import BaseAPIIntegrationTest


class SwarmTest(BaseAPIIntegrationTest):
    def setUp(self):
        super(SwarmTest, self).setUp()
        force_leave_swarm(self.client)
        self._unlock_key = None

    def tearDown(self):
        super(SwarmTest, self).tearDown()
        try:
            if self._unlock_key:
                self.client.unlock_swarm(self._unlock_key)
        except docker.errors.APIError:
            pass

        force_leave_swarm(self.client)

    @requires_api_version('1.24')
    def test_init_swarm_simple(self):
        assert self.init_swarm()

    @requires_api_version('1.24')
    def test_init_swarm_force_new_cluster(self):
        pytest.skip('Test stalls the engine on 1.12.0')

        assert self.init_swarm()
        version_1 = self.client.inspect_swarm()['Version']['Index']
        assert self.client.init_swarm(force_new_cluster=True)
        version_2 = self.client.inspect_swarm()['Version']['Index']
        assert version_2 != version_1

    @requires_api_version('1.24')
    def test_init_already_in_cluster(self):
        assert self.init_swarm()
        with pytest.raises(docker.errors.APIError):
            self.init_swarm()

    @requires_api_version('1.24')
    def test_init_swarm_custom_raft_spec(self):
        spec = self.client.create_swarm_spec(
            snapshot_interval=5000, log_entries_for_slow_followers=1200
        )
        assert self.init_swarm(swarm_spec=spec)
        swarm_info = self.client.inspect_swarm()
        assert swarm_info['Spec']['Raft']['SnapshotInterval'] == 5000
        assert swarm_info['Spec']['Raft']['LogEntriesForSlowFollowers'] == 1200

    @requires_api_version('1.30')
    def test_init_swarm_with_ca_config(self):
        spec = self.client.create_swarm_spec(
            node_cert_expiry=7776000000000000, ca_force_rotate=6000000000000
        )

        assert self.init_swarm(swarm_spec=spec)
        swarm_info = self.client.inspect_swarm()
        assert swarm_info['Spec']['CAConfig']['NodeCertExpiry'] == (
            spec['CAConfig']['NodeCertExpiry']
        )
        assert swarm_info['Spec']['CAConfig']['ForceRotate'] == (
            spec['CAConfig']['ForceRotate']
        )

    @requires_api_version('1.25')
    def test_init_swarm_with_autolock_managers(self):
        spec = self.client.create_swarm_spec(autolock_managers=True)
        assert self.init_swarm(swarm_spec=spec)
        # save unlock key for tearDown
        self._unlock_key = self.client.get_unlock_key()
        swarm_info = self.client.inspect_swarm()

        assert (
            swarm_info['Spec']['EncryptionConfig']['AutoLockManagers'] is True
        )

        assert self._unlock_key.get('UnlockKey')

    @requires_api_version('1.25')
    @pytest.mark.xfail(
        reason="This doesn't seem to be taken into account by the engine"
    )
    def test_init_swarm_with_log_driver(self):
        spec = {'TaskDefaults': {'LogDriver': {'Name': 'syslog'}}}
        assert self.init_swarm(swarm_spec=spec)
        swarm_info = self.client.inspect_swarm()

        assert swarm_info['Spec']['TaskDefaults']['LogDriver']['Name'] == (
            'syslog'
        )

    @requires_api_version('1.24')
    def test_leave_swarm(self):
        assert self.init_swarm()
        with pytest.raises(docker.errors.APIError) as exc_info:
            self.client.leave_swarm()
        exc_info.value.response.status_code == 500
        assert self.client.leave_swarm(force=True)
        with pytest.raises(docker.errors.APIError) as exc_info:
            self.client.inspect_swarm()
        exc_info.value.response.status_code == 406
        assert self.client.leave_swarm(force=True)

    @requires_api_version('1.24')
    def test_update_swarm(self):
        assert self.init_swarm()
        swarm_info_1 = self.client.inspect_swarm()
        spec = self.client.create_swarm_spec(
            snapshot_interval=5000, log_entries_for_slow_followers=1200,
            node_cert_expiry=7776000000000000
        )
        assert self.client.update_swarm(
            version=swarm_info_1['Version']['Index'],
            swarm_spec=spec, rotate_worker_token=True
        )
        swarm_info_2 = self.client.inspect_swarm()

        assert (
            swarm_info_1['Version']['Index'] !=
            swarm_info_2['Version']['Index']
        )
        assert swarm_info_2['Spec']['Raft']['SnapshotInterval'] == 5000
        assert (
            swarm_info_2['Spec']['Raft']['LogEntriesForSlowFollowers'] == 1200
        )
        assert (
            swarm_info_1['JoinTokens']['Manager'] ==
            swarm_info_2['JoinTokens']['Manager']
        )
        assert (
            swarm_info_1['JoinTokens']['Worker'] !=
            swarm_info_2['JoinTokens']['Worker']
        )

    @requires_api_version('1.24')
    def test_list_nodes(self):
        assert self.init_swarm()
        nodes_list = self.client.nodes()
        assert len(nodes_list) == 1
        node = nodes_list[0]
        assert 'ID' in node
        assert 'Spec' in node
        assert node['Spec']['Role'] == 'manager'

        filtered_list = self.client.nodes(filters={
            'id': node['ID']
        })
        assert len(filtered_list) == 1
        filtered_list = self.client.nodes(filters={
            'role': 'worker'
        })
        assert len(filtered_list) == 0

    @requires_api_version('1.24')
    def test_inspect_node(self):
        assert self.init_swarm()
        nodes_list = self.client.nodes()
        assert len(nodes_list) == 1
        node = nodes_list[0]
        node_data = self.client.inspect_node(node['ID'])
        assert node['ID'] == node_data['ID']
        assert node['Version'] == node_data['Version']

    @requires_api_version('1.24')
    def test_update_node(self):
        assert self.init_swarm()
        nodes_list = self.client.nodes()
        node = nodes_list[0]
        orig_spec = node['Spec']

        # add a new label
        new_spec = copy.deepcopy(orig_spec)
        new_spec['Labels'] = {'new.label': 'new value'}
        self.client.update_node(node_id=node['ID'],
                                version=node['Version']['Index'],
                                node_spec=new_spec)
        updated_node = self.client.inspect_node(node['ID'])
        assert new_spec == updated_node['Spec']

        # Revert the changes
        self.client.update_node(node_id=node['ID'],
                                version=updated_node['Version']['Index'],
                                node_spec=orig_spec)
        reverted_node = self.client.inspect_node(node['ID'])
        assert orig_spec == reverted_node['Spec']

    @requires_api_version('1.24')
    def test_remove_main_node(self):
        assert self.init_swarm()
        nodes_list = self.client.nodes()
        node_id = nodes_list[0]['ID']
        with pytest.raises(docker.errors.NotFound):
            self.client.remove_node('foobar01')
        with pytest.raises(docker.errors.APIError) as e:
            self.client.remove_node(node_id)

        assert e.value.response.status_code >= 400

        with pytest.raises(docker.errors.APIError) as e:
            self.client.remove_node(node_id, True)

        assert e.value.response.status_code >= 400
