import json

from . import fake_api
from .api_test import (
    DockerClientTest, url_prefix, fake_request, DEFAULT_TIMEOUT_SECONDS,
)


class ExecTest(DockerClientTest):
    def test_exec_create(self):
        self.client.exec_create(fake_api.FAKE_CONTAINER_ID, ['ls', '-1'])

        args = fake_request.call_args
        self.assertEqual(
            'POST',
            args[0][0], url_prefix + 'containers/{0}/exec'.format(
                fake_api.FAKE_CONTAINER_ID
            )
        )

        self.assertEqual(
            json.loads(args[1]['data']), {
                'Tty': False,
                'AttachStdout': True,
                'Container': fake_api.FAKE_CONTAINER_ID,
                'Cmd': ['ls', '-1'],
                'Privileged': False,
                'AttachStdin': False,
                'AttachStderr': True,
                'User': ''
            }
        )

        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_exec_start(self):
        self.client.exec_start(fake_api.FAKE_EXEC_ID)

        args = fake_request.call_args
        self.assertEqual(
            args[0][1], url_prefix + 'exec/{0}/start'.format(
                fake_api.FAKE_EXEC_ID
            )
        )

        self.assertEqual(
            json.loads(args[1]['data']), {
                'Tty': False,
                'Detach': False,
            }
        )

        self.assertEqual(
            args[1]['headers'], {
                'Content-Type': 'application/json',
                'Connection': 'Upgrade',
                'Upgrade': 'tcp'
            }
        )

    def test_exec_start_detached(self):
        self.client.exec_start(fake_api.FAKE_EXEC_ID, detach=True)

        args = fake_request.call_args
        self.assertEqual(
            args[0][1], url_prefix + 'exec/{0}/start'.format(
                fake_api.FAKE_EXEC_ID
            )
        )

        self.assertEqual(
            json.loads(args[1]['data']), {
                'Tty': False,
                'Detach': True
            }
        )

        self.assertEqual(
            args[1]['headers'], {
                'Content-Type': 'application/json'
            }
        )

    def test_exec_inspect(self):
        self.client.exec_inspect(fake_api.FAKE_EXEC_ID)

        args = fake_request.call_args
        self.assertEqual(
            args[0][1], url_prefix + 'exec/{0}/json'.format(
                fake_api.FAKE_EXEC_ID
            )
        )

    def test_exec_resize(self):
        self.client.exec_resize(fake_api.FAKE_EXEC_ID, height=20, width=60)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'exec/{0}/resize'.format(fake_api.FAKE_EXEC_ID),
            params={'h': 20, 'w': 60},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )
