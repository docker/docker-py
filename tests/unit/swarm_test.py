# -*- coding: utf-8 -*-

import json

from . import fake_api
from ..helpers import requires_api_version
from .api_test import BaseAPIClientTest, url_prefix, fake_request


class SwarmTest(BaseAPIClientTest):
    @requires_api_version('1.24')
    def test_node_update(self):
        node_spec = {
            'Availability': 'active',
            'Name': 'node-name',
            'Role': 'manager',
            'Labels': {'foo': 'bar'}
        }

        self.client.update_node(
            node_id=fake_api.FAKE_NODE_ID, version=1, node_spec=node_spec
        )
        args = fake_request.call_args
        assert args[0][1] == (
            url_prefix + 'nodes/24ifsmvkjbyhk/update?version=1'
        )
        assert json.loads(args[1]['data']) == node_spec
        assert args[1]['headers']['Content-Type'] == 'application/json'

    @requires_api_version('1.24')
    def test_join_swarm(self):
        remote_addr = ['1.2.3.4:2377']
        listen_addr = '2.3.4.5:2377'
        join_token = 'A_BEAUTIFUL_JOIN_TOKEN'

        data = {
            'RemoteAddrs': remote_addr,
            'ListenAddr': listen_addr,
            'JoinToken': join_token
        }

        self.client.join_swarm(
            remote_addrs=remote_addr,
            listen_addr=listen_addr,
            join_token=join_token
        )

        args = fake_request.call_args

        assert (args[0][1] == url_prefix + 'swarm/join')
        assert (json.loads(args[1]['data']) == data)
        assert (args[1]['headers']['Content-Type'] == 'application/json')

    @requires_api_version('1.24')
    def test_join_swarm_no_listen_address_takes_default(self):
        remote_addr = ['1.2.3.4:2377']
        join_token = 'A_BEAUTIFUL_JOIN_TOKEN'

        data = {
            'RemoteAddrs': remote_addr,
            'ListenAddr': '0.0.0.0:2377',
            'JoinToken': join_token
        }

        self.client.join_swarm(remote_addrs=remote_addr, join_token=join_token)

        args = fake_request.call_args

        assert (args[0][1] == url_prefix + 'swarm/join')
        assert (json.loads(args[1]['data']) == data)
        assert (args[1]['headers']['Content-Type'] == 'application/json')
