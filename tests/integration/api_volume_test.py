import docker
import pytest

from ..helpers import requires_api_version
from .base import BaseAPIIntegrationTest


class TestVolumes(BaseAPIIntegrationTest):
    def test_create_volume(self):
        name = 'perfectcherryblossom'
        self.tmp_volumes.append(name)
        result = self.client.create_volume(name)
        assert 'Name' in result
        assert result['Name'] == name
        assert 'Driver' in result
        assert result['Driver'] == 'local'

    def test_create_volume_invalid_driver(self):
        driver_name = 'invalid.driver'

        with pytest.raises(docker.errors.NotFound):
            self.client.create_volume('perfectcherryblossom', driver_name)

    def test_list_volumes(self):
        name = 'imperishablenight'
        self.tmp_volumes.append(name)
        volume_info = self.client.create_volume(name)
        result = self.client.volumes()
        assert 'Volumes' in result
        volumes = result['Volumes']
        assert volume_info in volumes

    def test_inspect_volume(self):
        name = 'embodimentofscarletdevil'
        self.tmp_volumes.append(name)
        volume_info = self.client.create_volume(name)
        result = self.client.inspect_volume(name)
        assert volume_info == result

    def test_inspect_nonexistent_volume(self):
        name = 'embodimentofscarletdevil'
        with pytest.raises(docker.errors.NotFound):
            self.client.inspect_volume(name)

    def test_remove_volume(self):
        name = 'shootthebullet'
        self.tmp_volumes.append(name)
        self.client.create_volume(name)
        self.client.remove_volume(name)

    @requires_api_version('1.25')
    def test_force_remove_volume(self):
        name = 'shootthebullet'
        self.tmp_volumes.append(name)
        self.client.create_volume(name)
        self.client.remove_volume(name, force=True)

    @requires_api_version('1.25')
    def test_prune_volumes(self):
        name = 'hopelessmasquerade'
        self.client.create_volume(name)
        self.tmp_volumes.append(name)
        result = self.client.prune_volumes()
        assert name in result['VolumesDeleted']

    def test_remove_nonexistent_volume(self):
        name = 'shootthebullet'
        with pytest.raises(docker.errors.NotFound):
            self.client.remove_volume(name)
