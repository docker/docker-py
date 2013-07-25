import os
import six
from StringIO import StringIO
import time
import unittest


import docker

# FIXME: missing tests for
# export; history; import_image; insert; port; push;
# tag; kill/stop/start/wait/restart (multi)

class BaseTestCase(unittest.TestCase):
    tmp_imgs = []
    tmp_containers = []

    def setUp(self):
        self.client = docker.Client()
        self.client.pull('busybox')

    def tearDown(self):
        if len(self.tmp_imgs) > 0:
            self.client.remove_image(*self.tmp_imgs)
        if len(self.tmp_containers) > 0:
            self.client.remove_container(*self.tmp_containers)

#########################
##  INFORMATION TESTS  ##
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
        base_img = [x for x in res if x['Name'] == 'busybox']
        self.assertEqual(len(base_img), 1)
        self.assertIn('Description', base_img[0])

###################
## LISTING TESTS ##
###################

class TestImages(BaseTestCase):
    def runTest(self):
        res1 = self.client.images(all=True)
        self.assertIn('Id', res1[0])
        res10 = [x for x in res1 if x['Id'].startswith('e9aa60c60128')][0]
        self.assertIn('Created', res10)
        self.assertIn('Repository', res10)
        self.assertIn('Tag', res10)
        self.assertEqual(res10['Tag'], 'latest')
        self.assertEqual(res10['Repository'], 'busybox')
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
        res1 = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res1)
        self.client.start(res1['Id'])
        self.tmp_containers.append(res1['Id'])
        res2 = self.client.containers(all=True)
        self.assertEqual(size + 1, len(res2))
        retrieved = [x for x in res2 if x['Id'].startswith(res1['Id'])]
        self.assertEqual(len(retrieved), 1)
        retrieved = retrieved[0]
        self.assertIn('Command', retrieved)
        self.assertEqual(retrieved['Command'], 'true ')
        self.assertIn('Image', retrieved)
        self.assertEqual(retrieved['Image'], 'busybox:latest')
        self.assertIn('Status', retrieved)

#####################
## CONTAINER TESTS ##
#####################

class TestCreateContainer(BaseTestCase):
    def runTest(self):
        res = self.client.create_container('busybox', 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])

class TestCreateContainerWithBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = os.getcwd()

        filename = 'shared.txt'
        shared_file = os.path.join(mount_origin, filename)

        with open(shared_file, 'w'):
            container = self.client.create_container('busybox',
                ['ls', mount_dest], volumes={mount_dest: {}})
            container_id = container['Id']
            self.client.start(container_id, binds={mount_origin: mount_dest})
            self.tmp_containers.append(container_id)
            exitcode = self.client.wait(container_id)
            self.assertEqual(exitcode, 0)
            logs = self.client.logs(container_id)

        os.unlink(shared_file)
        self.assertIn(filename, logs)

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

class TestLogs(BaseTestCase):
    def runTest(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container('busybox',
            'echo {0}'.format(snippet))
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id)
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
        # FIXME also test remove/modify
        # (need testcommit first)

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

class TestRemoveContainer(BaseTestCase):
    def runTest(self):
        container = self.client.create_container('busybox', ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.tmp_containers.append(id)
        self.client.remove_container(id)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)

##################
## IMAGES TESTS ##
##################

class TestPull(BaseTestCase):
    def runTest(self):
        self.client.remove_image('joffrey/test001')
        self.client.remove_image('376968a23351')
        info = self.client.info()
        self.assertIn('Images', info)
        img_count = info['Images']
        res = self.client.pull('joffrey/test001')
        self.assertEqual(type(res), six.text_type)
        self.assertEqual(img_count + 2, self.client.info()['Images'])
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
        script = StringIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz /tmp/silence.tar.gz'
        ]))
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

#######################
## PY SPECIFIC TESTS ##
#######################

class TestRunShlex(BaseTestCase):
    def runTest(self):
        commands = [
            'true',
            'echo "The Young Descendant of Tepes & Septette for the Dead Princess"',
            'echo -n "The Young Descendant of Tepes & Septette for the Dead Princess"',
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


if __name__ == '__main__':
    unittest.main()
