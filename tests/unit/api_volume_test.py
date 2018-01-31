import json

import pytest

from ..helpers import requires_api_version
from .api_test import BaseAPIClientTest, url_prefix, fake_request


class VolumeTest(BaseAPIClientTest):
    def test_list_volumes(self):
        volumes = self.client.volumes()
        assert 'Volumes' in volumes
        assert len(volumes['Volumes']) == 2
        args = fake_request.call_args

        assert args[0][0] == 'GET'
        assert args[0][1] == url_prefix + 'volumes'

    def test_list_volumes_and_filters(self):
        volumes = self.client.volumes(filters={'dangling': True})
        assert 'Volumes' in volumes
        assert len(volumes['Volumes']) == 2
        args = fake_request.call_args

        assert args[0][0] == 'GET'
        assert args[0][1] == url_prefix + 'volumes'
        assert args[1] == {'params': {'filters': '{"dangling": ["true"]}'},
                           'timeout': 60}

    def test_create_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.create_volume(name)
        assert 'Name' in result
        assert result['Name'] == name
        assert 'Driver' in result
        assert result['Driver'] == 'local'
        args = fake_request.call_args

        assert args[0][0] == 'POST'
        assert args[0][1] == url_prefix + 'volumes/create'
        assert json.loads(args[1]['data']) == {'Name': name}

    @requires_api_version('1.23')
    def test_create_volume_with_labels(self):
        name = 'perfectcherryblossom'
        result = self.client.create_volume(name, labels={
            'com.example.some-label': 'some-value'
        })
        assert result["Labels"] == {
            'com.example.some-label': 'some-value'
        }

    @requires_api_version('1.23')
    def test_create_volume_with_invalid_labels(self):
        name = 'perfectcherryblossom'
        with pytest.raises(TypeError):
            self.client.create_volume(name, labels=1)

    def test_create_volume_with_driver(self):
        name = 'perfectcherryblossom'
        driver_name = 'sshfs'
        self.client.create_volume(name, driver=driver_name)
        args = fake_request.call_args

        assert args[0][0] == 'POST'
        assert args[0][1] == url_prefix + 'volumes/create'
        data = json.loads(args[1]['data'])
        assert 'Driver' in data
        assert data['Driver'] == driver_name

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

    @requires_api_version('1.24')
    def test_create_volume_with_no_specified_name(self):
        result = self.client.create_volume(name=None)
        assert 'Name' in result
        assert result['Name'] is not None
        assert 'Driver' in result
        assert result['Driver'] == 'local'
        assert 'Scope' in result
        assert result['Scope'] == 'local'

    def test_inspect_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.inspect_volume(name)
        assert 'Name' in result
        assert result['Name'] == name
        assert 'Driver' in result
        assert result['Driver'] == 'local'
        args = fake_request.call_args

        assert args[0][0] == 'GET'
        assert args[0][1] == '{0}volumes/{1}'.format(url_prefix, name)

    def test_remove_volume(self):
        name = 'perfectcherryblossom'
        self.client.remove_volume(name)
        args = fake_request.call_args

        assert args[0][0] == 'DELETE'
        assert args[0][1] == '{0}volumes/{1}'.format(url_prefix, name)
