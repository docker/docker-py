# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import base64
import contextlib
import json
import io
import os
import shutil
import signal
import socket
import tarfile
import tempfile
import threading
import time
import unittest
import warnings

import docker
import six

from six.moves import BaseHTTPServer
from six.moves import socketserver

from test import Cleanup

# FIXME: missing tests for
# export; history; insert; port; push; tag; get; load; stats
DEFAULT_BASE_URL = os.environ.get('DOCKER_HOST')
EXEC_DRIVER_IS_NATIVE = True

warnings.simplefilter('error')
create_host_config = docker.utils.create_host_config
compare_version = docker.utils.compare_version


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []
    tmp_folders = []

    def setUp(self):
        if six.PY2:
            self.assertRegex = self.assertRegexpMatches
            self.assertCountEqual = self.assertItemsEqual
        self.client = docker.Client(base_url=DEFAULT_BASE_URL, timeout=5)
        self.tmp_imgs = []
        self.tmp_containers = []
        self.tmp_folders = []

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
        for folder in self.tmp_folders:
            shutil.rmtree(folder)
        self.client.close()

#########################
#   INFORMATION TESTS   #
#########################


class TestVersion(BaseTestCase):
    def runTest(self):
        res = self.client.version()
        self.assertIn('GoVersion', res)
        self.assertIn('Version', res)
        self.assertEqual(len(res['Version'].split('.')), 3)


class TestInfo(BaseTestCase):
    def runTest(self):
        res = self.client.info()
        self.assertIn('Containers', res)
        self.assertIn('Images', res)
        self.assertIn('Debug', res)


class TestSearch(BaseTestCase):
    def runTest(self):
        self.client = docker.Client(base_url=DEFAULT_BASE_URL, timeout=10)
        res = self.client.search('busybox')
        self.assertTrue(len(res) >= 1)
        base_img = [x for x in res if x['name'] == 'busybox']
        self.assertEqual(len(base_img), 1)
        self.assertIn('description', base_img[0])

###################
#  LISTING TESTS  #
###################


class TestImages(BaseTestCase):
    def runTest(self):
        res1 = self.client.images(all=True)
        self.assertIn('Id', res1[0])
        res10 = res1[0]
        self.assertIn('Created', res10)
        self.assertIn('RepoTags', res10)
        distinct = []
        for img in res1:
            if img['Id'] not in distinct:
                distinct.append(img['Id'])
        self.assertEqual(len(distinct), self.client.info()['Images'])


class TestImageIds(BaseTestCase):
    def runTest(self):
        res1 = self.client.images(quiet=True)
        self.assertEqual(type(res1[0]), six.text_type)


class TestListContainers(BaseTestCase):
    def runTest(self):
        res0 = self.client.containers(all=True)
        size = len(res0)
        res1 = self.client.create_container('busybox:latest', 'true')
        self.assertIn('Id', res1)
        self.client.start(res1['Id'])
        self.tmp_containers.append(res1['Id'])
        res2 = self.client.containers(all=True)
        self.assertEqual(size + 1, len(res2))
        retrieved = [x for x in res2 if x['Id'].startswith(res1['Id'])]
        self.assertEqual(len(retrieved), 1)
        retrieved = retrieved[0]
        self.assertIn('Command', retrieved)
        self.assertEqual(retrieved['Command'], six.text_type('true'))
        self.assertIn('Image', retrieved)
        self.assertRegex(retrieved['Image'], r'busybox:.*')
        self.assertIn('Status', retrieved)

#####################
#  CONTAINER TESTS  #
#####################


class TestCreateContainer(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])


class TestCreateContainerWithBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = tempfile.mkdtemp()
        self.tmp_folders.append(mount_origin)

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)
        binds = {
            mount_origin: {
                'bind': mount_dest,
                'ro': False,
            },
        }

        with open(shared_file, 'w'):
            container = self.client.create_container(
                'busybox',
                ['ls', mount_dest], volumes={mount_dest: {}},
                host_config=create_host_config(binds=binds)
            )
            container_id = container['Id']
            self.client.start(container_id)
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn(filename, logs)
        inspect_data = self.client.inspect_container(container_id)
        self.assertIn('Volumes', inspect_data)
        self.assertIn(mount_dest, inspect_data['Volumes'])
        self.assertEqual(mount_origin, inspect_data['Volumes'][mount_dest])
        self.assertIn(mount_dest, inspect_data['VolumesRW'])
        self.assertTrue(inspect_data['VolumesRW'][mount_dest])


class TestCreateContainerWithRoBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = tempfile.mkdtemp()
        self.tmp_folders.append(mount_origin)

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)
        binds = {
            mount_origin: {
                'bind': mount_dest,
                'ro': True,
            },
        }

        with open(shared_file, 'w'):
            container = self.client.create_container(
                'busybox',
                ['ls', mount_dest], volumes={mount_dest: {}},
                host_config=create_host_config(binds=binds)
            )
            container_id = container['Id']
            self.client.start(container_id)
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn(filename, logs)
        inspect_data = self.client.inspect_container(container_id)
        self.assertIn('Volumes', inspect_data)
        self.assertIn(mount_dest, inspect_data['Volumes'])
        self.assertEqual(mount_origin, inspect_data['Volumes'][mount_dest])
        self.assertIn(mount_dest, inspect_data['VolumesRW'])
        self.assertFalse(inspect_data['VolumesRW'][mount_dest])


class TestStartContainerWithBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = tempfile.mkdtemp()
        self.tmp_folders.append(mount_origin)

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)
        binds = {
            mount_origin: {
                'bind': mount_dest,
                'ro': False,
            },
        }

        with open(shared_file, 'w'):
            container = self.client.create_container(
                'busybox', ['ls', mount_dest], volumes={mount_dest: {}}
            )
            container_id = container['Id']
            self.client.start(container_id, binds=binds)
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn(filename, logs)
        inspect_data = self.client.inspect_container(container_id)
        self.assertIn('Volumes', inspect_data)
        self.assertIn(mount_dest, inspect_data['Volumes'])
        self.assertEqual(mount_origin, inspect_data['Volumes'][mount_dest])
        self.assertIn(mount_dest, inspect_data['VolumesRW'])
        self.assertTrue(inspect_data['VolumesRW'][mount_dest])


class TestStartContainerWithRoBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = tempfile.mkdtemp()
        self.tmp_folders.append(mount_origin)

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)
        binds = {
            mount_origin: {
                'bind': mount_dest,
                'ro': True,
            },
        }

        with open(shared_file, 'w'):
            container = self.client.create_container(
                'busybox', ['ls', mount_dest], volumes={mount_dest: {}}
            )
            container_id = container['Id']
            self.client.start(container_id, binds=binds)
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn(filename, logs)

        inspect_data = self.client.inspect_container(container_id)
        self.assertIn('Volumes', inspect_data)
        self.assertIn(mount_dest, inspect_data['Volumes'])
        self.assertEqual(mount_origin, inspect_data['Volumes'][mount_dest])
        self.assertIn('VolumesRW', inspect_data)
        self.assertIn(mount_dest, inspect_data['VolumesRW'])
        self.assertFalse(inspect_data['VolumesRW'][mount_dest])


class TestStartContainerWithFileBind(BaseTestCase):
    def runTest(self):
        mount_dest = '/myfile/myfile'
        mount_origin = tempfile.mktemp()
        try:
            binds = {
                mount_origin: {
                    'bind': mount_dest,
                    'ro': True
                },
            }

            with open(mount_origin, 'w') as f:
                f.write('sakuya izayoi')

            container = self.client.create_container(
                'busybox', ['cat', mount_dest], volumes={mount_dest: {}}
            )
            self.client.start(container, binds=binds)
            exitcode = self.client.wait(container)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container)
            if six.PY3:
                logs = logs.decode('utf-8')
            self.assertIn('sakuya izayoi', logs)
        finally:
            os.unlink(mount_origin)


class TestCreateContainerWithLogConfig(BaseTestCase):
    def runTest(self):
        config = docker.utils.LogConfig(
            type=docker.utils.LogConfig.types.SYSLOG,
            config={'key1': 'val1'}
        )
        ctnr = self.client.create_container(
            'busybox', ['true'],
            host_config=create_host_config(log_config=config)
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        info = self.client.inspect_container(ctnr)
        self.assertIn('HostConfig', info)
        host_config = info['HostConfig']
        self.assertIn('LogConfig', host_config)
        log_config = host_config['LogConfig']
        self.assertIn('Type', log_config)
        self.assertEqual(log_config['Type'], config.type)
        self.assertIn('Config', log_config)
        self.assertEqual(type(log_config['Config']), dict)
        self.assertEqual(log_config['Config'], config.config)


@unittest.skipIf(not EXEC_DRIVER_IS_NATIVE, 'Exec driver not native')
class TestCreateContainerReadOnlyFs(BaseTestCase):
    def runTest(self):
        ctnr = self.client.create_container(
            'busybox', ['mkdir', '/shrine'],
            host_config=create_host_config(read_only=True)
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        res = self.client.wait(ctnr)
        self.assertNotEqual(res, 0)


@unittest.skipIf(not EXEC_DRIVER_IS_NATIVE, 'Exec driver not native')
class TestStartContainerReadOnlyFs(BaseTestCase):
    def runTest(self):
        # Presumably a bug in 1.5.0
        # https://github.com/docker/docker/issues/10695
        ctnr = self.client.create_container(
            'busybox', ['mkdir', '/shrine'],
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr, read_only=True)
        # res = self.client.wait(ctnr)
        # self.assertNotEqual(res, 0)


class TestCreateContainerWithName(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true', name='foobar')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Name', inspect)
        self.assertEqual('/foobar', inspect['Name'])


class TestRenameContainer(BaseTestCase):
    def runTest(self):
        version = self.client.version()['Version']
        name = 'hong_meiling'
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.rename(res, name)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Name', inspect)
        if version == '1.5.0':
            self.assertEqual(name, inspect['Name'])
        else:
            self.assertEqual('/{0}'.format(name), inspect['Name'])


class TestStartContainer(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)


class TestStartContainerWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)


class TestCreateContainerPrivileged(BaseTestCase):
    def runTest(self):
        res = self.client.create_container(
            'busybox', 'true', host_config=create_host_config(privileged=True)
        )
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)
        # Since Nov 2013, the Privileged flag is no longer part of the
        # container's config exposed via the API (safety concerns?).
        #
        if 'Privileged' in inspect['Config']:
            self.assertEqual(inspect['Config']['Privileged'], True)


class TestStartContainerPrivileged(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'], privileged=True)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)
        # Since Nov 2013, the Privileged flag is no longer part of the
        # container's config exposed via the API (safety concerns?).
        #
        if 'Privileged' in inspect['Config']:
            self.assertEqual(inspect['Config']['Privileged'], True)


class TestWait(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', ['sleep', '3'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        inspect = self.client.inspect_container(id)
        self.assertIn('Running', inspect['State'])
        self.assertEqual(inspect['State']['Running'], False)
        self.assertIn('ExitCode', inspect['State'])
        self.assertEqual(inspect['State']['ExitCode'], exitcode)


class TestWaitWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', ['sleep', '3'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(res)
        exitcode = self.client.wait(res)
        self.assertEqual(exitcode, 0)
        inspect = self.client.inspect_container(res)
        self.assertIn('Running', inspect['State'])
        self.assertEqual(inspect['State']['Running'], False)
        self.assertIn('ExitCode', inspect['State'])
        self.assertEqual(inspect['State']['ExitCode'], exitcode)


class TestLogs(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            'busybox', 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id)
        self.assertEqual(logs, (snippet + '\n').encode(encoding='ascii'))


class TestLogsWithTailOption(BaseTestCase):
    def runTest(self):
        snippet = '''Line1
Line2'''
        container = self.client.create_container(
            'busybox', 'echo "{0}"'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id, tail=1)
        self.assertEqual(logs, ('Line2\n').encode(encoding='ascii'))


# class TestLogsStreaming(BaseTestCase):
#     def runTest(self):
#         snippet = 'Flowering Nights (Sakuya Iyazoi)'
#         container = self.client.create_container(
#             'busybox', 'echo {0}'.format(snippet)
#         )
#         id = container['Id']
#         self.client.start(id)
#         self.tmp_containers.append(id)
#         logs = bytes() if six.PY3 else str()
#         for chunk in self.client.logs(id, stream=True):
#             logs += chunk

#         exitcode = self.client.wait(id)
#         self.assertEqual(exitcode, 0)

#         self.assertEqual(logs, (snippet + '\n').encode(encoding='ascii'))


class TestLogsWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            'busybox', 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(container)
        self.assertEqual(logs, (snippet + '\n').encode(encoding='ascii'))


class TestDiff(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        diff = self.client.diff(id)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        self.assertEqual(len(test_diff), 1)
        self.assertIn('Kind', test_diff[0])
        self.assertEqual(test_diff[0]['Kind'], 1)


class TestDiffWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        diff = self.client.diff(container)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        self.assertEqual(len(test_diff), 1)
        self.assertIn('Kind', test_diff[0])
        self.assertEqual(test_diff[0]['Kind'], 1)


class TestStop(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.stop(id, timeout=2)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if EXEC_DRIVER_IS_NATIVE:
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestStopWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        self.assertIn('Id', container)
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        self.client.stop(container, timeout=2)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if EXEC_DRIVER_IS_NATIVE:
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKill(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if EXEC_DRIVER_IS_NATIVE:
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKillWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(container)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if EXEC_DRIVER_IS_NATIVE:
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKillWithSignal(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '60'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id, signal=signal.SIGKILL)
        exitcode = self.client.wait(id)
        self.assertNotEqual(exitcode, 0)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False, state)


class TestPort(BaseTestCase):
    def runTest(self):

        port_bindings = {
            '1111': ('127.0.0.1', '4567'),
            '2222': ('127.0.0.1', '4568')
        }

        container = self.client.create_container(
            'busybox', ['sleep', '60'], ports=list(port_bindings.keys()),
            host_config=create_host_config(port_bindings=port_bindings)
        )
        id = container['Id']

        self.client.start(container)

        # Call the port function on each biding and compare expected vs actual
        for port in port_bindings:
            actual_bindings = self.client.port(container, port)
            port_binding = actual_bindings.pop()

            ip, host_port = port_binding['HostIp'], port_binding['HostPort']

            self.assertEqual(ip, port_bindings[port][0])
            self.assertEqual(host_port, port_bindings[port][1])

        self.client.kill(id)


class TestStartWithPortBindings(BaseTestCase):
    def runTest(self):

        port_bindings = {
            '1111': ('127.0.0.1', '4567'),
            '2222': ('127.0.0.1', '4568')
        }

        container = self.client.create_container(
            'busybox', ['sleep', '60'], ports=list(port_bindings.keys())
        )
        id = container['Id']

        self.client.start(container, port_bindings=port_bindings)

        # Call the port function on each biding and compare expected vs actual
        for port in port_bindings:
            actual_bindings = self.client.port(container, port)
            port_binding = actual_bindings.pop()

            ip, host_port = port_binding['HostIp'], port_binding['HostPort']

            self.assertEqual(ip, port_bindings[port][0])
            self.assertEqual(host_port, port_bindings[port][1])

        self.client.kill(id)


class TestMacAddress(BaseTestCase):
    def runTest(self):
        mac_address_expected = "02:42:ac:11:00:0a"
        container = self.client.create_container(
            'busybox', ['sleep', '60'], mac_address=mac_address_expected)

        id = container['Id']

        self.client.start(container)
        res = self.client.inspect_container(container['Id'])
        self.assertEqual(mac_address_expected,
                         res['NetworkSettings']['MacAddress'])

        self.client.kill(id)


class TestRestart(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        self.assertIn('State', info)
        self.assertIn('StartedAt', info['State'])
        start_time1 = info['State']['StartedAt']
        self.client.restart(id, timeout=2)
        info2 = self.client.inspect_container(id)
        self.assertIn('State', info2)
        self.assertIn('StartedAt', info2['State'])
        start_time2 = info2['State']['StartedAt']
        self.assertNotEqual(start_time1, start_time2)
        self.assertIn('Running', info2['State'])
        self.assertEqual(info2['State']['Running'], True)
        self.client.kill(id)


class TestRestartWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        self.assertIn('Id', container)
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        self.assertIn('State', info)
        self.assertIn('StartedAt', info['State'])
        start_time1 = info['State']['StartedAt']
        self.client.restart(container, timeout=2)
        info2 = self.client.inspect_container(id)
        self.assertIn('State', info2)
        self.assertIn('StartedAt', info2['State'])
        start_time2 = info2['State']['StartedAt']
        self.assertNotEqual(start_time1, start_time2)
        self.assertIn('Running', info2['State'])
        self.assertEqual(info2['State']['Running'], True)
        self.client.kill(id)


class TestRemoveContainer(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(id)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)


class TestRemoveContainerWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(container)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)


class TestCreateContainerWithVolumesFrom(BaseTestCase):
    def runTest(self):
        vol_names = ['foobar_vol0', 'foobar_vol1']

        res0 = self.client.create_container(
            'busybox', 'true', name=vol_names[0]
        )
        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        res1 = self.client.create_container(
            'busybox', 'true', name=vol_names[1]
        )
        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id)
        with self.assertRaises(docker.errors.DockerException):
            self.client.create_container(
                'busybox', 'cat', detach=True, stdin_open=True,
                volumes_from=vol_names
            )
        res2 = self.client.create_container(
            'busybox', 'cat', detach=True, stdin_open=True,
            host_config=create_host_config(volumes_from=vol_names)
        )
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)

        info = self.client.inspect_container(res2['Id'])
        self.assertCountEqual(info['HostConfig']['VolumesFrom'], vol_names)


class TestCreateContainerWithLinks(BaseTestCase):
    def runTest(self):
        res0 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)

        self.client.start(container1_id)

        res1 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)

        self.client.start(container2_id)

        # we don't want the first /
        link_path1 = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias1 = 'mylink1'
        link_env_prefix1 = link_alias1.upper()

        link_path2 = self.client.inspect_container(container2_id)['Name'][1:]
        link_alias2 = 'mylink2'
        link_env_prefix2 = link_alias2.upper()

        res2 = self.client.create_container(
            'busybox', 'env', host_config=create_host_config(
                links={link_path1: link_alias1, link_path2: link_alias2}
            )
        )
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)
        self.assertEqual(self.client.wait(container3_id), 0)

        logs = self.client.logs(container3_id)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn('{0}_NAME='.format(link_env_prefix1), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix1), logs)
        self.assertIn('{0}_NAME='.format(link_env_prefix2), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix2), logs)


