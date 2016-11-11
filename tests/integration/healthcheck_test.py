import docker

from .base import BaseIntegrationTest
from .base import BUSYBOX
from .. import helpers

SECOND = 1000000000


class HealthcheckTest(BaseIntegrationTest):

    @helpers.requires_api_version('1.24')
    def test_healthcheck_passes(self):
        healthcheck = docker.types.Healthcheck(
            test=["CMD-SHELL", "true"],
            interval=1*SECOND,
            timeout=1*SECOND,
            retries=1,
        )
        container = self.client.create_container(
            BUSYBOX, 'top', healthcheck=healthcheck)
        self.tmp_containers.append(container)

        res = self.client.inspect_container(container)
        assert res['Config']['Healthcheck'] == {
            "Test": ["CMD-SHELL", "true"],
            "Interval": 1*SECOND,
            "Timeout": 1*SECOND,
            "Retries": 1,
        }

        def condition():
            res = self.client.inspect_container(container)
            return res['State']['Health']['Status'] == "healthy"

        self.client.start(container)
        helpers.wait_on_condition(condition)

    @helpers.requires_api_version('1.24')
    def test_healthcheck_fails(self):
        healthcheck = docker.types.Healthcheck(
            test=["CMD-SHELL", "false"],
            interval=1*SECOND,
            timeout=1*SECOND,
            retries=1,
        )
        container = self.client.create_container(
            BUSYBOX, 'top', healthcheck=healthcheck)
        self.tmp_containers.append(container)

        def condition():
            res = self.client.inspect_container(container)
            return res['State']['Health']['Status'] == "unhealthy"

        self.client.start(container)
        helpers.wait_on_condition(condition)
