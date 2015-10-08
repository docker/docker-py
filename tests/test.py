# Copyright 2013 dotCloud inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import base64
import datetime
import gzip
import io
import json
import os
import re
import shutil
import signal
import socket
import sys
import tarfile
import tempfile
import threading
import time
import random

import docker
import requests
import six

from . import base
from . import fake_api
from .helpers import make_tree

import pytest

try:
    from unittest import mock
except ImportError:
    import mock


DEFAULT_TIMEOUT_SECONDS = docker.constants.DEFAULT_TIMEOUT_SECONDS


def response(status_code=200, content='', headers=None, reason=None, elapsed=0,
             request=None):
    res = requests.Response()
    res.status_code = status_code
    if not isinstance(content, six.binary_type):
        content = json.dumps(content).encode('ascii')
    res._content = content
    res.headers = requests.structures.CaseInsensitiveDict(headers or {})
    res.reason = reason
    res.elapsed = datetime.timedelta(elapsed)
    res.request = request
    return res


def fake_resolve_authconfig(authconfig, registry=None):
    return None


def fake_inspect_container(self, container, tty=False):
    return fake_api.get_fake_inspect_container(tty=tty)[1]


def fake_inspect_container_tty(self, container):
    return fake_inspect_container(self, container, tty=True)


def fake_resp(method, url, *args, **kwargs):
    key = None
    if url in fake_api.fake_responses:
        key = url
    elif (url, method) in fake_api.fake_responses:
        key = (url, method)
    if not key:
        raise Exception('{0} {1}'.format(method, url))
    status_code, content = fake_api.fake_responses[key]()
    return response(status_code=status_code, content=content)


fake_request = mock.Mock(side_effect=fake_resp)


def fake_get(self, url, *args, **kwargs):
    return fake_request('GET', url, *args, **kwargs)


def fake_post(self, url, *args, **kwargs):
    return fake_request('POST', url, *args, **kwargs)


def fake_put(self, url, *args, **kwargs):
    return fake_request('PUT', url, *args, **kwargs)


def fake_delete(self, url, *args, **kwargs):
    return fake_request('DELETE', url, *args, **kwargs)

url_base = 'http+docker://localunixsocket/'
url_prefix = '{0}v{1}/'.format(
    url_base,
    docker.constants.DEFAULT_DOCKER_API_VERSION)


class Cleanup(object):
    if sys.version_info < (2, 7):
        # Provide a basic implementation of addCleanup for Python < 2.7
        def __init__(self, *args, **kwargs):
            super(Cleanup, self).__init__(*args, **kwargs)
            self._cleanups = []

        def tearDown(self):
            super(Cleanup, self).tearDown()
            ok = True
            while self._cleanups:
                fn, args, kwargs = self._cleanups.pop(-1)
                try:
                    fn(*args, **kwargs)
                except KeyboardInterrupt:
                    raise
                except:
                    ok = False
            if not ok:
                raise

        def addCleanup(self, function, *args, **kwargs):
            self._cleanups.append((function, args, kwargs))


@mock.patch.multiple('docker.Client', get=fake_get, post=fake_post,
                     put=fake_put, delete=fake_delete)
