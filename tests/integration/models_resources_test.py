import docker
from .base import BaseIntegrationTest, TEST_API_VERSION


class ModelTest(BaseIntegrationTest):

    def test_reload(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 300", detach=True)
        self.tmp_containers.append(container.id)
        first_started_at = container.attrs['State']['StartedAt']
        container.kill()
        container.start()
        assert container.attrs['State']['StartedAt'] == first_started_at
        container.reload()
        assert container.attrs['State']['StartedAt'] != first_started_at
