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

import time
import base64
import json
import io
import os
import signal
import tempfile
import unittest

import docker
import six

# FIXME: missing tests for
# export; history; import_image; insert; port; push; tag


class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []

    def setUp(self):
        self.client = docker.Client()
        self.client.pull('busybox')
        self.tmp_imgs = []
        self.tmp_containers = []

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
        res1 = self.client.create_container('busybox', 'true;')
        self.assertIn('Id', res1)
        self.client.start(res1['Id'])
        self.tmp_containers.append(res1['Id'])
        res2 = self.client.containers(all=True)
        self.assertEqual(size + 1, len(res2))
        retrieved = [x for x in res2 if x['Id'].startswith(res1['Id'])]
        self.assertEqual(len(retrieved), 1)
        retrieved = retrieved[0]
        self.assertIn('Command', retrieved)
        self.assertEqual(retrieved['Command'], 'true;')
        self.assertIn('Image', retrieved)
        self.assertEqual(retrieved['Image'], 'busybox:latest')
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
        mount_origin = '/tmp'

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)

        with open(shared_file, 'w'):
            container = self.client.create_container(
                'busybox',
                ['ls', mount_dest], volumes={mount_dest: {}}
            )
            container_id = container['Id']
            self.client.start(
                container_id,
                binds={
                    mount_origin: {
                        'bind': mount_dest,
                        'ro': False,
                    },
                },
            )
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        self.assertIn(filename, logs)


class TestCreateContainerWithName(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true', name='foobar')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Name', inspect)
        self.assertEqual('/foobar', inspect['Name'])


class TestStartContainer(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('ID', inspect)
        self.assertTrue(inspect['ID'].startswith(res['Id']))
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
        self.assertIn('ID', inspect)
        self.assertTrue(inspect['ID'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)


class TestStartContainerPrivileged(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'], privileged=True)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('ID', inspect)
        self.assertTrue(inspect['ID'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)
        # Since Nov 2013, the Privileged flag is no longer part of the
        # container's config exposed via the API (safety concerns?).
        #
        # self.assertEqual(inspect['Config']['Privileged'], True)


class TestWait(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', ['sleep', '10'])
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
        res = self.client.create_container('busybox', ['sleep', '10'])
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
        self.assertEqual(logs, snippet + '\n')


class TestLogsStreaming(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            'busybox', 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        logs = ''
        for chunk in self.client.logs(id, stream=True):
            logs += chunk

        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)

        self.assertEqual(logs, snippet + '\n')


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
        self.assertEqual(logs, snippet + '\n')


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
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class TestKillWithSignal(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['sleep', '60'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id, signal=signal.SIGTERM)
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
            1111: ('127.0.0.1', '4567'),
            2222: ('127.0.0.1', '4568')
        }

        container = self.client.create_container(
            'busybox', ['sleep', '60'], ports=port_bindings.keys()
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

        res2 = self.client.create_container(
            'busybox', 'cat',
            detach=True, stdin_open=True,
            volumes_from=vol_names)
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)

        info = self.client.inspect_container(res2['Id'])
        self.assertEqual(info['Config']['VolumesFrom'], ','.join(vol_names))


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
        self.assertIn('{0}_NAME='.format(link_env_prefix1), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix1), logs)
        self.assertIn('{0}_NAME='.format(link_env_prefix2), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix2), logs)

#################
#  LINKS TESTS  #
#################


class TestRemoveLink(BaseTestCase):
    def runTest(self):
        # Create containers
        container1 = self.client.create_container(
            'busybox', 'cat', detach=True, stdin_open=True)
        container1_id = container1['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        # Create Link
        # we don't want the first /
        link_path = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias = 'mylink'

        container2 = self.client.create_container('busybox', 'cat')
        container2_id = container2['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id, links={link_path: link_alias})

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
            x for x in containers if x['Id'].startswith(container1_id)
            or x['Id'].startswith(container2_id)
        ]
        self.assertEqual(len(retrieved), 2)

##################
#  IMAGES TESTS  #
##################


class TestPull(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_image('joffrey/test001')
            self.client.remove_image('376968a23351')
        except docker.errors.APIError:
            pass
        info = self.client.info()
        self.assertIn('Images', info)
        img_count = info['Images']
        res = self.client.pull('joffrey/test001')
        self.assertEqual(type(res), six.text_type)
        self.assertEqual(img_count + 3, self.client.info()['Images'])
        img_info = self.client.inspect_image('joffrey/test001')
        self.assertIn('id', img_info)
        self.tmp_imgs.append('joffrey/test001')
        self.tmp_imgs.append('376968a23351')


class TestPullStream(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_image('joffrey/test001')
            self.client.remove_image('376968a23351')
        except docker.errors.APIError:
            pass
        info = self.client.info()
        self.assertIn('Images', info)
        img_count = info['Images']
        stream = self.client.pull('joffrey/test001', stream=True)
        for chunk in stream:
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
        self.assertEqual(img_count + 3, self.client.info()['Images'])
        img_info = self.client.inspect_image('joffrey/test001')
        self.assertIn('id', img_info)
        self.tmp_imgs.append('joffrey/test001')
        self.tmp_imgs.append('376968a23351')


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
        self.assertIn('container', img)
        self.assertTrue(img['container'].startswith(id))
        self.assertIn('container_config', img)
        self.assertIn('Image', img['container_config'])
        self.assertEqual('busybox', img['container_config']['Image'])
        busybox_id = self.client.inspect_image('busybox')['id']
        self.assertIn('parent', img)
        self.assertEqual(img['parent'], busybox_id)


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
        self.client.remove_image(img_id)
        images = self.client.images(all=True)
        res = [x for x in images if x['Id'].startswith(img_id)]
        self.assertEqual(len(res), 0)

#################
# BUILDER TESTS #
#################


class TestBuild(BaseTestCase):
    def runTest(self):
        if self.client._version >= 1.8:
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
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
            logs += chunk
        self.assertNotEqual(logs, '')


class TestBuildFromStringIO(BaseTestCase):
    def runTest(self):
        if six.PY3:
            return
        script = io.StringIO(u'\n'.join([
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
            logs += chunk
        self.assertNotEqual(logs, '')


class TestBuildWithAuth(BaseTestCase):
    def runTest(self):
        if self.client._version < 1.9:
            return

        k = 'K4104GON3P4Q6ZUJFZRRC2ZQTBJ5YT0UMZD7TGT7ZVIR8Y05FAH2TJQI6Y90SMIB'
        self.client.login('quay+fortesting', k, registry='https://quay.io/v1/',
                          email='')

        script = io.BytesIO('\n'.join([
            'FROM quay.io/quay/teststuff',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
        ]).encode('ascii'))

        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            logs += chunk

        self.assertNotEqual(logs, '')
        self.assertEqual(logs.find('HTTP code: 403'), -1)


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
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], b'sakuya')
        self.assertEqual(cfg['password'], b'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


class TestLoadJSONConfig(BaseTestCase):
    def runTest(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        email_ = 'sakuya@scarlet.net'
        f.write('{{"{}": {{"auth": "{}", "email": "{}"}}}}\n'.format(
            docker.auth.INDEX_URL, auth_, email_))
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], b'sakuya')
        self.assertEqual(cfg['password'], b'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


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


if __name__ == '__main__':
    unittest.main()
