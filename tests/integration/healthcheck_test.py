import time
import docker

from ..base import requires_api_version
from .. import helpers


class HealthcheckTest(helpers.BaseTestCase):

    @requires_api_version('1.21')
    def test_healthcheck(self):
        healthcheck = docker.types.Healthcheck(
            test=["CMD-SHELL",
                  "foo.txt || (/bin/usleep 10000 && touch foo.txt)"],
            interval=500000,
            timeout=1000000000,
            retries=1
        )
        container = self.client.create_container(helpers.BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True,
                                                 healthcheck=healthcheck)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res1 = self.client.inspect_container(id)
        self.assertIn('State', res1)
        self.assertIn('Health', res1['State'])
        self.assertIn('Status', res1['State']['Health'])
        self.assertEqual(res1['State']['Health']['Status'], "starting")
        time.sleep(0.5)
        res2 = self.client.inspect_container(id)
        self.assertIn('State', res2)
        self.assertIn('Health', res2['State'])
        self.assertIn('Status', res2['State']['Health'])
        self.assertEqual(res2['State']['Health']['Status'], "healthy")
