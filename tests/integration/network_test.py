import random

import docker
import pytest

from .. import helpers
from ..base import requires_api_version


@requires_api_version('1.21')
class TestNetworks(helpers.BaseTestCase):
    def create_network(self, *args, **kwargs):
        net_name = u'dockerpy{}'.format(random.getrandbits(24))[:14]
        net_id = self.client.create_network(net_name, *args, **kwargs)['Id']
        self.tmp_networks.append(net_id)
        return (net_name, net_id)

    def test_list_networks(self):
        networks = self.client.networks()
        initial_size = len(networks)

        net_name, net_id = self.create_network()

        networks = self.client.networks()
        self.assertEqual(len(networks), initial_size + 1)
        self.assertTrue(net_id in [n['Id'] for n in networks])

        networks_by_name = self.client.networks(names=[net_name])
        self.assertEqual([n['Id'] for n in networks_by_name], [net_id])

        networks_by_partial_id = self.client.networks(ids=[net_id[:8]])
        self.assertEqual([n['Id'] for n in networks_by_partial_id], [net_id])

    def test_inspect_network(self):
        net_name, net_id = self.create_network()

        net = self.client.inspect_network(net_id)
        self.assertEqual(net, {
            u'Name': net_name,
            u'Id': net_id,
            u'Driver': 'bridge',
            u'Containers': {},
            u'IPAM': {u'Config': [{}], u'Driver': 'default'},
            u'Options': {},
            u'Scope': 'local'
        })

    def test_create_network_with_host_driver_fails(self):
        net_name = 'dockerpy{}'.format(random.getrandbits(24))[:14]

        with pytest.raises(docker.errors.APIError):
            self.client.create_network(net_name, driver='host')

    def test_remove_network(self):
        initial_size = len(self.client.networks())

        net_name, net_id = self.create_network()
        self.assertEqual(len(self.client.networks()), initial_size + 1)

        self.client.remove_network(net_id)
        self.assertEqual(len(self.client.networks()), initial_size)

    def test_connect_and_disconnect_container(self):
        net_name, net_id = self.create_network()

        container = self.client.create_container('busybox', 'top')
        self.tmp_containers.append(container)
        self.client.start(container)

        network_data = self.client.inspect_network(net_id)
        self.assertFalse(network_data.get('Containers'))

        self.client.connect_container_to_network(container, net_id)
        network_data = self.client.inspect_network(net_id)
        self.assertEqual(
            list(network_data['Containers'].keys()),
            [container['Id']])

        self.client.disconnect_container_from_network(container, net_id)
        network_data = self.client.inspect_network(net_id)
        self.assertFalse(network_data.get('Containers'))

    def test_connect_on_container_create(self):
        net_name, net_id = self.create_network()

        container = self.client.create_container(
            image='busybox',
            command='top',
            host_config=self.client.create_host_config(network_mode=net_name),
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        network_data = self.client.inspect_network(net_id)
        self.assertEqual(
            list(network_data['Containers'].keys()),
            [container['Id']])

        self.client.disconnect_container_from_network(container, net_id)
        network_data = self.client.inspect_network(net_id)
        self.assertFalse(network_data.get('Containers'))