class TestStartContainerWithVolumesFrom(BaseTestCase):
    def runTest(self):
        vol_names = ['foobar_vol0', 'foobar_vol1']

        res0 = self.client.create_container(
            'busybox', 'true',
            name=vol_names[0])
        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        res1 = self.client.create_container(
            'busybox', 'true',
            name=vol_names[1])
        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id)
        with self.assertRaises(docker.errors.DockerException):
            res2 = self.client.create_container(
                'busybox', 'cat',
                detach=True, stdin_open=True,
                volumes_from=vol_names)
        res2 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True)
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id, volumes_from=vol_names)

        info = self.client.inspect_container(res2['Id'])
        self.assertCountEqual(info['HostConfig']['VolumesFrom'], vol_names)


class TestStartContainerWithUlimits(BaseTestCase):
    def runTest(self):
        ulimit = docker.utils.Ulimit(name='nofile', soft=4096, hard=4096)

        res0 = self.client.create_container('busybox', 'true')
        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id, ulimits=[ulimit])

        info = self.client.inspect_container(container1_id)
        self.assertCountEqual(info['HostConfig']['Ulimits'], [ulimit])


class TestStartContainerWithLinks(BaseTestCase):
    def runTest(self):
        res0 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)

        self.client.start(container1_id)

        res1 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)

        self.client.start(container2_id)

        # we don't want the first /
        link_path1 = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias1 = 'mylink1'
        link_env_prefix1 = link_alias1.upper()

        link_path2 = self.client.inspect_container(container2_id)['Name'][1:]
        link_alias2 = 'mylink2'
        link_env_prefix2 = link_alias2.upper()

        res2 = self.client.create_container('busybox', 'env')
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(
            container3_id,
            links={link_path1: link_alias1, link_path2: link_alias2}
        )
        self.assertEqual(self.client.wait(container3_id), 0)

        logs = self.client.logs(container3_id)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn('{0}_NAME='.format(link_env_prefix1), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix1), logs)
        self.assertIn('{0}_NAME='.format(link_env_prefix2), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix2), logs)


class TestRestartingContainer(BaseTestCase):
    def runTest(self):
        container = self.client.create_container(
            'busybox', ['sleep', '2'], host_config=create_host_config(
                restart_policy={"Name": "always", "MaximumRetryCount": 0}
            )
        )
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        with self.assertRaises(docker.errors.APIError) as exc:
            self.client.remove_container(id)
        err = exc.exception.response.text
        self.assertIn(
            'You cannot remove a running container', err
        )
        self.client.remove_container(id, force=True)


@unittest.skipIf(not EXEC_DRIVER_IS_NATIVE, 'Exec driver not native')
class TestExecuteCommand(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, ['echo', 'hello'])
        self.assertIn('Id', res)

        exec_log = self.client.exec_start(res)
        expected = b'hello\n' if six.PY3 else 'hello\n'
        self.assertEqual(exec_log, expected)


@unittest.skipIf(not EXEC_DRIVER_IS_NATIVE, 'Exec driver not native')
class TestExecuteCommandString(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'echo hello world')
        self.assertIn('Id', res)

        exec_log = self.client.exec_start(res)
        expected = b'hello world\n' if six.PY3 else 'hello world\n'
        self.assertEqual(exec_log, expected)


@unittest.skipIf(not EXEC_DRIVER_IS_NATIVE, 'Exec driver not native')
class TestExecuteCommandStreaming(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(id, ['echo', 'hello\nworld'])
        self.assertIn('Id', exec_id)

        res = b'' if six.PY3 else ''
        for chunk in self.client.exec_start(exec_id, stream=True):
            res += chunk
        expected = b'hello\nworld\n' if six.PY3 else 'hello\nworld\n'
        self.assertEqual(res, expected)


@unittest.skipIf(not EXEC_DRIVER_IS_NATIVE, 'Exec driver not native')
class TestExecInspect(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(id, ['mkdir', '/does/not/exist'])
        self.assertIn('Id', exec_id)
        self.client.exec_start(exec_id)
        exec_info = self.client.exec_inspect(exec_id)
        self.assertIn('ExitCode', exec_info)
        self.assertNotEqual(exec_info['ExitCode'], 0)


class TestRunContainerStreaming(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', '/bin/sh',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        socket = self.client.attach_socket(container, ws=False)
        self.assertTrue(socket.fileno() > -1)


class TestPauseUnpauseContainer(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '9999'])
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(container)
        self.client.pause(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], True)
        self.assertIn('Paused', state)
        self.assertEqual(state['Paused'], True)

        self.client.unpause(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], True)
        self.assertIn('Paused', state)
        self.assertEqual(state['Paused'], False)


class TestCreateContainerWithHostPidMode(BaseTestCase):
    def runTest(self):
        ctnr = self.client.create_container(
            'busybox', 'true', host_config=create_host_config(
                pid_mode='host'
            )
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)
        self.assertIn('HostConfig', inspect)
        host_config = inspect['HostConfig']
        self.assertIn('PidMode', host_config)
        self.assertEqual(host_config['PidMode'], 'host')


class TestStartContainerWithHostPidMode(BaseTestCase):
    def runTest(self):
        ctnr = self.client.create_container(
            'busybox', 'true'
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr, pid_mode='host')
        inspect = self.client.inspect_container(ctnr)
        self.assertIn('HostConfig', inspect)
        host_config = inspect['HostConfig']
        self.assertIn('PidMode', host_config)
        self.assertEqual(host_config['PidMode'], 'host')

#################
#  LINKS TESTS  #
#################


class TestRemoveLink(BaseTestCase):
    def runTest(self):
        # Create containers
        container1 = self.client.create_container(
            'busybox', 'cat', detach=True, stdin_open=True
        )
        container1_id = container1['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        # Create Link
        # we don't want the first /
        link_path = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias = 'mylink'

        container2 = self.client.create_container(
            'busybox', 'cat', host_config=create_host_config(
                links={link_path: link_alias}
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

##################
#  IMAGES TESTS  #
##################


class TestPull(BaseTestCase):
    def runTest(self):
        self.client.close()
        self.client = docker.Client(base_url=DEFAULT_BASE_URL, timeout=10)
        try:
            self.client.remove_image('busybox')
        except docker.errors.APIError:
            pass
        res = self.client.pull('busybox')
        self.assertEqual(type(res), six.text_type)
        self.assertGreaterEqual(
            len(self.client.images('busybox')), 1
        )
        img_info = self.client.inspect_image('busybox')
        self.assertIn('Id', img_info)


class TestPullStream(BaseTestCase):
    def runTest(self):
        self.client.close()
        self.client = docker.Client(base_url=DEFAULT_BASE_URL, timeout=10)
        try:
            self.client.remove_image('busybox')
        except docker.errors.APIError:
            pass
        stream = self.client.pull('busybox', stream=True)
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
        self.assertGreaterEqual(
            len(self.client.images('busybox')), 1
        )
        img_info = self.client.inspect_image('busybox')
        self.assertIn('Id', img_info)


class TestCommit(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res = self.client.commit(id)
        self.assertIn('Id', res)
        img_id = res['Id']
        self.tmp_imgs.append(img_id)
        img = self.client.inspect_image(img_id)
        self.assertIn('Container', img)
        self.assertTrue(img['Container'].startswith(id))
        self.assertIn('ContainerConfig', img)
        self.assertIn('Image', img['ContainerConfig'])
        self.assertEqual('busybox', img['ContainerConfig']['Image'])
        busybox_id = self.client.inspect_image('busybox')['Id']
        self.assertIn('Parent', img)
        self.assertEqual(img['Parent'], busybox_id)


class TestRemoveImage(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res = self.client.commit(id)
        self.assertIn('Id', res)
        img_id = res['Id']
        self.tmp_imgs.append(img_id)
        self.client.remove_image(img_id, force=True)
        images = self.client.images(all=True)
        res = [x for x in images if x['Id'].startswith(img_id)]
        self.assertEqual(len(res), 0)


##################
#  IMPORT TESTS  #
##################


class ImportTestCase(BaseTestCase):
    '''Base class for `docker import` test cases.'''

    # Use a large file size to increase the chance of triggering any
    # MemoryError exceptions we might hit.
    TAR_SIZE = 512 * 1024 * 1024

    def write_dummy_tar_content(self, n_bytes, tar_fd):
        def extend_file(f, n_bytes):
            f.seek(n_bytes - 1)
            f.write(bytearray([65]))
            f.seek(0)

        tar = tarfile.TarFile(fileobj=tar_fd, mode='w')

        with tempfile.NamedTemporaryFile() as f:
            extend_file(f, n_bytes)
            tarinfo = tar.gettarinfo(name=f.name, arcname='testdata')
            tar.addfile(tarinfo, fileobj=f)

        tar.close()

    @contextlib.contextmanager
    def dummy_tar_stream(self, n_bytes):
        '''Yields a stream that is valid tar data of size n_bytes.'''
        with tempfile.NamedTemporaryFile() as tar_file:
            self.write_dummy_tar_content(n_bytes, tar_file)
            tar_file.seek(0)
            yield tar_file

    @contextlib.contextmanager
    def dummy_tar_file(self, n_bytes):
        '''Yields the name of a valid tar file of size n_bytes.'''
        with tempfile.NamedTemporaryFile() as tar_file:
            self.write_dummy_tar_content(n_bytes, tar_file)
            tar_file.seek(0)
            yield tar_file.name


class TestImportFromBytes(ImportTestCase):
    '''Tests importing an image from in-memory byte data.'''

    def runTest(self):
        with self.dummy_tar_stream(n_bytes=500) as f:
            content = f.read()

        # The generic import_image() function cannot import in-memory bytes
        # data that happens to be represented as a string type, because
        # import_image() will try to use it as a filename and usually then
        # trigger an exception. So we test the import_image_from_data()
        # function instead.
        statuses = self.client.import_image_from_data(
            content, repository='test/import-from-bytes')

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        img_id = result['status']
        self.tmp_imgs.append(img_id)


class TestImportFromFile(ImportTestCase):
    '''Tests importing an image from a tar file on disk.'''

    def runTest(self):
        with self.dummy_tar_file(n_bytes=self.TAR_SIZE) as tar_filename:
            # statuses = self.client.import_image(
            #     src=tar_filename, repository='test/import-from-file')
            statuses = self.client.import_image_from_file(
                tar_filename, repository='test/import-from-file')

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        self.assertIn('status', result)
        img_id = result['status']
        self.tmp_imgs.append(img_id)


class TestImportFromStream(ImportTestCase):
    '''Tests importing an image from a stream containing tar data.'''

    def runTest(self):
        with self.dummy_tar_stream(n_bytes=self.TAR_SIZE) as tar_stream:
            statuses = self.client.import_image(
                src=tar_stream, repository='test/import-from-stream')
            # statuses = self.client.import_image_from_stream(
            #     tar_stream, repository='test/import-from-stream')
        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        self.assertIn('status', result)
        img_id = result['status']
        self.tmp_imgs.append(img_id)


class TestImportFromURL(ImportTestCase):
    '''Tests downloading an image over HTTP.'''

    @contextlib.contextmanager
    def temporary_http_file_server(self, stream):
        '''Serve data from an IO stream over HTTP.'''

        class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-tar')
                self.end_headers()
                shutil.copyfileobj(stream, self.wfile)

        server = socketserver.TCPServer(('', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.setDaemon(True)
        thread.start()

        yield 'http://%s:%s' % (socket.gethostname(), server.server_address[1])

        server.shutdown()

    def runTest(self):
        # The crappy test HTTP server doesn't handle large files well, so use
        # a small file.
        TAR_SIZE = 10240

        with self.dummy_tar_stream(n_bytes=TAR_SIZE) as tar_data:
            with self.temporary_http_file_server(tar_data) as url:
                statuses = self.client.import_image(
                    src=url, repository='test/import-from-url')

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        self.assertIn('status', result)
        img_id = result['status']
        self.tmp_imgs.append(img_id)


#################
# BUILDER TESTS #
#################


class TestBuild(BaseTestCase):
    def runTest(self):
        if compare_version(self.client._version, '1.8') < 0:
            return
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        img, logs = self.client.build(fileobj=script)
        self.assertNotEqual(img, None)
        self.assertNotEqual(img, '')
        self.assertNotEqual(logs, '')
        container1 = self.client.create_container(img, 'test -d /tmp/test')
        id1 = container1['Id']
        self.client.start(id1)
        self.tmp_containers.append(id1)
        exitcode1 = self.client.wait(id1)
        self.assertEqual(exitcode1, 0)
        container2 = self.client.create_container(img, 'test -d /tmp/test')
        id2 = container2['Id']
        self.client.start(id2)
        self.tmp_containers.append(id2)
        exitcode2 = self.client.wait(id2)
        self.assertEqual(exitcode2, 0)
        self.tmp_imgs.append(img)


class TestBuildStream(BaseTestCase):
    def runTest(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
            logs += chunk
        self.assertNotEqual(logs, '')


class TestBuildFromStringIO(BaseTestCase):
    def runTest(self):
        if six.PY3:
            return
        script = io.StringIO(six.text_type('\n').join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]))
        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            logs += chunk
        self.assertNotEqual(logs, '')


class TestBuildWithDockerignore(Cleanup, BaseTestCase):
    def runTest(self):
        if compare_version(self.client._version, '1.8') >= 0:
            return

        base_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_dir)

        with open(os.path.join(base_dir, 'Dockerfile'), 'w') as f:
            f.write("\n".join([
                'FROM busybox',
                'MAINTAINER docker-py',
                'ADD . /test',
                'RUN ls -A /test',
            ]))

        with open(os.path.join(base_dir, '.dockerignore'), 'w') as f:
            f.write("\n".join([
                'node_modules',
                'Dockerfile',
                '.dockerginore',
                '',  # empty line
            ]))

        with open(os.path.join(base_dir, 'not-ignored'), 'w') as f:
            f.write("this file should not be ignored")

        subdir = os.path.join(base_dir, 'node_modules', 'grunt-cli')
        os.makedirs(subdir)
        with open(os.path.join(subdir, 'grunt'), 'w') as f:
            f.write("grunt")

        stream = self.client.build(path=base_dir, stream=True)
        logs = ''
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            logs += chunk
        self.assertFalse('node_modules' in logs)
        self.assertFalse('Dockerfile' in logs)
        self.assertFalse('.dockerginore' in logs)
        self.assertTrue('not-ignored' in logs)

#######################
#  PY SPECIFIC TESTS  #
#######################


class TestRunShlex(BaseTestCase):
    def runTest(self):
        commands = [
            'true',
            'echo "The Young Descendant of Tepes & Septette for the '
            'Dead Princess"',
            'echo -n "The Young Descendant of Tepes & Septette for the '
            'Dead Princess"',
            '/bin/sh -c "echo Hello World"',
            '/bin/sh -c \'echo "Hello World"\'',
            'echo "\"Night of Nights\""',
            'true && echo "Night of Nights"'
        ]
        for cmd in commands:
            container = self.client.create_container('busybox', cmd)
            id = container['Id']
            self.client.start(id)
            self.tmp_containers.append(id)
            exitcode = self.client.wait(id)
            self.assertEqual(exitcode, 0, msg=cmd)


class TestLoadConfig(BaseTestCase):
    def runTest(self):
        folder = tempfile.mkdtemp()
        self.tmp_folders.append(folder)
        cfg_path = os.path.join(folder, '.dockercfg')
        f = open(cfg_path, 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(cfg_path)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


class TestLoadJSONConfig(BaseTestCase):
    def runTest(self):
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


class TestAutoDetectVersion(unittest.TestCase):
    def test_client_init(self):
        client = docker.Client(version='auto')
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()

    def test_auto_client(self):
        client = docker.AutoVersionClient()
        client_version = client._version
        api_version = client.version(api_version=False)['ApiVersion']
        self.assertEqual(client_version, api_version)
        api_version_2 = client.version()['ApiVersion']
        self.assertEqual(client_version, api_version_2)
        client.close()
        with self.assertRaises(docker.errors.DockerException):
            docker.AutoVersionClient(version='1.11')


class TestConnectionTimeout(unittest.TestCase):
    def setUp(self):
        self.timeout = 0.5
        self.client = docker.client.Client(base_url='http://192.168.10.2:4243',
                                           timeout=self.timeout)

    def runTest(self):
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


class UnixconnTestCase(unittest.TestCase):
    """
    Test UNIX socket connection adapter.
    """

    def test_resource_warnings(self):
        """
        Test no warnings are produced when using the client.
        """

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')

            client = docker.Client(base_url=DEFAULT_BASE_URL)
            client.images()
            client.close()
            del client

            assert len(w) == 0, \
                "No warnings produced: {0}".format(w[0].message)


####################
# REGRESSION TESTS #
####################

class TestRegressions(BaseTestCase):
    def test_443(self):
        dfile = io.BytesIO()
        with self.assertRaises(docker.errors.APIError) as exc:
            for line in self.client.build(fileobj=dfile, tag="a/b/c"):
                pass
        self.assertEqual(exc.exception.response.status_code, 500)
        dfile.close()

    def test_542(self):
        self.client.start(
            self.client.create_container('busybox', ['true'])
        )
        result = self.client.containers(trunc=True)
        self.assertEqual(len(result[0]['Id']), 12)


if __name__ == '__main__':
    c = docker.Client(base_url=DEFAULT_BASE_URL)
    c.pull('busybox')
    exec_driver = c.info()['ExecutionDriver']
    EXEC_DRIVER_IS_NATIVE = exec_driver.startswith('native')
    c.close()
    unittest.main()
