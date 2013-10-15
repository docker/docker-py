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
import datetime
import io
import json
import os
import tempfile
import unittest

import docker
import requests
import six

import fake_api


try:
    from unittest import mock
except ImportError:
    import mock


# FIXME: missing tests for
# export; history; import_image; insert; port; push; tag


def response(status_code=200, content='', headers=None, reason=None, elapsed=0,
             request=None):
    res = requests.Response()
    res.status_code = status_code
    if not isinstance(content, six.string_types):
        content = json.dumps(content)
    if six.PY3:
        content = content.encode('ascii')
    res._content = content
    res.headers = requests.structures.CaseInsensitiveDict(headers or {})
    res.reason = reason
    res.elapsed = datetime.timedelta(elapsed)
    res.request = request
    return res


def fake_resp(url, data=None, **kwargs):
    status_code, content = fake_api.fake_responses[url]()
    return response(status_code=status_code, content=content)

fake_request = mock.Mock(side_effect=fake_resp)


@mock.patch.multiple('docker.Client', get=fake_request, post=fake_request,
                     put=fake_request, delete=fake_request)
class DockerClientTest(unittest.TestCase):
    def setUp(self):
        self.client = docker.Client()

    #########################
    ##  INFORMATION TESTS  ##
    #########################
    def test_version(self):
        try:
            self.client.version()
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/version'
        )

    def test_info(self):
        try:
            self.client.info()
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with('unix://var/run/docker.sock/v1.4/info')

    def test_search(self):
        try:
            self.client.search('busybox')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/images/search',
            params={'term': 'busybox'}
        )

    ###################
    ## LISTING TESTS ##
    ###################

    def test_images(self):
        try:
            self.client.images(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/images/json',
            params={'filter': None, 'only_ids': 0, 'all': 1}
        )

    def test_image_ids(self):
        try:
            self.client.images(quiet=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/images/json',
            params={'filter': None, 'only_ids': 1, 'all': 0}
        )

    def test_list_containers(self):
        try:
            self.client.containers(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/ps',
            params={
                'all': 1,
                'since': None,
                'limit': -1,
                'trunc_cmd': 1,
                'before': None
            }
        )

    #####################
    ## CONTAINER TESTS ##
    #####################

    def test_create_container(self):
        try:
            self.client.create_container('busybox', 'true')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         'unix://var/run/docker.sock/v1.4/containers/create')
        self.assertEqual(json.loads(args[0][1]),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false, "Memory": 0,
                             "AttachStderr": true, "Privileged": false,
                             "AttachStdout": true, "OpenStdin": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_binds(self):
        mount_dest = '/mnt'
        #mount_origin = '/tmp'

        try:
            self.client.create_container('busybox', ['ls', mount_dest],
                                         volumes={mount_dest: {}})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         'unix://var/run/docker.sock/v1.4/containers/create')
        self.assertEqual(json.loads(args[0][1]),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
                             "Volumes": {"/mnt": {}}, "Memory": 0,
                             "AttachStderr": true, "Privileged": false,
                             "AttachStdout": true, "OpenStdin": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_privileged(self):
        try:
            self.client.create_container('busybox', 'true', privileged=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         'unix://var/run/docker.sock/v1.4/containers/create')
        self.assertEqual(json.loads(args[0][1]),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false, "Memory": 0,
                             "AttachStderr": true, "Privileged": true,
                             "AttachStdout": true, "OpenStdin": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_start_container(self):
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/start',
            '{}',
            headers={'Content-Type': 'application/json'}
        )

    def test_start_container_with_binds(self):
        try:
            mount_dest = '/mnt'
            mount_origin = '/tmp'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              binds={mount_origin: mount_dest})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/start',
            '{"Binds": ["/tmp:/mnt"]}',
            headers={'Content-Type': 'application/json'}
        )

    def test_start_container_with_dict_instead_of_id(self):
        try:
            self.client.start({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/start',
            '{}', headers={'Content-Type': 'application/json'}
        )

    def test_wait(self):
        try:
            self.client.wait(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/wait',
            None,
            timeout=None
        )

    def test_wait_with_dict_instead_of_id(self):
        try:
            self.client.wait({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/wait',
            None,
            timeout=None
        )

    def test_logs(self):
        try:
            self.client.logs(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/attach',
            None,
            params={'logs': 1, 'stderr': 1, 'stdout': 1}
        )

    def test_logs_with_dict_instead_of_id(self):
        try:
            self.client.logs({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/attach',
            None,
            params={'logs': 1, 'stderr': 1, 'stdout': 1}
        )

    def test_diff(self):
        try:
            self.client.diff(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/changes')

    def test_diff_with_dict_instead_of_id(self):
        try:
            self.client.diff({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/changes')

    def test_stop_container(self):
        try:
            self.client.stop(fake_api.FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/stop',
            None,
            params={'t': 2}
        )

    def test_stop_container_with_dict_instead_of_id(self):
        try:
            self.client.stop({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/stop',
            None,
            params={'t': 2}
        )

    def test_kill_container(self):
        try:
            self.client.kill(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/kill',
            None
        )

    def test_kill_container_with_dict_instead_of_id(self):
        try:
            self.client.kill({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/kill',
            None
        )

    def test_restart_container(self):
        try:
            self.client.restart(fake_api.FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception : {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/restart',
            None,
            params={'t': 2}
        )

    def test_restart_container_with_dict_instead_of_id(self):
        try:
            self.client.restart({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b/restart',
            None,
            params={'t': 2}
        )

    def test_remove_container(self):
        try:
            self.client.remove_container(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b',
            params={'v': False}
        )

    def test_remove_container_with_dict_instead_of_id(self):
        try:
            self.client.remove_container({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/containers/3cc2351ab11b',
            params={'v': False}
        )

    ##################
    ## IMAGES TESTS ##
    ##################

    def test_pull(self):
        try:
            self.client.pull('joffrey/test001')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/images/create',
            headers={},
            params={'tag': None, 'fromImage': 'joffrey/test001'}
        )

    def test_commit(self):
        try:
            self.client.commit(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/commit',
            '{}',
            headers={'Content-Type': 'application/json'},
            params={
                'repo': None,
                'comment': None,
                'tag': None,
                'container': '3cc2351ab11b',
                'author': None
            }
        )

    def test_remove_image(self):
        try:
            self.client.remove_image(fake_api.FAKE_IMAGE_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            'unix://var/run/docker.sock/v1.4/images/e9aa60c60128'
        )

    #################
    # BUILDER TESTS #
    #################

    def test_build_container(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        try:
            self.client.build(fileobj=script)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

    #######################
    ## PY SPECIFIC TESTS ##
    #######################

    def test_load_config(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertNotEqual(cfg['Configs'][docker.auth.INDEX_URL], None)
        cfg = cfg['Configs'][docker.auth.INDEX_URL]
        self.assertEqual(cfg['Username'], b'sakuya')
        self.assertEqual(cfg['Password'], b'izayoi')
        self.assertEqual(cfg['Email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('Auth'), None)


if __name__ == '__main__':
    unittest.main()
