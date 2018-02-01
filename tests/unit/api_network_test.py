import json

import six

from .api_test import BaseAPIClientTest, url_prefix, response
from docker.types import IPAMConfig, IPAMPool

try:
    from unittest import mock
except ImportError:
    import mock


class NetworkTest(BaseAPIClientTest):
    def test_list_networks(self):
        networks = [
            {
                "name": "none",
                "id": "8e4e55c6863ef424",
                "type": "null",
                "endpoints": []
            },
            {
                "name": "host",
                "id": "062b6d9ea7913fde",
                "type": "host",
                "endpoints": []
            },
        ]

        get = mock.Mock(return_value=response(
            status_code=200, content=json.dumps(networks).encode('utf-8')))

        with mock.patch('docker.api.client.APIClient.get', get):
            assert self.client.networks() == networks

            assert get.call_args[0][0] == url_prefix + 'networks'

            filters = json.loads(get.call_args[1]['params']['filters'])
            assert not filters

            self.client.networks(names=['foo'])
            filters = json.loads(get.call_args[1]['params']['filters'])
            assert filters == {'name': ['foo']}

            self.client.networks(ids=['123'])
            filters = json.loads(get.call_args[1]['params']['filters'])
            assert filters == {'id': ['123']}

    def test_create_network(self):
        network_data = {
            "id": 'abc12345',
            "warning": "",
        }

        network_response = response(status_code=200, content=network_data)
        post = mock.Mock(return_value=network_response)

        with mock.patch('docker.api.client.APIClient.post', post):
            result = self.client.create_network('foo')
            assert result == network_data

            assert post.call_args[0][0] == url_prefix + 'networks/create'

            assert json.loads(post.call_args[1]['data']) == {"Name": "foo"}

            opts = {
                'com.docker.network.bridge.enable_icc': False,
                'com.docker.network.bridge.enable_ip_masquerade': False,
            }
            self.client.create_network('foo', 'bridge', opts)

            assert json.loads(post.call_args[1]['data']) == {
                "Name": "foo", "Driver": "bridge", "Options": opts
            }

            ipam_pool_config = IPAMPool(subnet="192.168.52.0/24",
                                        gateway="192.168.52.254")
            ipam_config = IPAMConfig(pool_configs=[ipam_pool_config])

            self.client.create_network("bar", driver="bridge",
                                       ipam=ipam_config)

            assert json.loads(post.call_args[1]['data']) == {
                "Name": "bar",
                "Driver": "bridge",
                "IPAM": {
                    "Driver": "default",
                    "Config": [{
                        "IPRange": None,
                        "Gateway": "192.168.52.254",
                        "Subnet": "192.168.52.0/24",
                        "AuxiliaryAddresses": None,
                    }],
                }
            }

    def test_remove_network(self):
        network_id = 'abc12345'
        delete = mock.Mock(return_value=response(status_code=200))

        with mock.patch('docker.api.client.APIClient.delete', delete):
            self.client.remove_network(network_id)

        args = delete.call_args
        assert args[0][0] == url_prefix + 'networks/{0}'.format(network_id)

    def test_inspect_network(self):
        network_id = 'abc12345'
        network_name = 'foo'
        network_data = {
            six.u('name'): network_name,
            six.u('id'): network_id,
            six.u('driver'): 'bridge',
            six.u('containers'): {},
        }

        network_response = response(status_code=200, content=network_data)
        get = mock.Mock(return_value=network_response)

        with mock.patch('docker.api.client.APIClient.get', get):
            result = self.client.inspect_network(network_id)
            assert result == network_data

        args = get.call_args
        assert args[0][0] == url_prefix + 'networks/{0}'.format(network_id)

    def test_connect_container_to_network(self):
        network_id = 'abc12345'
        container_id = 'def45678'

        post = mock.Mock(return_value=response(status_code=201))

        with mock.patch('docker.api.client.APIClient.post', post):
            self.client.connect_container_to_network(
                container={'Id': container_id},
                net_id=network_id,
                aliases=['foo', 'bar'],
                links=[('baz', 'quux')]
            )

        assert post.call_args[0][0] == (
            url_prefix + 'networks/{0}/connect'.format(network_id)
        )

        assert json.loads(post.call_args[1]['data']) == {
            'Container': container_id,
            'EndpointConfig': {
                'Aliases': ['foo', 'bar'],
                'Links': ['baz:quux'],
            },
        }

    def test_disconnect_container_from_network(self):
        network_id = 'abc12345'
        container_id = 'def45678'

        post = mock.Mock(return_value=response(status_code=201))

        with mock.patch('docker.api.client.APIClient.post', post):
            self.client.disconnect_container_from_network(
                container={'Id': container_id}, net_id=network_id)

        assert post.call_args[0][0] == (
            url_prefix + 'networks/{0}/disconnect'.format(network_id)
        )
        assert json.loads(post.call_args[1]['data']) == {
            'Container': container_id
        }
