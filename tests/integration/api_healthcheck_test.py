from .. import helpers
from .base import TEST_IMG, BaseAPIIntegrationTest

SECOND = 1000000000


def wait_on_health_status(client, container, status):
    def condition():
        res = client.inspect_container(container)
        return res['State']['Health']['Status'] == status
    return helpers.wait_on_condition(condition)


class HealthcheckTest(BaseAPIIntegrationTest):

    @helpers.requires_api_version('1.24')
    def test_healthcheck_shell_command(self):
        container = self.client.create_container(
            TEST_IMG, 'top', healthcheck={'test': 'echo "hello world"'})
        self.tmp_containers.append(container)

        res = self.client.inspect_container(container)
        assert res['Config']['Healthcheck']['Test'] == [
            'CMD-SHELL', 'echo "hello world"'
        ]

    @helpers.requires_api_version('1.24')
    def test_healthcheck_passes(self):
        container = self.client.create_container(
            TEST_IMG, 'top', healthcheck={
                'test': "true",
                'interval': 1 * SECOND,
                'timeout': 1 * SECOND,
                'retries': 1,
            })
        self.tmp_containers.append(container)
        self.client.start(container)
        wait_on_health_status(self.client, container, "healthy")

    @helpers.requires_api_version('1.24')
    def test_healthcheck_fails(self):
        container = self.client.create_container(
            TEST_IMG, 'top', healthcheck={
                'test': "false",
                'interval': 1 * SECOND,
                'timeout': 1 * SECOND,
                'retries': 1,
            })
        self.tmp_containers.append(container)
        self.client.start(container)
        wait_on_health_status(self.client, container, "unhealthy")

    @helpers.requires_api_version('1.29')
    def test_healthcheck_start_period(self):
        container = self.client.create_container(
            TEST_IMG, 'top', healthcheck={
                'test': "echo 'x' >> /counter.txt && "
                     "test `cat /counter.txt | wc -l` -ge 3",
                'interval': 1 * SECOND,
                'timeout': 1 * SECOND,
                'retries': 1,
                'start_period': 3 * SECOND
            }
        )

        self.tmp_containers.append(container)
        self.client.start(container)
        wait_on_health_status(self.client, container, "healthy")
