import docker
from .base import BaseIntegrationTest, TEST_API_VERSION


class VolumesTest(BaseIntegrationTest):
    def test_create_get(self):
        client = docker.from_env(version=TEST_API_VERSION)
        volume = client.volumes.create(
            'dockerpytest_1',
            driver='local',
            labels={'labelkey': 'labelvalue'}
        )
        self.tmp_volumes.append(volume.id)
        assert volume.id
        assert volume.name == 'dockerpytest_1'
        assert volume.attrs['Labels'] == {'labelkey': 'labelvalue'}

        volume = client.volumes.get(volume.id)
        assert volume.name == 'dockerpytest_1'

    def test_list_remove(self):
        client = docker.from_env(version=TEST_API_VERSION)
        volume = client.volumes.create('dockerpytest_1')
        self.tmp_volumes.append(volume.id)
        assert volume in client.volumes.list()
        assert volume in client.volumes.list(filters={'name': 'dockerpytest_'})
        assert volume not in client.volumes.list(filters={'name': 'foobar'})

        volume.remove()
        assert volume not in client.volumes.list()
