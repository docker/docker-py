import base64
import os
import tempfile
import time
import unittest
import warnings

import docker

from .. import helpers


class InformationTest(helpers.BaseTestCase):
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

    def test_search(self):
        self.client = helpers.docker_client(timeout=10)
        res = self.client.search('busybox')
        self.assertTrue(len(res) >= 1)
        base_img = [x for x in res if x['name'] == 'busybox']
        self.assertEqual(len(base_img), 1)
        self.assertIn('description', base_img[0])


class LinkTest(helpers.BaseTestCase):
    def test_remove_link(self):
        # Create containers
        container1 = self.client.create_container(
            helpers.BUSYBOX, 'cat', detach=True, stdin_open=True
        )
        container1_id = container1['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        # Create Link
        # we don't want the first /
        link_path = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias = 'mylink'

        container2 = self.client.create_container(
            helpers.BUSYBOX, 'cat', host_config=self.client.create_host_config(
                links={link_path: link_alias}, network_mode='none'
            )
        )
        container2_id = container2['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id)

        # Remove link
        linked_name = self.client.inspect_container(container2_id)['Name'][1:]
        link_name = '%s/%s' % (linked_name, link_alias)
        self.client.remove_container(link_name, link=True)

        # Link is gone
        containers = self.client.containers(all=True)
        retrieved = [x for x in containers if link_name in x['Names']]
        self.assertEqual(len(retrieved), 0)

        # Containers are still there
        retrieved = [
            x for x in containers if x['Id'].startswith(container1_id) or
            x['Id'].startswith(container2_id)
        ]
        self.assertEqual(len(retrieved), 2)


class LoadConfigTest(helpers.BaseTestCase):
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
        client = helpers.docker_client(version='auto')
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()

    def test_auto_client(self):
        client = docker.AutoVersionClient(**helpers.docker_client_kwargs())
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()
        with self.assertRaises(docker.errors.DockerException):
            docker.AutoVersionClient(
                **helpers.docker_client_kwargs(version='1.11')
            )


class ConnectionTimeoutTest(unittest.TestCase):
    def setUp(self):
        self.timeout = 0.5
        self.client = docker.client.Client(base_url='http://192.168.10.2:4243',
                                           timeout=self.timeout)

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

            client = helpers.docker_client()
            client.images()
            client.close()
            del client

            assert len(w) == 0, \
                "No warnings produced: {0}".format(w[0].message)
