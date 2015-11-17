import docker
import pytest

from .. import helpers
from ..base import requires_api_version


@requires_api_version('1.21')
class TestVolumes(helpers.BaseTestCase):
    def test_create_volume(self):
        name = 'perfectcherryblossom'
        self.tmp_volumes.append(name)
        result = self.client.create_volume(name)
        self.assertIn('Name', result)
        self.assertEqual(result['Name'], name)
        self.assertIn('Driver', result)
        self.assertEqual(result['Driver'], 'local')

    def test_create_volume_invalid_driver(self):
        driver_name = 'invalid.driver'

        with pytest.raises(docker.errors.NotFound):
            self.client.create_volume('perfectcherryblossom', driver_name)

    def test_list_volumes(self):
        name = 'imperishablenight'
        self.tmp_volumes.append(name)
        volume_info = self.client.create_volume(name)
        result = self.client.volumes()
        self.assertIn('Volumes', result)
        volumes = result['Volumes']
        self.assertIn(volume_info, volumes)

    def test_inspect_volume(self):
        name = 'embodimentofscarletdevil'
        self.tmp_volumes.append(name)
        volume_info = self.client.create_volume(name)
        result = self.client.inspect_volume(name)
        self.assertEqual(volume_info, result)

    def test_inspect_nonexistent_volume(self):
        name = 'embodimentofscarletdevil'
        with pytest.raises(docker.errors.NotFound):
            self.client.inspect_volume(name)

    def test_remove_volume(self):
        name = 'shootthebullet'
        self.tmp_volumes.append(name)
        self.client.create_volume(name)
        result = self.client.remove_volume(name)
        self.assertTrue(result)

    def test_remove_nonexistent_volume(self):
        name = 'shootthebullet'
        with pytest.raises(docker.errors.NotFound):
            self.client.remove_volume(name)