class DockerClientTest(Cleanup, base.BaseTestCase):
    def setUp(self):
        self.client = docker.Client()
        # Force-clear authconfig to avoid tampering with the tests
        self.client._cfg = {'Configs': {}}

    def tearDown(self):
        self.client.close()

    def assertIn(self, object, collection):
        if six.PY2 and sys.version_info[1] <= 6:
            return self.assertTrue(object in collection)
        return super(DockerClientTest, self).assertIn(object, collection)

    def base_create_payload(self, img='busybox', cmd=None):
        if not cmd:
            cmd = ['true']
        return {"Tty": False, "Image": img, "Cmd": cmd,
                "AttachStdin": False,
                "AttachStderr": True, "AttachStdout": True,
                "StdinOnce": False,
                "OpenStdin": False, "NetworkDisabled": False,
                }

    def test_ctor(self):
        with pytest.raises(docker.errors.DockerException) as excinfo:
            docker.Client(version=1.12)

        self.assertEqual(
            str(excinfo.value),
            'Version parameter must be a string or None. Found float'
        )

    def test_url_valid_resource(self):
        url = self.client._url('/hello/{0}/world', 'somename')
        self.assertEqual(
            url, '{0}{1}'.format(url_prefix, 'hello/somename/world')
        )

        url = self.client._url(
            '/hello/{0}/world/{1}', 'somename', 'someothername'
        )
        self.assertEqual(
            url,
            '{0}{1}'.format(url_prefix, 'hello/somename/world/someothername')
        )

        url = self.client._url('/hello/{0}/world', '/some?name')
        self.assertEqual(
            url, '{0}{1}'.format(url_prefix, 'hello/%2Fsome%3Fname/world')
        )

    def test_url_invalid_resource(self):
        with pytest.raises(ValueError):
            self.client._url('/hello/{0}/world', ['sakuya', 'izayoi'])

    def test_url_no_resource(self):
        url = self.client._url('/simple')
        self.assertEqual(url, '{0}{1}'.format(url_prefix, 'simple'))

    def test_url_unversioned_api(self):
        url = self.client._url(
            '/hello/{0}/world', 'somename', versioned_api=False
        )
        self.assertEqual(
            url, '{0}{1}'.format(url_base, 'hello/somename/world')
        )

    #########################
    #   INFORMATION TESTS   #
    #########################
    def test_version(self):
        self.client.version()

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'version',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_version_no_api_version(self):
        self.client.version(False)

        fake_request.assert_called_with(
            'GET',
            url_base + 'version',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_retrieve_server_version(self):
        client = docker.Client(version="auto")
        self.assertTrue(isinstance(client._version, six.string_types))
        self.assertFalse(client._version == "auto")
        client.close()

    def test_auto_retrieve_server_version(self):
        version = self.client._retrieve_server_version()
        self.assertTrue(isinstance(version, six.string_types))

    def test_info(self):
        self.client.info()

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'info',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_search(self):
        self.client.search('busybox')

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/search',
            params={'term': 'busybox'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_viz(self):
        with pytest.raises(Exception):
            self.client.images('busybox', viz=True)
            self.fail('Viz output should not be supported!')

    def test_events(self):
        self.client.events()

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'events',
            params={'since': None, 'until': None, 'filters': None},
            stream=True
        )

    def test_events_with_since_until(self):
        ts = 1356048000
        now = datetime.datetime.utcfromtimestamp(ts)
        since = now - datetime.timedelta(seconds=10)
        until = now + datetime.timedelta(seconds=10)

        self.client.events(since=since, until=until)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'events',
            params={
                'since': ts - 10,
                'until': ts + 10,
                'filters': None
            },
            stream=True
        )

    def test_events_with_filters(self):
        filters = {'event': ['die', 'stop'],
                   'container': fake_api.FAKE_CONTAINER_ID}

        self.client.events(filters=filters)

        expected_filters = docker.utils.convert_filters(filters)
        fake_request.assert_called_with(
            'GET',
            url_prefix + 'events',
            params={
                'since': None,
                'until': None,
                'filters': expected_filters
            },
            stream=True
        )

    ###################
    #  LISTING TESTS  #
    ###################

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

    def test_list_containers(self):
        self.client.containers(all=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/json',
            params={
                'all': 1,
                'since': None,
                'size': 0,
                'limit': -1,
                'trunc_cmd': 0,
                'before': None
            },
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    @base.requires_api_version('1.21')
    def test_list_networks(self):
        networks = [
            {
                "name": "none",
                "id": "8e4e55c6863ef424",
                "type": "null",
                "endpoints": []
            },
            {
                "name": "host",
                "id": "062b6d9ea7913fde",
                "type": "host",
                "endpoints": []
            },
        ]

        get = mock.Mock(return_value=response(
            status_code=200, content=json.dumps(networks).encode('utf-8')))

        with mock.patch('docker.Client.get', get):
            self.assertEqual(self.client.networks(), networks)

            self.assertEqual(get.call_args[0][0], url_prefix + 'networks')

            filters = json.loads(get.call_args[1]['params']['filters'])
            self.assertFalse(filters)

            self.client.networks(names=['foo'])
            filters = json.loads(get.call_args[1]['params']['filters'])
            self.assertEqual(filters, {'name': ['foo']})

            self.client.networks(ids=['123'])
            filters = json.loads(get.call_args[1]['params']['filters'])
            self.assertEqual(filters, {'id': ['123']})

    #####################
    #  CONTAINER TESTS  #
    #####################

    def test_create_container(self):
        self.client.create_container('busybox', 'true')

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": false,
                             "OpenStdin": false, "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_binds(self):
        mount_dest = '/mnt'

        self.client.create_container('busybox', ['ls', mount_dest],
                                     volumes=[mount_dest])

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
                             "Volumes": {"/mnt": {}},
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_volume_string(self):
        mount_dest = '/mnt'

        self.client.create_container('busybox', ['ls', mount_dest],
                                     volumes=mount_dest)

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
                             "Volumes": {"/mnt": {}},
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_ports(self):
        self.client.create_container('busybox', 'ls',
                                     ports=[1111, (2222, 'udp'), (3333,)])

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "ExposedPorts": {
                                "1111/tcp": {},
                                "2222/udp": {},
                                "3333/tcp": {}
                             },
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_entrypoint(self):
        self.client.create_container('busybox', 'hello',
                                     entrypoint='cowsay entry')

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["hello"], "AttachStdin": false,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "Entrypoint": ["cowsay", "entry"]}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_cpu_shares(self):
        self.client.create_container('busybox', 'ls',
                                     cpu_shares=5)

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "CpuShares": 5}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_cpuset(self):
        self.client.create_container('busybox', 'ls',
                                     cpuset='0,1')

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "Cpuset": "0,1",
                             "CpusetCpus": "0,1"}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_cgroup_parent(self):
        self.client.create_container(
            'busybox', 'ls', host_config=self.client.create_host_config(
                cgroup_parent='test'
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        data = json.loads(args[1]['data'])
        self.assertIn('HostConfig', data)
        self.assertIn('CgroupParent', data['HostConfig'])
        self.assertEqual(data['HostConfig']['CgroupParent'], 'test')

    def test_create_container_with_working_dir(self):
        self.client.create_container('busybox', 'ls',
                                     working_dir='/root')

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "WorkingDir": "/root"}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_stdin_open(self):
        self.client.create_container('busybox', 'true', stdin_open=True)

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": true,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": true,
                             "OpenStdin": true, "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_volumes_from(self):
        vol_names = ['foo', 'bar']
        try:
            self.client.create_container('busybox', 'true',
                                         volumes_from=vol_names)
        except docker.errors.DockerException:
            self.assertTrue(
                docker.utils.compare_version('1.10', self.client._version) >= 0
            )
            return

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data'])['VolumesFrom'],
                         ','.join(vol_names))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_empty_volumes_from(self):
        self.client.create_container('busybox', 'true', volumes_from=[])

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertTrue('VolumesFrom' not in data)

    def test_create_named_container(self):
        self.client.create_container('busybox', 'true',
                                     name='marisa-kirisame')

        args = fake_request.call_args
        self.assertEqual(args[0][1],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": false,
                             "OpenStdin": false, "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(args[1]['params'], {'name': 'marisa-kirisame'})

    def test_create_container_with_mem_limit_as_int(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit=128.0
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertEqual(data['HostConfig']['Memory'], 128.0)

    def test_create_container_with_mem_limit_as_string(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertEqual(data['HostConfig']['Memory'], 128.0)

    def test_create_container_with_mem_limit_as_string_with_k_unit(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128k'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertEqual(data['HostConfig']['Memory'], 128.0 * 1024)

    def test_create_container_with_mem_limit_as_string_with_m_unit(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128m'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertEqual(data['HostConfig']['Memory'], 128.0 * 1024 * 1024)

    def test_create_container_with_mem_limit_as_string_with_g_unit(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128g'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        self.assertEqual(
            data['HostConfig']['Memory'], 128.0 * 1024 * 1024 * 1024
        )

    def test_create_container_with_mem_limit_as_string_with_wrong_value(self):
        self.assertRaises(
            docker.errors.DockerException,
            self.client.create_host_config, mem_limit='128p'
        )

        self.assertRaises(
            docker.errors.DockerException,
            self.client.create_host_config, mem_limit='1f28'
        )

    def test_start_container(self):
        self.client.start(fake_api.FAKE_CONTAINER_ID)

        args = fake_request.call_args
        self.assertEqual(
            args[0][1],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(json.loads(args[1]['data']), {})
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_none(self):
        with pytest.raises(ValueError) as excinfo:
            self.client.start(container=None)

        self.assertEqual(
            str(excinfo.value),
            'image or container param is undefined',
        )

        with pytest.raises(ValueError) as excinfo:
            self.client.start(None)

        self.assertEqual(
            str(excinfo.value),
            'image or container param is undefined',
        )

    def test_start_container_regression_573(self):
        self.client.start(**{'container': fake_api.FAKE_CONTAINER_ID})

    def test_create_container_with_lxc_conf(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                lxc_conf={'lxc.conf.k': 'lxc.conf.value'}
            )
        )

        args = fake_request.call_args
        self.assertEqual(
            args[0][1],
            url_prefix + 'containers/create'
        )
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['LxcConf'] = [
            {"Value": "lxc.conf.value", "Key": "lxc.conf.k"}
        ]

        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_lxc_conf_compat(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                lxc_conf=[{'Key': 'lxc.conf.k', 'Value': 'lxc.conf.value'}]
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['LxcConf'] = [
            {"Value": "lxc.conf.value", "Key": "lxc.conf.k"}
        ]
        self.assertEqual(
            json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_binds_ro(self):
        mount_dest = '/mnt'
        mount_origin = '/tmp'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                binds={mount_origin: {
                    "bind": mount_dest,
                    "ro": True
                }}
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix +
                         'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["/tmp:/mnt:ro"]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_binds_rw(self):
        mount_dest = '/mnt'
        mount_origin = '/tmp'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                binds={mount_origin: {
                    "bind": mount_dest,
                    "ro": False
                }}
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix +
                         'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["/tmp:/mnt:rw"]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_binds_mode(self):
        mount_dest = '/mnt'
        mount_origin = '/tmp'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                binds={mount_origin: {
                    "bind": mount_dest,
                    "mode": "z",
                }}
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix +
                         'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["/tmp:/mnt:z"]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_binds_mode_and_ro_error(self):
        with pytest.raises(ValueError):
            mount_dest = '/mnt'
            mount_origin = '/tmp'
            self.client.create_container(
                'busybox', 'true', host_config=self.client.create_host_config(
                    binds={mount_origin: {
                        "bind": mount_dest,
                        "mode": "z",
                        "ro": True,
                    }}
                )
            )

    def test_create_container_with_binds_list(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                binds=[
                    "/tmp:/mnt/1:ro",
                    "/tmp:/mnt/2",
                ],
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix +
                         'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = [
            "/tmp:/mnt/1:ro",
            "/tmp:/mnt/2",
        ]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_port_binds(self):
        self.maxDiff = None

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                port_bindings={
                    1111: None,
                    2222: 2222,
                    '3333/udp': (3333,),
                    4444: ('127.0.0.1',),
                    5555: ('127.0.0.1', 5555),
                    6666: [('127.0.0.1',), ('192.168.0.1',)]
                }
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        data = json.loads(args[1]['data'])
        port_bindings = data['HostConfig']['PortBindings']
        self.assertTrue('1111/tcp' in port_bindings)
        self.assertTrue('2222/tcp' in port_bindings)
        self.assertTrue('3333/udp' in port_bindings)
        self.assertTrue('4444/tcp' in port_bindings)
        self.assertTrue('5555/tcp' in port_bindings)
        self.assertTrue('6666/tcp' in port_bindings)
        self.assertEqual(
            [{"HostPort": "", "HostIp": ""}],
            port_bindings['1111/tcp']
        )
        self.assertEqual(
            [{"HostPort": "2222", "HostIp": ""}],
            port_bindings['2222/tcp']
        )
        self.assertEqual(
            [{"HostPort": "3333", "HostIp": ""}],
            port_bindings['3333/udp']
        )
        self.assertEqual(
            [{"HostPort": "", "HostIp": "127.0.0.1"}],
            port_bindings['4444/tcp']
        )
        self.assertEqual(
            [{"HostPort": "5555", "HostIp": "127.0.0.1"}],
            port_bindings['5555/tcp']
        )
        self.assertEqual(len(port_bindings['6666/tcp']), 2)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_mac_address(self):
        mac_address_expected = "02:42:ac:11:00:0a"

        container = self.client.create_container(
            'busybox', ['sleep', '60'], mac_address=mac_address_expected)

        res = self.client.inspect_container(container['Id'])
        self.assertEqual(mac_address_expected,
                         res['NetworkSettings']['MacAddress'])

    def test_create_container_with_links(self):
        link_path = 'path'
        alias = 'alias'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                links={link_path: alias}
            )
        )

        args = fake_request.call_args
        self.assertEqual(
            args[0][1], url_prefix + 'containers/create'
        )
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Links'] = ['path:alias']

        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )

    def test_create_container_with_multiple_links(self):
        link_path = 'path'
        alias = 'alias'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                links={
                    link_path + '1': alias + '1',
                    link_path + '2': alias + '2'
                }
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Links'] = [
            'path1:alias1', 'path2:alias2'
        ]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )

    def test_create_container_with_links_as_list_of_tuples(self):
        link_path = 'path'
        alias = 'alias'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                links=[(link_path, alias)]
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Links'] = ['path:alias']

        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )

    def test_create_container_privileged(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(privileged=True)
        )

        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Privileged'] = True
        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_lxc_conf(self):
        def call_start():
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf={'lxc.conf.k': 'lxc.conf.value'}
            )

        pytest.deprecated_call(call_start)

    def test_start_container_with_lxc_conf_compat(self):
        def call_start():
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf=[{'Key': 'lxc.conf.k', 'Value': 'lxc.conf.value'}]
            )

        pytest.deprecated_call(call_start)

    def test_start_container_with_binds_ro(self):
        def call_start():
            self.client.start(
                fake_api.FAKE_CONTAINER_ID, binds={
                    '/tmp': {
                        "bind": '/mnt',
                        "ro": True
                    }
                }
            )

        pytest.deprecated_call(call_start)

    def test_start_container_with_binds_rw(self):
        def call_start():
            self.client.start(
                fake_api.FAKE_CONTAINER_ID, binds={
                    '/tmp': {"bind": '/mnt', "ro": False}
                }
            )

        pytest.deprecated_call(call_start)

    def test_start_container_with_port_binds(self):
        self.maxDiff = None

        def call_start():
            self.client.start(fake_api.FAKE_CONTAINER_ID, port_bindings={
                1111: None,
                2222: 2222,
                '3333/udp': (3333,),
                4444: ('127.0.0.1',),
                5555: ('127.0.0.1', 5555),
                6666: [('127.0.0.1',), ('192.168.0.1',)]
            })

        pytest.deprecated_call(call_start)

    def test_start_container_with_links(self):
        def call_start():
            self.client.start(
                fake_api.FAKE_CONTAINER_ID, links={'path': 'alias'}
            )

        pytest.deprecated_call(call_start)

    def test_start_container_with_multiple_links(self):
        def call_start():
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                links={
                    'path1': 'alias1',
                    'path2': 'alias2'
                }
            )

        pytest.deprecated_call(call_start)

    def test_start_container_with_links_as_list_of_tuples(self):
        def call_start():
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              links=[('path', 'alias')])

        pytest.deprecated_call(call_start)

    def test_start_container_privileged(self):
        def call_start():
            self.client.start(fake_api.FAKE_CONTAINER_ID, privileged=True)

        pytest.deprecated_call(call_start)

    def test_start_container_with_dict_instead_of_id(self):
        self.client.start({'Id': fake_api.FAKE_CONTAINER_ID})

        args = fake_request.call_args
        self.assertEqual(
            args[0][1],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(json.loads(args[1]['data']), {})
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_restart_policy(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                restart_policy={
                    "Name": "always",
                    "MaximumRetryCount": 0
                }
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')

        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['RestartPolicy'] = {
            "MaximumRetryCount": 0, "Name": "always"
        }
        self.assertEqual(json.loads(args[1]['data']), expected_payload)

        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_added_capabilities(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(cap_add=['MKNOD'])
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['CapAdd'] = ['MKNOD']
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_dropped_capabilities(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(cap_drop=['MKNOD'])
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['CapDrop'] = ['MKNOD']
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_devices(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                devices=['/dev/sda:/dev/xvda:rwm',
                         '/dev/sdb:/dev/xvdb',
                         '/dev/sdc']
            )
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Devices'] = [
            {'CgroupPermissions': 'rwm',
             'PathInContainer': '/dev/xvda',
             'PathOnHost': '/dev/sda'},
            {'CgroupPermissions': 'rwm',
             'PathInContainer': '/dev/xvdb',
             'PathOnHost': '/dev/sdb'},
            {'CgroupPermissions': 'rwm',
             'PathInContainer': '/dev/sdc',
             'PathOnHost': '/dev/sdc'}
        ]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_labels_dict(self):
        labels_dict = {
            six.text_type('foo'): six.text_type('1'),
            six.text_type('bar'): six.text_type('2'),
        }

        self.client.create_container(
            'busybox', 'true',
            labels=labels_dict,
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data'])['Labels'], labels_dict)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_labels_list(self):
        labels_list = [
            six.text_type('foo'),
            six.text_type('bar'),
        ]
        labels_dict = {
            six.text_type('foo'): six.text_type(),
            six.text_type('bar'): six.text_type(),
        }

        self.client.create_container(
            'busybox', 'true',
            labels=labels_list,
        )

        args = fake_request.call_args
        self.assertEqual(args[0][1], url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data'])['Labels'], labels_dict)
        self.assertEqual(
            args[1]['headers'], {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'], DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_container_with_named_volume(self):
        mount_dest = '/mnt'
        volume_name = 'name'

        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(
                binds={volume_name: {
                    "bind": mount_dest,
                    "ro": False
                }}),
            volume_driver='foodriver',
        )

        args = fake_request.call_args
        self.assertEqual(
            args[0][1], url_prefix + 'containers/create'
        )
        expected_payload = self.base_create_payload()
        expected_payload['VolumeDriver'] = 'foodriver'
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["name:/mnt:rw"]
        self.assertEqual(json.loads(args[1]['data']), expected_payload)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            DEFAULT_TIMEOUT_SECONDS
        )

    def test_resize_container(self):
        self.client.resize(
            {'Id': fake_api.FAKE_CONTAINER_ID},
            height=15,
            width=120
        )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/resize',
            params={'h': 15, 'w': 120},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_rename_container(self):
        self.client.rename(
            {'Id': fake_api.FAKE_CONTAINER_ID},
            name='foobar'
        )

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/rename',
            params={'name': 'foobar'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_wait(self):
        self.client.wait(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None
        )

    def test_wait_with_dict_instead_of_id(self):
        self.client.wait({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None
        )

    def _socket_path_for_client_session(self, client):
        socket_adapter = client.get_adapter('http+docker://')
        return socket_adapter.socket_path

    def test_url_compatibility_unix(self):
        c = docker.Client(base_url="unix://socket")

        assert self._socket_path_for_client_session(c) == '/socket'

    def test_url_compatibility_unix_triple_slash(self):
        c = docker.Client(base_url="unix:///socket")

        assert self._socket_path_for_client_session(c) == '/socket'

    def test_url_compatibility_http_unix_triple_slash(self):
        c = docker.Client(base_url="http+unix:///socket")

        assert self._socket_path_for_client_session(c) == '/socket'

    def test_url_compatibility_http(self):
        c = docker.Client(base_url="http://hostname:1234")

        assert c.base_url == "http://hostname:1234"

    def test_url_compatibility_tcp(self):
        c = docker.Client(base_url="tcp://hostname:1234")

        assert c.base_url == "http://hostname:1234"

    def test_logs(self):
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container):
            logs = self.client.logs(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

        self.assertEqual(
            logs,
            'Flowering Nights\n(Sakuya Iyazoi)\n'.encode('ascii')
        )

    def test_logs_with_dict_instead_of_id(self):
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container):
            logs = self.client.logs({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

        self.assertEqual(
            logs,
            'Flowering Nights\n(Sakuya Iyazoi)\n'.encode('ascii')
        )

    def test_log_streaming(self):
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 1, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=True
        )

    def test_log_tail(self):
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             tail=10)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 10},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_log_tty(self):
        m = mock.Mock()
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container_tty):
            with mock.patch('docker.Client._stream_raw_result',
                            m):
                self.client.logs(fake_api.FAKE_CONTAINER_ID,
                                 stream=True)

        self.assertTrue(m.called)
        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 1, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=True
        )

    def test_diff(self):
        self.client.diff(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/changes',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_diff_with_dict_instead_of_id(self):
        self.client.diff({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/changes',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_port(self):
        self.client.port({'Id': fake_api.FAKE_CONTAINER_ID}, 1111)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/json',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_stop_container(self):
        timeout = 2

        self.client.stop(fake_api.FAKE_CONTAINER_ID, timeout=timeout)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/stop',
            params={'t': timeout},
            timeout=(DEFAULT_TIMEOUT_SECONDS + timeout)
        )

    def test_stop_container_with_dict_instead_of_id(self):
        timeout = 2

        self.client.stop({'Id': fake_api.FAKE_CONTAINER_ID},
                         timeout=timeout)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/stop',
            params={'t': timeout},
            timeout=(DEFAULT_TIMEOUT_SECONDS + timeout)
        )

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

        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

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

    def test_pause_container(self):
        self.client.pause(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/pause',
            timeout=(DEFAULT_TIMEOUT_SECONDS)
        )

    def test_unpause_container(self):
        self.client.unpause(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/unpause',
            timeout=(DEFAULT_TIMEOUT_SECONDS)
        )

    def test_kill_container(self):
        self.client.kill(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container_with_dict_instead_of_id(self):
        self.client.kill({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container_with_signal(self):
        self.client.kill(fake_api.FAKE_CONTAINER_ID, signal=signal.SIGTERM)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={'signal': signal.SIGTERM},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_restart_container(self):
        self.client.restart(fake_api.FAKE_CONTAINER_ID, timeout=2)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/restart',
            params={'t': 2},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_restart_container_with_dict_instead_of_id(self):
        self.client.restart({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/restart',
            params={'t': 2},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_container(self):
        self.client.remove_container(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'DELETE',
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': False, 'force': False},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_container_with_dict_instead_of_id(self):
        self.client.remove_container({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'DELETE',
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': False, 'force': False},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_link(self):
        self.client.remove_container(fake_api.FAKE_CONTAINER_ID, link=True)

        fake_request.assert_called_with(
            'DELETE',
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': True, 'force': False},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_export(self):
        self.client.export(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/export',
            stream=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_export_with_dict_instead_of_id(self):
        self.client.export({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/export',
            stream=True,
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_container(self):
        self.client.inspect_container(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/json',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_container_undefined_id(self):
        for arg in None, '', {True: True}:
            with pytest.raises(docker.errors.NullResource) as excinfo:
                self.client.inspect_container(arg)

            self.assertEqual(
                excinfo.value.args[0], 'image or container param is undefined'
            )

    def test_container_stats(self):
        self.client.stats(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/stats',
            timeout=60,
            stream=True
        )

    def test_container_top(self):
        self.client.top(fake_api.FAKE_CONTAINER_ID)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/top',
            params={},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_container_top_with_psargs(self):
        self.client.top(fake_api.FAKE_CONTAINER_ID, 'waux')

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/top',
            params={'ps_args': 'waux'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    ##################
    #  IMAGES TESTS  #
    ##################

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
                'author': None
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

        self.client.build(fileobj=script)

    def test_build_container_pull(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))

        self.client.build(fileobj=script, pull=True)

    def test_build_container_stream(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))

        self.client.build(fileobj=script, stream=True)

    def test_build_container_custom_context(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script)

        self.client.build(fileobj=context, custom_context=True)

    def test_build_container_custom_context_gzip(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script)
        gz_context = gzip.GzipFile(fileobj=context)

        self.client.build(
            fileobj=gz_context,
            custom_context=True,
            encoding="gzip"
        )

    def test_build_remote_with_registry_auth(self):
        self.client._auth_configs = {
            'https://example.com': {
                'user': 'example',
                'password': 'example',
                'email': 'example@example.com'
            }
        }

        self.client.build(path='https://github.com/docker-library/mongo')

    def test_build_container_with_named_dockerfile(self):
        self.client.build('.', dockerfile='nameddockerfile')

    def test_build_container_with_container_limits(self):
        self.client.build('.', container_limits={
            'memory': 1024 * 1024,
            'cpusetcpus': 1,
            'cpushares': 1000,
            'memswap': 1024 * 1024 * 8
        })

    def test_build_container_invalid_container_limits(self):
        self.assertRaises(
            docker.errors.DockerException,
            lambda: self.client.build('.', container_limits={
                'foo': 'bar'
            })
        )

    ###################
    #  VOLUMES TESTS  #
    ###################

    @base.requires_api_version('1.21')
    def test_list_volumes(self):
        volumes = self.client.volumes()
        self.assertIn('Volumes', volumes)
        self.assertEqual(len(volumes['Volumes']), 2)
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'GET')
        self.assertEqual(args[0][1], url_prefix + 'volumes')

    @base.requires_api_version('1.21')
    def test_create_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.create_volume(name)
        self.assertIn('Name', result)
        self.assertEqual(result['Name'], name)
        self.assertIn('Driver', result)
        self.assertEqual(result['Driver'], 'local')
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'POST')
        self.assertEqual(args[0][1], url_prefix + 'volumes')
        self.assertEqual(json.loads(args[1]['data']), {'Name': name})

    @base.requires_api_version('1.21')
    def test_create_volume_with_driver(self):
        name = 'perfectcherryblossom'
        driver_name = 'sshfs'
        self.client.create_volume(name, driver=driver_name)
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'POST')
        self.assertEqual(args[0][1], url_prefix + 'volumes')
        data = json.loads(args[1]['data'])
        self.assertIn('Driver', data)
        self.assertEqual(data['Driver'], driver_name)

    @base.requires_api_version('1.21')
    def test_create_volume_invalid_opts_type(self):
        with pytest.raises(TypeError):
            self.client.create_volume(
                'perfectcherryblossom', driver_opts='hello=world'
            )

        with pytest.raises(TypeError):
            self.client.create_volume(
                'perfectcherryblossom', driver_opts=['hello=world']
            )

        with pytest.raises(TypeError):
            self.client.create_volume(
                'perfectcherryblossom', driver_opts=''
            )

    @base.requires_api_version('1.21')
    def test_inspect_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.inspect_volume(name)
        self.assertIn('Name', result)
        self.assertEqual(result['Name'], name)
        self.assertIn('Driver', result)
        self.assertEqual(result['Driver'], 'local')
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'GET')
        self.assertEqual(args[0][1], '{0}volumes/{1}'.format(url_prefix, name))

    @base.requires_api_version('1.21')
    def test_remove_volume(self):
        name = 'perfectcherryblossom'
        result = self.client.remove_volume(name)
        self.assertTrue(result)
        args = fake_request.call_args

        self.assertEqual(args[0][0], 'DELETE')
        self.assertEqual(args[0][1], '{0}volumes/{1}'.format(url_prefix, name))

    #####################
    #   NETWORK TESTS   #
    #####################

    @base.requires_api_version('1.21')
    def test_create_network(self):
        network_data = {
            "id": 'abc12345',
            "warning": "",
        }

        network_response = response(status_code=200, content=network_data)
        post = mock.Mock(return_value=network_response)

        with mock.patch('docker.Client.post', post):
            result = self.client.create_network('foo')
            self.assertEqual(result, network_data)

            self.assertEqual(
                post.call_args[0][0],
                url_prefix + 'networks/create')

            self.assertEqual(
                json.loads(post.call_args[1]['data']),
                {"name": "foo"})

            self.client.create_network('foo', 'bridge')

            self.assertEqual(
                json.loads(post.call_args[1]['data']),
                {"name": "foo", "driver": "bridge"})

    @base.requires_api_version('1.21')
    def test_remove_network(self):
        network_id = 'abc12345'
        delete = mock.Mock(return_value=response(status_code=200))

        with mock.patch('docker.Client.delete', delete):
            self.client.remove_network(network_id)

        args = delete.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'networks/{0}'.format(network_id))

    @base.requires_api_version('1.21')
    def test_inspect_network(self):
        network_id = 'abc12345'
        network_name = 'foo'
        network_data = {
            six.u('name'): network_name,
            six.u('id'): network_id,
            six.u('driver'): 'bridge',
            six.u('containers'): {},
        }

        network_response = response(status_code=200, content=network_data)
        get = mock.Mock(return_value=network_response)

        with mock.patch('docker.Client.get', get):
            result = self.client.inspect_network(network_id)
            self.assertEqual(result, network_data)

        args = get.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'networks/{0}'.format(network_id))

    @base.requires_api_version('1.21')
    def test_connect_container_to_network(self):
        network_id = 'abc12345'
        container_id = 'def45678'

        post = mock.Mock(return_value=response(status_code=201))

        with mock.patch('docker.Client.post', post):
            self.client.connect_container_to_network(
                {'Id': container_id}, network_id)

        self.assertEqual(
            post.call_args[0][0],
            url_prefix + 'networks/{0}/connect'.format(network_id))

        self.assertEqual(
            json.loads(post.call_args[1]['data']),
            {'container': container_id})

    @base.requires_api_version('1.21')
    def test_disconnect_container_from_network(self):
        network_id = 'abc12345'
        container_id = 'def45678'

        post = mock.Mock(return_value=response(status_code=201))

        with mock.patch('docker.Client.post', post):
            self.client.disconnect_container_from_network(
                {'Id': container_id}, network_id)

        self.assertEqual(
            post.call_args[0][0],
            url_prefix + 'networks/{0}/disconnect'.format(network_id))

        self.assertEqual(
            json.loads(post.call_args[1]['data']),
            {'container': container_id})

    #######################
    #  PY SPECIFIC TESTS  #
    #######################

    def test_load_config_no_file(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg = docker.auth.load_config(folder)
        self.assertTrue(cfg is not None)

    def test_load_config(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, '.dockercfg')
        with open(dockercfg_path, 'w') as f:
            auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
            f.write('auth = {0}\n'.format(auth_))
            f.write('email = sakuya@scarlet.net')
        cfg = docker.auth.load_config(dockercfg_path)
        self.assertTrue(docker.auth.INDEX_NAME in cfg)
        self.assertNotEqual(cfg[docker.auth.INDEX_NAME], None)
        cfg = cfg[docker.auth.INDEX_NAME]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('auth'), None)

    def test_load_config_with_random_name(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder,
                                      '.{0}.dockercfg'.format(
                                          random.randrange(100000)))
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            registry: {
                'auth': '{0}'.format(auth_),
                'email': 'sakuya@scarlet.net'
            }
        }

        with open(dockercfg_path, 'w') as f:
            f.write(json.dumps(config))

        cfg = docker.auth.load_config(dockercfg_path)
        self.assertTrue(registry in cfg)
        self.assertNotEqual(cfg[registry], None)
        cfg = cfg[registry]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('auth'), None)

    def test_tar_with_excludes(self):
        dirs = [
            'foo',
            'foo/bar',
            'bar',
        ]

        files = [
            'Dockerfile',
            'Dockerfile.alt',
            '.dockerignore',
            'a.py',
            'a.go',
            'b.py',
            'cde.py',
            'foo/a.py',
            'foo/b.py',
            'foo/bar/a.py',
            'bar/a.py',
        ]

        exclude = [
            '*.py',
            '!b.py',
            '!a.go',
            'foo',
            'Dockerfile*',
            '.dockerignore',
        ]

        expected_names = set([
            'Dockerfile',
            '.dockerignore',
            'a.go',
            'b.py',
            'bar',
            'bar/a.py',
        ])

        base = make_tree(dirs, files)
        self.addCleanup(shutil.rmtree, base)

        with docker.utils.tar(base, exclude=exclude) as archive:
            tar = tarfile.open(fileobj=archive)
            assert sorted(tar.getnames()) == sorted(expected_names)

    def test_tar_with_empty_directory(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        with docker.utils.tar(base) as archive:
            tar = tarfile.open(fileobj=archive)
            self.assertEqual(sorted(tar.getnames()), ['bar', 'foo'])

    def test_tar_with_file_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        with open(os.path.join(base, 'foo'), 'w') as f:
            f.write("content")
        os.makedirs(os.path.join(base, 'bar'))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with docker.utils.tar(base) as archive:
            tar = tarfile.open(fileobj=archive)
            self.assertEqual(sorted(tar.getnames()), ['bar', 'bar/foo', 'foo'])

    def test_tar_with_directory_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with docker.utils.tar(base) as archive:
            tar = tarfile.open(fileobj=archive)
            self.assertEqual(sorted(tar.getnames()), ['bar', 'bar/foo', 'foo'])

    #######################
    #  HOST CONFIG TESTS  #
    #######################

    def test_create_host_config_secopt(self):
        security_opt = ['apparmor:test_profile']
        result = self.client.create_host_config(security_opt=security_opt)
        self.assertIn('SecurityOpt', result)
        self.assertEqual(result['SecurityOpt'], security_opt)

        self.assertRaises(
            docker.errors.DockerException, self.client.create_host_config,
            security_opt='wrong'
        )


class StreamTest(Cleanup, base.BaseTestCase):

    def setUp(self):
        socket_dir = tempfile.mkdtemp()
        self.build_context = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, socket_dir)
        self.addCleanup(shutil.rmtree, self.build_context)
        self.socket_file = os.path.join(socket_dir, 'test_sock.sock')
        self.server_socket = self._setup_socket()
        self.stop_server = False
        server_thread = threading.Thread(target=self.run_server)
        server_thread.setDaemon(True)
        server_thread.start()
        self.response = None
        self.request_handler = None
        self.addCleanup(server_thread.join)
        self.addCleanup(self.stop)

    def stop(self):
        self.stop_server = True

    def _setup_socket(self):
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(self.socket_file)
        # Non-blocking mode so that we can shut the test down easily
        server_sock.setblocking(0)
        server_sock.listen(5)
        return server_sock

    def run_server(self):
        try:
            while not self.stop_server:
                try:
                    connection, client_address = self.server_socket.accept()
                except socket.error:
                    # Probably no connection to accept yet
                    time.sleep(0.01)
                    continue

                connection.setblocking(1)
                try:
                    self.request_handler(connection)
                finally:
                    connection.close()
        finally:
            self.server_socket.close()

    def early_response_sending_handler(self, connection):
        data = b''
        headers = None

        connection.sendall(self.response)
        while not headers:
            data += connection.recv(2048)
            parts = data.split(b'\r\n\r\n', 1)
            if len(parts) == 2:
                headers, data = parts

        mo = re.search(r'Content-Length: ([0-9]+)', headers.decode())
        assert mo
        content_length = int(mo.group(1))

        while True:
            if len(data) >= content_length:
                break

            data += connection.recv(2048)

    def test_early_stream_response(self):
        self.request_handler = self.early_response_sending_handler
        lines = []
        for i in range(0, 50):
            line = str(i).encode()
            lines += [('%x' % len(line)).encode(), line]
        lines.append(b'0')
        lines.append(b'')

        self.response = (
            b'HTTP/1.1 200 OK\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
        ) + b'\r\n'.join(lines)

        with docker.Client(base_url="http+unix://" + self.socket_file) \
                as client:
            for i in range(5):
                try:
                    stream = client.build(
                        path=self.build_context,
                        stream=True
                    )
                    break
                except requests.ConnectionError as e:
                    if i == 4:
                        raise e

            self.assertEqual(list(stream), [
                str(i).encode() for i in range(50)])
