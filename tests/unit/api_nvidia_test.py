import docker.utils.nvidia as nvidia
import json

from .api_test import (
    NvidiaAPIClientTest, fake_request, url_prefix, DEFAULT_TIMEOUT_SECONDS
)
from pytest import mark


class StartContainerTest(NvidiaAPIClientTest):
    @mark.skipif("sys.platform == 'win32'")
    def test_create_container_with_nvidia_docker(self):
        self.maxDiff = None

        self.assertEqual(nvidia.get_nvidia_driver_version(), '111.11')
        self.assertEqual(nvidia.get_nvidia_driver_volume(),
                         'nvidia_driver_111.11')

        self.client.create_container('busybox', 'true')

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix +
                         'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = {}
        expected_payload['HostConfig']['Binds'] = [
                'nvidia_driver_111.11:/usr/local/nvidia:ro']
        expected_payload['HostConfig']['Devices'] = []
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )
