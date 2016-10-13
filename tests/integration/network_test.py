import random

import docker
from docker.utils import create_ipam_config
from docker.utils import create_ipam_pool
import pytest

from .. import helpers
from ..base import requires_api_version


class TestNetworks(helpers.BaseTestCase):
    def create_network(self, *args, **kwargs):
        net_name = u'dockerpy{}'.format(random.getrandbits(24))[:14]
        net_id = self.client.create_network(net_name, *args, **kwargs)['Id']
        self.tmp_networks.append(net_id)
        return (net_name, net_id)

    @requires_api_version('1.21')
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

    @requires_api_version('1.21')
    def test_inspect_network(self):
        net_name, net_id = self.create_network()

        net = self.client.inspect_network(net_id)
        self.assertEqual(net['Id'], net_id)
        self.assertEqual(net['Name'], net_name)
        self.assertEqual(net['Driver'], 'bridge')
        self.assertEqual(net['Scope'], 'local')
        self.assertEqual(net['IPAM']['Driver'], 'default')

    @requires_api_version('1.21')
    def test_create_network_with_ipam_config(self):
        _, net_id = self.create_network(
            ipam=create_ipam_config(
                driver='default',
                pool_configs=[
                    create_ipam_pool(
                        subnet="172.28.0.0/16",
                        iprange="172.28.5.0/24",
                        gateway="172.28.5.254",
                        aux_addresses={
                            "a": "172.28.1.5",
                            "b": "172.28.1.6",
                            "c": "172.28.1.7",
                        },
                    ),
                ],
            ),
        )

        net = self.client.inspect_network(net_id)
        ipam = net['IPAM']

        assert ipam.pop('Options', None) is None

        assert ipam['Driver'] == 'default'

        assert ipam['Config'] == [{
            'Subnet': "172.28.0.0/16",
            'IPRange': "172.28.5.0/24",
            'Gateway': "172.28.5.254",
            'AuxiliaryAddresses': {
                "a": "172.28.1.5",
                "b": "172.28.1.6",
                "c": "172.28.1.7",
            },
        }]

    @requires_api_version('1.21')
    def test_create_network_with_host_driver_fails(self):
        net_name = 'dockerpy{}'.format(random.getrandbits(24))[:14]

        with pytest.raises(docker.errors.APIError):
            self.client.create_network(net_name, driver='host')

    @requires_api_version('1.21')
    def test_remove_network(self):
        initial_size = len(self.client.networks())

        net_name, net_id = self.create_network()
        self.assertEqual(len(self.client.networks()), initial_size + 1)

        self.client.remove_network(net_id)
        self.assertEqual(len(self.client.networks()), initial_size)

    @requires_api_version('1.21')
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
            [container['Id']]
        )

        with pytest.raises(docker.errors.APIError):
            self.client.connect_container_to_network(container, net_id)

        self.client.disconnect_container_from_network(container, net_id)
        network_data = self.client.inspect_network(net_id)
        self.assertFalse(network_data.get('Containers'))

        with pytest.raises(docker.errors.APIError):
            self.client.disconnect_container_from_network(container, net_id)

    @requires_api_version('1.22')
    def test_connect_and_force_disconnect_container(self):
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
            [container['Id']]
        )

        self.client.disconnect_container_from_network(container, net_id, True)
        network_data = self.client.inspect_network(net_id)
        self.assertFalse(network_data.get('Containers'))

        with pytest.raises(docker.errors.APIError):
            self.client.disconnect_container_from_network(
                container, net_id, force=True
            )

    @requires_api_version('1.22')
    def test_connect_with_aliases(self):
        net_name, net_id = self.create_network()

        container = self.client.create_container('busybox', 'top')
        self.tmp_containers.append(container)
        self.client.start(container)

        self.client.connect_container_to_network(
            container, net_id, aliases=['foo', 'bar'])
        container_data = self.client.inspect_container(container)
        aliases = (
            container_data['NetworkSettings']['Networks'][net_name]['Aliases']
        )
        assert 'foo' in aliases
        assert 'bar' in aliases

    @requires_api_version('1.21')
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

    @requires_api_version('1.22')
    def test_create_with_aliases(self):
        net_name, net_id = self.create_network()

        container = self.client.create_container(
            image='busybox',
            command='top',
            host_config=self.client.create_host_config(
                network_mode=net_name,
            ),
            networking_config=self.client.create_networking_config({
                net_name: self.client.create_endpoint_config(
                    aliases=['foo', 'bar'],
                ),
            }),
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        container_data = self.client.inspect_container(container)
        aliases = (
            container_data['NetworkSettings']['Networks'][net_name]['Aliases']
        )
        assert 'foo' in aliases
        assert 'bar' in aliases

    @requires_api_version('1.22')
    def test_create_with_ipv4_address(self):
        net_name, net_id = self.create_network(
            ipam=create_ipam_config(
                driver='default',
                pool_configs=[create_ipam_pool(subnet="132.124.0.0/16")],
            ),
        )
        container = self.client.create_container(
            image='busybox', command='top',
            host_config=self.client.create_host_config(network_mode=net_name),
            networking_config=self.client.create_networking_config({
                net_name: self.client.create_endpoint_config(
                    ipv4_address='132.124.0.23'
                )
            })
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        container_data = self.client.inspect_container(container)
        self.assertEqual(
            container_data[
                'NetworkSettings']['Networks'][net_name]['IPAMConfig'][
                'IPv4Address'
            ],
            '132.124.0.23'
        )

    @requires_api_version('1.22')
    def test_create_with_ipv6_address(self):
        net_name, net_id = self.create_network(
            ipam=create_ipam_config(
                driver='default',
                pool_configs=[create_ipam_pool(subnet="2001:389::1/64")],
            ),
        )
        container = self.client.create_container(
            image='busybox', command='top',
            host_config=self.client.create_host_config(network_mode=net_name),
            networking_config=self.client.create_networking_config({
                net_name: self.client.create_endpoint_config(
                    ipv6_address='2001:389::f00d'
                )
            })
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        container_data = self.client.inspect_container(container)
        self.assertEqual(
            container_data[
                'NetworkSettings']['Networks'][net_name]['IPAMConfig'][
                'IPv6Address'
            ],
            '2001:389::f00d'
        )

    @requires_api_version('1.24')
    def test_create_with_linklocal_ips(self):
        container = self.client.create_container(
            'busybox', 'top',
            networking_config=self.client.create_networking_config(
                {
                    'bridge': self.client.create_endpoint_config(
                        link_local_ips=['169.254.8.8']
                    )
                }
            ),
            host_config=self.client.create_host_config(network_mode='bridge')
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        container_data = self.client.inspect_container(container)
        net_cfg = container_data['NetworkSettings']['Networks']['bridge']
        assert 'IPAMConfig' in net_cfg
        assert 'LinkLocalIPs' in net_cfg['IPAMConfig']
        assert net_cfg['IPAMConfig']['LinkLocalIPs'] == ['169.254.8.8']

    @requires_api_version('1.22')
    def test_create_with_links(self):
        net_name, net_id = self.create_network()

        container = self.create_and_start(
            host_config=self.client.create_host_config(network_mode=net_name),
            networking_config=self.client.create_networking_config({
                net_name: self.client.create_endpoint_config(
                    links=[('docker-py-test-upstream', 'bar')],
                ),
            }),
        )

        container_data = self.client.inspect_container(container)
        self.assertEqual(
            container_data['NetworkSettings']['Networks'][net_name]['Links'],
            ['docker-py-test-upstream:bar'])

        self.create_and_start(
            name='docker-py-test-upstream',
            host_config=self.client.create_host_config(network_mode=net_name),
        )

        self.execute(container, ['nslookup', 'bar'])

    @requires_api_version('1.21')
    def test_create_check_duplicate(self):
        net_name, net_id = self.create_network()
        with self.assertRaises(docker.errors.APIError):
            self.client.create_network(net_name, check_duplicate=True)
        net_id = self.client.create_network(net_name, check_duplicate=False)
        self.tmp_networks.append(net_id['Id'])

    @requires_api_version('1.22')
    def test_connect_with_links(self):
        net_name, net_id = self.create_network()

        container = self.create_and_start(
            host_config=self.client.create_host_config(network_mode=net_name))

        self.client.disconnect_container_from_network(container, net_name)
        self.client.connect_container_to_network(
            container, net_name,
            links=[('docker-py-test-upstream', 'bar')])

        container_data = self.client.inspect_container(container)
        self.assertEqual(
            container_data['NetworkSettings']['Networks'][net_name]['Links'],
            ['docker-py-test-upstream:bar'])

        self.create_and_start(
            name='docker-py-test-upstream',
            host_config=self.client.create_host_config(network_mode=net_name),
        )

        self.execute(container, ['nslookup', 'bar'])

    @requires_api_version('1.22')
    def test_connect_with_ipv4_address(self):
        net_name, net_id = self.create_network(
            ipam=create_ipam_config(
                driver='default',
                pool_configs=[
                    create_ipam_pool(
                        subnet="172.28.0.0/16", iprange="172.28.5.0/24",
                        gateway="172.28.5.254"
                    )
                ]
            )
        )

        container = self.create_and_start(
            host_config=self.client.create_host_config(network_mode=net_name))

        self.client.disconnect_container_from_network(container, net_name)
        self.client.connect_container_to_network(
            container, net_name, ipv4_address='172.28.5.24'
        )

        container_data = self.client.inspect_container(container)
        net_data = container_data['NetworkSettings']['Networks'][net_name]
        self.assertEqual(
            net_data['IPAMConfig']['IPv4Address'], '172.28.5.24'
        )

    @requires_api_version('1.22')
    def test_connect_with_ipv6_address(self):
        net_name, net_id = self.create_network(
            ipam=create_ipam_config(
                driver='default',
                pool_configs=[
                    create_ipam_pool(
                        subnet="2001:389::1/64", iprange="2001:389::0/96",
                        gateway="2001:389::ffff"
                    )
                ]
            )
        )

        container = self.create_and_start(
            host_config=self.client.create_host_config(network_mode=net_name))

        self.client.disconnect_container_from_network(container, net_name)
        self.client.connect_container_to_network(
            container, net_name, ipv6_address='2001:389::f00d'
        )

        container_data = self.client.inspect_container(container)
        net_data = container_data['NetworkSettings']['Networks'][net_name]
        self.assertEqual(
            net_data['IPAMConfig']['IPv6Address'], '2001:389::f00d'
        )

    @requires_api_version('1.23')
    def test_create_internal_networks(self):
        _, net_id = self.create_network(internal=True)
        net = self.client.inspect_network(net_id)
        assert net['Internal'] is True

    @requires_api_version('1.23')
    def test_create_network_with_labels(self):
        _, net_id = self.create_network(labels={
            'com.docker.py.test': 'label'
        })

        net = self.client.inspect_network(net_id)
        assert 'Labels' in net
        assert len(net['Labels']) == 1
        assert net['Labels'] == {
            'com.docker.py.test': 'label'
        }

    @requires_api_version('1.23')
    def test_create_network_with_labels_wrong_type(self):
        with pytest.raises(TypeError):
            self.create_network(labels=['com.docker.py.test=label', ])

    @requires_api_version('1.23')
    def test_create_network_ipv6_enabled(self):
        _, net_id = self.create_network(enable_ipv6=True)
        net = self.client.inspect_network(net_id)
        assert net['EnableIPv6'] is True
