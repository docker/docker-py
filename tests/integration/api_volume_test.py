import pytest

import docker

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
        # special name to avoid exponential timeout loop
        # https://github.com/moby/moby/blob/9e00a63d65434cdedc444e79a2b33a7c202b10d8/pkg/plugins/client.go#L253-L254
        driver_name = 'this-plugin-does-not-exist'

        with pytest.raises(docker.errors.APIError) as cm:
            self.client.create_volume('perfectcherryblossom', driver_name)
            assert (
                cm.value.response.status_code == 404 or
                cm.value.response.status_code == 400
            )

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
        v = self.client.create_volume()
        self.tmp_volumes.append(v["Name"])
        result = self.client.prune_volumes()
        assert v["Name"] in result['VolumesDeleted']

    def test_remove_nonexistent_volume(self):
        name = 'shootthebullet'
        with pytest.raises(docker.errors.NotFound):
            self.client.remove_volume(name)
