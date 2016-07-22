import docker
import pytest

from . import fake_api
from docker import auth
from .api_test import (
    DockerClientTest, fake_request, DEFAULT_TIMEOUT_SECONDS, url_prefix,
    fake_resolve_authconfig
)

try:
    from unittest import mock
except ImportError:
    import mock


class ImageTest(DockerClientTest):
    def test_image_viz(self):
        with pytest.raises(Exception):
            self.client.images('busybox', viz=True)
            self.fail('Viz output should not be supported!')

    def test_images(self):
        self.client.images(all=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 0, 'all': 1},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_quiet(self):
        self.client.images(all=True, quiet=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 1, 'all': 1},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_ids(self):
        self.client.images(quiet=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 1, 'all': 0},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_filters(self):
        self.client.images(filters={'dangling': True})

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 0, 'all': 0,
                    'filters': '{"dangling": ["true"]}'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_pull(self):
        self.client.pull('joffrey/test001')

        args = fake_request.call_args
        self.assertEqual(
            args[0][1],
            url_prefix + 'images/create'
        )
        self.assertEqual(
            args[1]['params'],
            {'tag': None, 'fromImage': 'joffrey/test001'}
        )
        self.assertFalse(args[1]['stream'])

    def test_pull_stream(self):
        self.client.pull('joffrey/test001', stream=True)

        args = fake_request.call_args
        self.assertEqual(
            args[0][1],
            url_prefix + 'images/create'
        )
        self.assertEqual(
            args[1]['params'],
            {'tag': None, 'fromImage': 'joffrey/test001'}
        )
        self.assertTrue(args[1]['stream'])

    def test_commit(self):
        self.client.commit(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'commit',
            data='{}',
            headers={'Content-Type': 'application/json'},
            params={
                'repo': None,
                'comment': None,
                'tag': None,
                'container': '3cc2351ab11b',
                'author': None,
                'changes': None
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_image(self):
        self.client.remove_image(fake_api.FAKE_IMAGE_ID)

        fake_request.assert_called_with(
            'DELETE',
            url_prefix + 'images/e9aa60c60128',
            params={'force': False, 'noprune': False},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_history(self):
        self.client.history(fake_api.FAKE_IMAGE_NAME)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/test_image/history',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image(self):
        self.client.import_image(
            fake_api.FAKE_TARBALL_PATH,
            repository=fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': fake_api.FAKE_TARBALL_PATH
            },
            data=None,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image_from_bytes(self):
        stream = (i for i in range(0, 100))

        self.client.import_image(
            stream,
            repository=fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': '-',
            },
            headers={
                'Content-Type': 'application/tar',
            },
            data=stream,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image_from_image(self):
        self.client.import_image(
            image=fake_api.FAKE_IMAGE_NAME,
            repository=fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromImage': fake_api.FAKE_IMAGE_NAME
            },
            data=None,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_image(self):
        self.client.inspect_image(fake_api.FAKE_IMAGE_NAME)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/test_image/json',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_image_undefined_id(self):
        for arg in None, '', {True: True}:
            with pytest.raises(docker.errors.NullResource) as excinfo:
                self.client.inspect_image(arg)

            self.assertEqual(
                excinfo.value.args[0], 'image or container param is undefined'
            )

    def test_insert_image(self):
        try:
            self.client.insert(fake_api.FAKE_IMAGE_NAME,
                               fake_api.FAKE_URL, fake_api.FAKE_PATH)
        except docker.errors.DeprecatedMethod:
            self.assertTrue(
                docker.utils.compare_version('1.12', self.client._version) >= 0
            )
            return

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/test_image/insert',
            params={
                'url': fake_api.FAKE_URL,
                'path': fake_api.FAKE_PATH
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image(self):
        with mock.patch('docker.auth.auth.resolve_authconfig',
                        fake_resolve_authconfig):
            self.client.push(fake_api.FAKE_IMAGE_NAME)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/test_image/push',
            params={
                'tag': None
            },
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=False,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_with_tag(self):
        with mock.patch('docker.auth.auth.resolve_authconfig',
                        fake_resolve_authconfig):
            self.client.push(
                fake_api.FAKE_IMAGE_NAME, tag=fake_api.FAKE_TAG_NAME
            )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/test_image/push',
            params={
                'tag': fake_api.FAKE_TAG_NAME,
            },
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=False,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_with_auth(self):
        auth_config = {
            'username': "test_user",
            'password': "test_password",
            'serveraddress': "test_server",
        }
        encoded_auth = auth.encode_header(auth_config)
        self.client.push(
                fake_api.FAKE_IMAGE_NAME, tag=fake_api.FAKE_TAG_NAME,
                auth_config=auth_config
                )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/test_image/push',
            params={
                'tag': fake_api.FAKE_TAG_NAME,
            },
            data='{}',
            headers={'Content-Type': 'application/json',
                     'X-Registry-Auth': encoded_auth},
            stream=False,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_stream(self):
        with mock.patch('docker.auth.auth.resolve_authconfig',
                        fake_resolve_authconfig):
            self.client.push(fake_api.FAKE_IMAGE_NAME, stream=True)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/test_image/push',
            params={
                'tag': None
            },
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image(self):
        self.client.tag(fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': None,
                'repo': 'repo',
                'force': 0
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_tag(self):
        self.client.tag(
            fake_api.FAKE_IMAGE_ID,
            fake_api.FAKE_REPO_NAME,
            tag=fake_api.FAKE_TAG_NAME
        )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': 'tag',
                'repo': 'repo',
                'force': 0
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_force(self):
        self.client.tag(
            fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME, force=True)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': None,
                'repo': 'repo',
                'force': 1
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_get_image(self):
        self.client.get_image(fake_api.FAKE_IMAGE_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/e9aa60c60128/get',
            stream=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_load_image(self):
        self.client.load_image('Byte Stream....')

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'images/load',
            data='Byte Stream....',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )
