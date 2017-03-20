import base64
import os
import tempfile
import time
import unittest
import warnings

import docker
from docker.utils import kwargs_from_env

from .base import BaseAPIIntegrationTest


class InformationTest(BaseAPIIntegrationTest):
    def test_version(self):
        res = self.client.version()
        self.assertIn('GoVersion', res)
        self.assertIn('Version', res)
        self.assertEqual(len(res['Version'].split('.')), 3)

    def test_info(self):
        res = self.client.info()
        self.assertIn('Containers', res)
        self.assertIn('Images', res)
        self.assertIn('Debug', res)


class LoadConfigTest(BaseAPIIntegrationTest):
    def test_load_legacy_config(self):
        folder = tempfile.mkdtemp()
        self.tmp_folders.append(folder)
        cfg_path = os.path.join(folder, '.dockercfg')
        f = open(cfg_path, 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(cfg_path)
        self.assertNotEqual(cfg[docker.auth.INDEX_NAME], None)
        cfg = cfg[docker.auth.INDEX_NAME]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)

    def test_load_json_config(self):
        folder = tempfile.mkdtemp()
        self.tmp_folders.append(folder)
        cfg_path = os.path.join(folder, '.dockercfg')
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        email_ = 'sakuya@scarlet.net'
        f.write('{{"{0}": {{"auth": "{1}", "email": "{2}"}}}}\n'.format(
            docker.auth.INDEX_URL, auth_, email_))
        f.close()
        cfg = docker.auth.load_config(cfg_path)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


class AutoDetectVersionTest(unittest.TestCase):
    def test_client_init(self):
        client = docker.APIClient(version='auto', **kwargs_from_env())
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()


class ConnectionTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.timeout = 0.5
        self.client = docker.api.APIClient(
            version=docker.constants.MINIMUM_DOCKER_API_VERSION,
            base_url='http://192.168.10.2:4243',
            timeout=self.timeout
        )

    def test_timeout(self):
        start = time.time()
        res = None
        # This call isn't supposed to complete, and it should fail fast.
        try:
            res = self.client.inspect_container('id')
        except:
            pass
        end = time.time()
        self.assertTrue(res is None)
        self.assertTrue(end - start < 2 * self.timeout)


class UnixconnTest(unittest.TestCase):
    """
    Test UNIX socket connection adapter.
    """

    def test_resource_warnings(self):
        """
        Test no warnings are produced when using the client.
        """

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            client = docker.APIClient(version='auto', **kwargs_from_env())
            client.images()
            client.close()
            del client

            assert len(w) == 0, \
                "No warnings produced: {0}".format(w[0].message)
