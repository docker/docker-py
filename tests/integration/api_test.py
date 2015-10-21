import base64
import json
import os
import shutil
import tempfile
import time
import unittest
import warnings

import docker
import six

BUSYBOX = 'busybox:buildroot-2014.02'
EXEC_DRIVER = []


def exec_driver_is_native():
    global EXEC_DRIVER
    if not EXEC_DRIVER:
        c = docker_client()
        EXEC_DRIVER = c.info()['ExecutionDriver']
        c.close()
    return EXEC_DRIVER.startswith('native')


def docker_client(**kwargs):
    return docker.Client(**docker_client_kwargs(**kwargs))


def docker_client_kwargs(**kwargs):
    client_kwargs = docker.utils.kwargs_from_env(assert_hostname=False)
    client_kwargs.update(kwargs)
    return client_kwargs


def setup_module():
    warnings.simplefilter('error')
    c = docker_client()
    try:
        c.inspect_image(BUSYBOX)
    except docker.errors.NotFound:
        os.write(2, "\npulling busybox\n".encode('utf-8'))
        for data in c.pull(BUSYBOX, stream=True):
            data = json.loads(data.decode('utf-8'))
            os.write(2, ("%c[2K\r" % 27).encode('utf-8'))
            status = data.get("status")
            progress = data.get("progress")
            detail = "{0} - {1}".format(status, progress).encode('utf-8')
            os.write(2, detail)
        os.write(2, "\npulled busybox\n".encode('utf-8'))

        # Double make sure we now have busybox
        c.inspect_image(BUSYBOX)
    c.close()


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []
    tmp_folders = []
    tmp_volumes = []

    def setUp(self):
        if six.PY2:
            self.assertRegex = self.assertRegexpMatches
            self.assertCountEqual = self.assertItemsEqual
        self.client = docker_client(timeout=60)
        self.tmp_imgs = []
        self.tmp_containers = []
        self.tmp_folders = []
        self.tmp_volumes = []
        self.tmp_networks = []

    def tearDown(self):
        for img in self.tmp_imgs:
            try:
                self.client.remove_image(img)
            except docker.errors.APIError:
                pass
        for container in self.tmp_containers:
            try:
                self.client.stop(container, timeout=1)
                self.client.remove_container(container)
            except docker.errors.APIError:
                pass
        for network in self.tmp_networks:
            try:
                self.client.remove_network(network)
            except docker.errors.APIError:
                pass
        for folder in self.tmp_folders:
            shutil.rmtree(folder)

        for volume in self.tmp_volumes:
            try:
                self.client.remove_volume(volume)
            except docker.errors.APIError:
                pass

        self.client.close()

    def run_container(self, *args, **kwargs):
        container = self.client.create_container(*args, **kwargs)
        self.tmp_containers.append(container)
        self.client.start(container)
        exitcode = self.client.wait(container)

        if exitcode != 0:
            output = self.client.logs(container)
            raise Exception(
                "Container exited with code {}:\n{}"
                .format(exitcode, output))

        return container


#########################
#   INFORMATION TESTS   #
#########################


class InformationTest(BaseTestCase):
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
        self.client = docker_client(timeout=10)
        res = self.client.search('busybox')
        self.assertTrue(len(res) >= 1)
        base_img = [x for x in res if x['name'] == 'busybox']
        self.assertEqual(len(base_img), 1)
        self.assertIn('description', base_img[0])


#################
#  LINKS TESTS  #
#################


class LinkTest(BaseTestCase):
    def test_remove_link(self):
        # Create containers
        container1 = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True
        )
        container1_id = container1['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        # Create Link
        # we don't want the first /
        link_path = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias = 'mylink'

        container2 = self.client.create_container(
            BUSYBOX, 'cat', host_config=self.client.create_host_config(
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


#######################
#  PY SPECIFIC TESTS  #
#######################

class LoadConfigTest(BaseTestCase):
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
        client = docker_client(version='auto')
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()

    def test_auto_client(self):
        client = docker.AutoVersionClient(**docker_client_kwargs())
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()
        with self.assertRaises(docker.errors.DockerException):
            docker.AutoVersionClient(**docker_client_kwargs(version='1.11'))


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

            client = docker_client()
            client.images()
            client.close()
            del client

            assert len(w) == 0, \
                "No warnings produced: {0}".format(w[0].message)
