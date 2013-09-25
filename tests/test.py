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
import os
from StringIO import StringIO
import tempfile
import unittest

import docker
import six


import requests
from requests import structures
import datetime
import json
from fake_api import fake_responses, FAKE_CONTAINER_ID, FAKE_IMAGE_ID

# FIXME: missing tests for
# export; history; import_image; insert; port; push; tag


def response(status_code=200, content='', headers=None, reason=None, elapsed=0,
             request=None):
    res = requests.Response()
    res.status_code = status_code
    if isinstance(content, dict):
        content = json.dumps(content)
    res._content = content
    res.headers = structures.CaseInsensitiveDict(headers or {})
    res.reason = reason
    res.elapsed = datetime.timedelta(elapsed)
    return res


def fake_get(self, url, **kwargs):
    status_code, content = fake_responses[url]()
    return response(status_code=status_code, content=content)


def fake_post(self, url, data=None, **kwargs):
    status_code, content = fake_responses[url]()
    return response(status_code=status_code, content=content)


def fake_put(self, url, data=None, **kwargs):
    status_code, content = fake_responses[url]()
    return response(status_code=status_code, content=content)


def fake_delete(self, url, data=None, **kwargs):
    status_code, content = fake_responses[url]()
    return response(status_code=status_code, content=content)


docker.Client.get = fake_get
docker.Client.post = fake_post
docker.Client.put = fake_put
docker.Client.delete = fake_delete


class BaseTestCase(unittest.TestCase):

    def setUp(self):
        self.client = docker.Client()


#########################
##  INFORMATION TESTS  ##
#########################


class TestVersion(BaseTestCase):
    def runTest(self):
        try:
            self.client.version()
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestInfo(BaseTestCase):
    def runTest(self):
        try:
            self.client.info()
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestSearch(BaseTestCase):
    def runTest(self):
        try:
            self.client.search('busybox')
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


# ###################
# ## LISTING TESTS ##
# ###################


class TestImages(BaseTestCase):
    def runTest(self):
        try:
            self.client.images(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestImageIds(BaseTestCase):
    def runTest(self):
        try:
            self.client.images(quiet=True)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestListContainers(BaseTestCase):
    def runTest(self):
        try:
            self.client.containers(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


#####################
## CONTAINER TESTS ##
#####################


class TestCreateContainer(BaseTestCase):
    def runTest(self):
        try:
            self.client.create_container('busybox', 'true')
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestCreateContainerWithBinds(BaseTestCase):
    def runTest(self):
        mount_dest = '/mnt'
        mount_origin = '/tmp'

        try:
            self.client.create_container('busybox',
                ['ls', mount_dest], volumes={mount_dest: {}})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestCreateContainerPrivileged(BaseTestCase):
    def runTest(self):
        try:
            self.client.create_container('busybox', 'true', privileged=True)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestStartContainer(BaseTestCase):
    def runTest(self):
        try:
            self.client.start(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestStartContainerWithBinds(BaseTestCase):
    def runTest(self):
        try:
            mount_dest = '/mnt'
            mount_origin = '/tmp'
            self.client.start(FAKE_CONTAINER_ID, binds={mount_origin: mount_dest})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestStartContainerWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.start({'Id': FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestWait(BaseTestCase):
    def runTest(self):
        try:
            self.client.wait(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestWaitWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.wait({'Id': FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestLogs(BaseTestCase):
    def runTest(self):
        try:
            self.client.logs(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestLogsWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.logs({'Id': FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestDiff(BaseTestCase):
    def runTest(self):
        try:
            self.client.diff(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestDiffWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.diff({'Id': FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestStop(BaseTestCase):
    def runTest(self):
        try:
            self.client.stop(FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestStopWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.stop({'Id': FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestKill(BaseTestCase):
    def runTest(self):
        try:
            self.client.kill(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestKillWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.kill({'Id': FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestRestart(BaseTestCase):
    def runTest(self):
        try:
            self.client.restart(FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception : ' + str(e))


class TestRestartWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.restart({'Id': FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestRemoveContainer(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_container(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestRemoveContainerWithDictInsteadOfId(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_container({'Id': FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


# ##################
# ## IMAGES TESTS ##
# ##################

class TestPull(BaseTestCase):
    def runTest(self):
        try:
            self.client.pull('joffrey/test001')
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestCommit(BaseTestCase):
    def runTest(self):
        try:
            self.client.commit(FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


class TestRemoveImage(BaseTestCase):
    def runTest(self):
        try:
            self.client.remove_image(FAKE_IMAGE_ID)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


# #################
# # BUILDER TESTS #
# #################

class TestBuild(BaseTestCase):
    def runTest(self):
        script = StringIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz /tmp/silence.tar.gz'
        ]))
        try:
            self.client.build(fileobj=script)
        except Exception as e:
            self.fail('Command should not raise exception: ' + str(e))


# #######################
# ## PY SPECIFIC TESTS ##
# #######################

class TestLoadConfig(BaseTestCase):
    def runTest(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode('sakuya:izayoi')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertNotEqual(cfg['Configs'][docker.auth.INDEX_URL], None)
        cfg = cfg['Configs'][docker.auth.INDEX_URL]
        self.assertEqual(cfg['Username'], 'sakuya')
        self.assertEqual(cfg['Password'], 'izayoi')
        self.assertEqual(cfg['Email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)

if __name__ == '__main__':
    unittest.main()
