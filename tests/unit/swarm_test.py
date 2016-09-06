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
        self.assertEqual(
            args[0][1], url_prefix + 'nodes/24ifsmvkjbyhk/update?version=1'
        )
        self.assertEqual(
            json.loads(args[1]['data']), node_spec
        )
        self.assertEqual(
            args[1]['headers']['Content-Type'], 'application/json'
        )
