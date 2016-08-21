import json

import pytest

from .. import base
from .api_test import DockerClientTest, url_prefix, fake_request


class VolumeTest(DockerClientTest):
    @base.requires_api_version('1.21')
    def test_list_volumes(self):
        volumes = self.client.volumes()
        self.assertIn('Volumes', volumes)
        self.assertEqual(len(volumes['Volumes']), 2)
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'GET')
        self.assertEqual(args[0][1], url_prefix + 'volumes')

    @base.requires_api_version('1.21')
    def test_list_volumes_and_filters(self):
        volumes = self.client.volumes(filters={'dangling': True})
        assert 'Volumes' in volumes
        assert len(volumes['Volumes']) == 2
        args = fake_request.call_args

        assert args[0][0] == 'GET'
        assert args[0][1] == url_prefix + 'volumes'
        assert args[1] == {'params': {'filters': '{"dangling": ["true"]}'},
                           'timeout': 60}

    @base.requires_api_version('1.21')
    def test_create_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.create_volume(name)
        self.assertIn('Name', result)
        self.assertEqual(result['Name'], name)
        self.assertIn('Driver', result)
        self.assertEqual(result['Driver'], 'local')
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'POST')
        self.assertEqual(args[0][1], url_prefix + 'volumes/create')
        self.assertEqual(json.loads(args[1]['data']), {'Name': name})

    @base.requires_api_version('1.23')
    def test_create_volume_with_labels(self):
        name = 'perfectcherryblossom'
        result = self.client.create_volume(name, labels={
            'com.example.some-label': 'some-value'})
        self.assertEqual(
            result["Labels"],
            {'com.example.some-label': 'some-value'}
        )

    @base.requires_api_version('1.23')
    def test_create_volume_with_invalid_labels(self):
        name = 'perfectcherryblossom'
        with pytest.raises(TypeError):
            self.client.create_volume(name, labels=1)

    @base.requires_api_version('1.21')
    def test_create_volume_with_driver(self):
        name = 'perfectcherryblossom'
        driver_name = 'sshfs'
        self.client.create_volume(name, driver=driver_name)
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'POST')
        self.assertEqual(args[0][1], url_prefix + 'volumes/create')
        data = json.loads(args[1]['data'])
        self.assertIn('Driver', data)
        self.assertEqual(data['Driver'], driver_name)

    @base.requires_api_version('1.21')
    def test_create_volume_invalid_opts_type(self):
        with pytest.raises(TypeError):
            self.client.create_volume(
                'perfectcherryblossom', driver_opts='hello=world'
            )

        with pytest.raises(TypeError):
            self.client.create_volume(
                'perfectcherryblossom', driver_opts=['hello=world']
            )

        with pytest.raises(TypeError):
            self.client.create_volume(
                'perfectcherryblossom', driver_opts=''
            )

    @base.requires_api_version('1.21')
    def test_inspect_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.inspect_volume(name)
        self.assertIn('Name', result)
        self.assertEqual(result['Name'], name)
        self.assertIn('Driver', result)
        self.assertEqual(result['Driver'], 'local')
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'GET')
        self.assertEqual(args[0][1], '{0}volumes/{1}'.format(url_prefix, name))

    @base.requires_api_version('1.21')
    def test_remove_volume(self):
        name = 'perfectcherryblossom'
        self.client.remove_volume(name)
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'DELETE')
        self.assertEqual(args[0][1], '{0}volumes/{1}'.format(url_prefix, name))
