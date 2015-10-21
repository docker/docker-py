import json

import six

from .. import base
from .api_test import DockerClientTest, url_prefix, response

try:
    from unittest import mock
except ImportError:
    import mock


class NetworkTest(DockerClientTest):
    @base.requires_api_version('1.21')
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

        with mock.patch('docker.Client.get', get):
            self.assertEqual(self.client.networks(), networks)

            self.assertEqual(get.call_args[0][0], url_prefix + 'networks')

            filters = json.loads(get.call_args[1]['params']['filters'])
            self.assertFalse(filters)

            self.client.networks(names=['foo'])
            filters = json.loads(get.call_args[1]['params']['filters'])
            self.assertEqual(filters, {'name': ['foo']})

            self.client.networks(ids=['123'])
            filters = json.loads(get.call_args[1]['params']['filters'])
            self.assertEqual(filters, {'id': ['123']})

    @base.requires_api_version('1.21')
    def test_create_network(self):
        network_data = {
            "id": 'abc12345',
            "warning": "",
        }

        network_response = response(status_code=200, content=network_data)
        post = mock.Mock(return_value=network_response)

        with mock.patch('docker.Client.post', post):
            result = self.client.create_network('foo')
            self.assertEqual(result, network_data)

            self.assertEqual(
                post.call_args[0][0],
                url_prefix + 'networks/create')

            self.assertEqual(
                json.loads(post.call_args[1]['data']),
                {"name": "foo"})

            self.client.create_network('foo', 'bridge')

            self.assertEqual(
                json.loads(post.call_args[1]['data']),
                {"name": "foo", "driver": "bridge"})

    @base.requires_api_version('1.21')
    def test_remove_network(self):
        network_id = 'abc12345'
        delete = mock.Mock(return_value=response(status_code=200))

        with mock.patch('docker.Client.delete', delete):
            self.client.remove_network(network_id)

        args = delete.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'networks/{0}'.format(network_id))

    @base.requires_api_version('1.21')
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

        with mock.patch('docker.Client.get', get):
            result = self.client.inspect_network(network_id)
            self.assertEqual(result, network_data)

        args = get.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'networks/{0}'.format(network_id))

    @base.requires_api_version('1.21')
    def test_connect_container_to_network(self):
        network_id = 'abc12345'
        container_id = 'def45678'

        post = mock.Mock(return_value=response(status_code=201))

        with mock.patch('docker.Client.post', post):
            self.client.connect_container_to_network(
                {'Id': container_id}, network_id)

        self.assertEqual(
            post.call_args[0][0],
            url_prefix + 'networks/{0}/connect'.format(network_id))

        self.assertEqual(
            json.loads(post.call_args[1]['data']),
            {'container': container_id})

    @base.requires_api_version('1.21')
    def test_disconnect_container_from_network(self):
        network_id = 'abc12345'
        container_id = 'def45678'

        post = mock.Mock(return_value=response(status_code=201))

        with mock.patch('docker.Client.post', post):
            self.client.disconnect_container_from_network(
                {'Id': container_id}, network_id)

        self.assertEqual(
            post.call_args[0][0],
            url_prefix + 'networks/{0}/disconnect'.format(network_id))

        self.assertEqual(
            json.loads(post.call_args[1]['data']),
            {'container': container_id})
