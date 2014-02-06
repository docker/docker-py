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
import signal
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
url_prefix = 'http+unix://var/run/docker.sock/v{0}/'.format(
    docker.client.DEFAULT_DOCKER_API_VERSION)


@mock.patch.multiple('docker.Client', get=fake_request, post=fake_request,
                     put=fake_request, delete=fake_request)
class DockerClientTest(unittest.TestCase):
    def setUp(self):
        self.client = docker.Client()
        # Force-clear authconfig to avoid tampering with the tests
        self.client._cfg = {'Configs': {}}

    #########################
    ##  INFORMATION TESTS  ##
    #########################
    def test_version(self):
        try:
            self.client.version()
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'version',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_info(self):
        try:
            self.client.info()
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'info',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_search(self):
        try:
            self.client.search('busybox')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/search',
            params={'term': 'busybox'},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_viz(self):
        try:
            self.client.images('busybox', viz=True)
            self.fail('Viz output should not be supported!')
        except Exception:
            pass

    ###################
    ## LISTING TESTS ##
    ###################

    def test_images(self):
        try:
            self.client.images(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        fake_request.assert_called_with(
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 0, 'all': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_images_quiet(self):
        try:
            self.client.images(all=True, quiet=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        fake_request.assert_called_with(
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 1, 'all': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_ids(self):
        try:
            self.client.images(quiet=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/json',
            params={'filter': None, 'only_ids': 1, 'all': 0},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_list_containers(self):
        try:
            self.client.containers(all=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/json',
            params={
                'all': 1,
                'since': None,
                'limit': -1,
                'trunc_cmd': 1,
                'before': None
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
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
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false, "Memory": 0,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": false,
                             "OpenStdin": false, "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_binds(self):
        mount_dest = '/mnt'
        #mount_origin = '/tmp'

        try:
            self.client.create_container('busybox', ['ls', mount_dest],
                                         volumes=[mount_dest])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
                             "Volumes": {"/mnt": {}}, "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_ports(self):
        try:
            self.client.create_container('busybox', 'ls',
                                         ports=[1111, (2222, 'udp'), (3333,)])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "Memory": 0, "ExposedPorts": {
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
        try:
            self.client.create_container('busybox', 'hello',
                                         entrypoint='cowsay')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["hello"], "AttachStdin": false,
                             "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "Entrypoint": "cowsay"}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_cpu_shares(self):
        try:
            self.client.create_container('busybox', 'ls',
                                         cpu_shares=5)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "CpuShares": 5}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_working_dir(self):
        try:
            self.client.create_container('busybox', 'ls',
                                         working_dir='/root')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox",
                             "Cmd": ["ls"], "AttachStdin": false,
                             "Memory": 0,
                             "AttachStderr": true,
                             "AttachStdout": true, "OpenStdin": false,
                             "StdinOnce": false,
                             "NetworkDisabled": false,
                             "WorkingDir": "/root"}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_container_with_stdin_open(self):
        try:
            self.client.create_container('busybox', 'true', stdin_open=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": true, "Memory": 0,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": true,
                             "OpenStdin": true, "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})

    def test_create_named_container(self):
        try:
            self.client.create_container('busybox', 'true',
                                         name='marisa-kirisame')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0],
                         url_prefix + 'containers/create')
        self.assertEqual(json.loads(args[1]['data']),
                         json.loads('''
                            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
                             "AttachStdin": false, "Memory": 0,
                             "AttachStderr": true, "AttachStdout": true,
                             "StdinOnce": false,
                             "OpenStdin": false, "NetworkDisabled": false}'''))
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(args[1]['params'], {'name': 'marisa-kirisame'})

    def test_start_container(self):
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            raise e
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_lxc_conf(self):
        try:
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf={'lxc.conf.k': 'lxc.conf.value'}
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"LxcConf": [{"Value": "lxc.conf.value", "Key": "lxc.conf.k"}],
             "PublishAllPorts": False, "Privileged": False}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_lxc_conf_compat(self):
        try:
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf=[{'Key': 'lxc.conf.k', 'Value': 'lxc.conf.value'}]
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        self.assertEqual(
            json.loads(args[1]['data']),
            {
                "LxcConf": [{"Key": "lxc.conf.k", "Value": "lxc.conf.value"}],
                "PublishAllPorts": False,
                "Privileged": False,
            }
        )
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_binds(self):
        try:
            mount_dest = '/mnt'
            mount_origin = '/tmp'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              binds={mount_origin: mount_dest})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        self.assertEqual(json.loads(args[1]['data']),
                         {"Binds": ["/tmp:/mnt"],
                          "PublishAllPorts": False,
                          "Privileged": False})
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_port_binds(self):
        self.maxDiff = None
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID, port_bindings={
                1111: None,
                2222: 2222,
                '3333/udp': (3333,),
                4444: ('127.0.0.1',),
                5555: ('127.0.0.1', 5555),
                6666: [('127.0.0.1',), ('192.168.0.1',)]
            })
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(args[0][0], url_prefix +
                         'containers/3cc2351ab11b/start')
        data = json.loads(args[1]['data'])
        self.assertEqual(data['PublishAllPorts'], False)
        self.assertTrue('1111/tcp' in data['PortBindings'])
        self.assertTrue('2222/tcp' in data['PortBindings'])
        self.assertTrue('3333/udp' in data['PortBindings'])
        self.assertTrue('4444/tcp' in data['PortBindings'])
        self.assertTrue('5555/tcp' in data['PortBindings'])
        self.assertTrue('6666/tcp' in data['PortBindings'])
        self.assertEqual(
            [{"HostPort": "", "HostIp": ""}],
            data['PortBindings']['1111/tcp']
        )
        self.assertEqual(
            [{"HostPort": "2222", "HostIp": ""}],
            data['PortBindings']['2222/tcp']
        )
        self.assertEqual(
            [{"HostPort": "3333", "HostIp": ""}],
            data['PortBindings']['3333/udp']
        )
        self.assertEqual(
            [{"HostPort": "", "HostIp": "127.0.0.1"}],
            data['PortBindings']['4444/tcp']
        )
        self.assertEqual(
            [{"HostPort": "5555", "HostIp": "127.0.0.1"}],
            data['PortBindings']['5555/tcp']
        )
        self.assertEqual(len(data['PortBindings']['6666/tcp']), 2)
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_links(self):
        # one link
        try:
            link_path = 'path'
            alias = 'alias'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              links={link_path: alias})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False,
             "Links": ["path:alias"]}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )

    def test_start_container_with_multiple_links(self):
        try:
            link_path = 'path'
            alias = 'alias'
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                links={
                    link_path + '1': alias + '1',
                    link_path + '2': alias + '2'
                }
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {
                "PublishAllPorts": False,
                "Privileged": False,
                "Links": ["path1:alias1", "path2:alias2"]
            }
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )

    def test_start_container_with_links_as_list_of_tuples(self):
        # one link
        try:
            link_path = 'path'
            alias = 'alias'
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              links=[(link_path, alias)])
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False,
             "Links": ["path:alias"]}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )

    def test_start_container_privileged(self):
        try:
            self.client.start(fake_api.FAKE_CONTAINER_ID, privileged=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(json.loads(args[1]['data']),
                         {"PublishAllPorts": False, "Privileged": True})
        self.assertEqual(args[1]['headers'],
                         {'Content-Type': 'application/json'})
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_start_container_with_dict_instead_of_id(self):
        try:
            self.client.start({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))
        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'containers/3cc2351ab11b/start'
        )
        self.assertEqual(
            json.loads(args[1]['data']),
            {"PublishAllPorts": False, "Privileged": False}
        )
        self.assertEqual(
            args[1]['headers'],
            {'Content-Type': 'application/json'}
        )
        self.assertEqual(
            args[1]['timeout'],
            docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_wait(self):
        try:
            self.client.wait(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None
        )

    def test_wait_with_dict_instead_of_id(self):
        try:
            self.client.wait({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            raise e
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None
        )

    def test_url_compatibility_unix(self):
        c = docker.Client(base_url="unix://socket")

        assert c.base_url == "http+unix://socket"

    def test_url_compatibility_unix_triple_slash(self):
        c = docker.Client(base_url="unix:///socket")

        assert c.base_url == "http+unix://socket"

    def test_url_compatibility_http_unix_triple_slash(self):
        c = docker.Client(base_url="http+unix:///socket")

        assert c.base_url == "http+unix://socket"

    def test_url_compatibility_http(self):
        c = docker.Client(base_url="http://hostname")

        assert c.base_url == "http://hostname"

    def test_url_compatibility_tcp(self):
        c = docker.Client(base_url="tcp://hostname")

        assert c.base_url == "http://hostname"

    def test_logs(self):
        try:
            self.client.logs(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/attach',
            params={'stream': 0, 'logs': 1, 'stderr': 1, 'stdout': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_logs_with_dict_instead_of_id(self):
        try:
            self.client.logs({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/attach',
            params={'stream': 0, 'logs': 1, 'stderr': 1, 'stdout': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_log_streaming(self):
        try:
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/attach',
            params={'stream': 1, 'logs': 1, 'stderr': 1, 'stdout': 1},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS,
            stream=True
        )

    def test_diff(self):
        try:
            self.client.diff(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/changes',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_diff_with_dict_instead_of_id(self):
        try:
            self.client.diff({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/changes',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_port(self):
        try:
            self.client.port({'Id': fake_api.FAKE_CONTAINER_ID}, 1111)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/json',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_stop_container(self):
        try:
            self.client.stop(fake_api.FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/stop',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_stop_container_with_dict_instead_of_id(self):
        try:
            self.client.stop({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/stop',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container(self):
        try:
            self.client.kill(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container_with_dict_instead_of_id(self):
        try:
            self.client.kill({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_kill_container_with_signal(self):
        try:
            self.client.kill(fake_api.FAKE_CONTAINER_ID, signal=signal.SIGTERM)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/kill',
            params={'signal': signal.SIGTERM},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_restart_container(self):
        try:
            self.client.restart(fake_api.FAKE_CONTAINER_ID, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception : {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/restart',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_restart_container_with_dict_instead_of_id(self):
        try:
            self.client.restart({'Id': fake_api.FAKE_CONTAINER_ID}, timeout=2)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/restart',
            params={'t': 2},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_container(self):
        try:
            self.client.remove_container(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': False},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_container_with_dict_instead_of_id(self):
        try:
            self.client.remove_container({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': False},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_link(self):
        try:
            self.client.remove_container(fake_api.FAKE_CONTAINER_ID, link=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': True},
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_export(self):
        try:
            self.client.export(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/export',
            stream=True,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_export_with_dict_instead_of_id(self):
        try:
            self.client.export({'Id': fake_api.FAKE_CONTAINER_ID})
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/export',
            stream=True,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_container(self):
        try:
            self.client.inspect_container(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'containers/3cc2351ab11b/json',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    ##################
    ## IMAGES TESTS ##
    ##################

    def test_pull(self):
        try:
            self.client.pull('joffrey/test001')
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'images/create'
        )
        self.assertEqual(
            args[1]['params'],
            {'tag': None, 'fromImage': 'joffrey/test001'}
        )
        self.assertFalse(args[1]['stream'])

    def test_pull_stream(self):
        try:
            self.client.pull('joffrey/test001', stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        args = fake_request.call_args
        self.assertEqual(
            args[0][0],
            url_prefix + 'images/create'
        )
        self.assertEqual(
            args[1]['params'],
            {'tag': None, 'fromImage': 'joffrey/test001'}
        )
        self.assertTrue(args[1]['stream'])

    def test_commit(self):
        try:
            self.client.commit(fake_api.FAKE_CONTAINER_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
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
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_remove_image(self):
        try:
            self.client.remove_image(fake_api.FAKE_IMAGE_ID)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_image_history(self):
        try:
            self.client.history(fake_api.FAKE_IMAGE_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/history',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image(self):
        try:
            self.client.import_image(
                fake_api.FAKE_TARBALL_PATH,
                repository=fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': fake_api.FAKE_TARBALL_PATH
            },
            data=None,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_import_image_from_file(self):
        buf = tempfile.NamedTemporaryFile(delete=False)
        try:
            # pretent the buffer is a file
            self.client.import_image(
                buf.name,
                repository=fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromSrc': '-'
            },
            data='',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )
        buf.close()
        os.remove(buf.name)

    def test_import_image_from_image(self):
        try:
            self.client.import_image(
                image=fake_api.FAKE_IMAGE_NAME,
                repository=fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/create',
            params={
                'repo': fake_api.FAKE_REPO_NAME,
                'tag': fake_api.FAKE_TAG_NAME,
                'fromImage': fake_api.FAKE_IMAGE_NAME
            },
            data=None,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_inspect_image(self):
        try:
            self.client.inspect_image(fake_api.FAKE_IMAGE_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/json',
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_insert_image(self):
        try:
            self.client.insert(fake_api.FAKE_IMAGE_NAME,
                               fake_api.FAKE_URL, fake_api.FAKE_PATH)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/insert',
            params={
                'url': fake_api.FAKE_URL,
                'path': fake_api.FAKE_PATH
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image(self):
        try:
            self.client.push(fake_api.FAKE_IMAGE_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/push',
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=False,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_push_image_stream(self):
        try:
            self.client.push(fake_api.FAKE_IMAGE_NAME, stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/test_image/push',
            data='{}',
            headers={'Content-Type': 'application/json'},
            stream=True,
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image(self):
        try:
            self.client.tag(fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': None,
                'repo': 'repo',
                'force': 0
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_tag(self):
        try:
            self.client.tag(
                fake_api.FAKE_IMAGE_ID,
                fake_api.FAKE_REPO_NAME,
                tag=fake_api.FAKE_TAG_NAME
            )
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': 'tag',
                'repo': 'repo',
                'force': 0
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
        )

    def test_tag_image_force(self):
        try:
            self.client.tag(
                fake_api.FAKE_IMAGE_ID, fake_api.FAKE_REPO_NAME, force=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

        fake_request.assert_called_with(
            url_prefix + 'images/e9aa60c60128/tag',
            params={
                'tag': None,
                'repo': 'repo',
                'force': 1
            },
            timeout=docker.client.DEFAULT_TIMEOUT_SECONDS
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

    def test_build_container_stream(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        try:
            self.client.build(fileobj=script, stream=True)
        except Exception as e:
            self.fail('Command should not raise exception: {0}'.format(e))

    #######################
    ## PY SPECIFIC TESTS ##
    #######################

    def test_load_config_no_file(self):
        folder = tempfile.mkdtemp()
        cfg = docker.auth.load_config(folder)
        self.assertTrue(cfg is not None)

    def test_load_config(self):
        folder = tempfile.mkdtemp()
        f = open(os.path.join(folder, '.dockercfg'), 'w')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        f.write('auth = {0}\n'.format(auth_))
        f.write('email = sakuya@scarlet.net')
        f.close()
        cfg = docker.auth.load_config(folder)
        self.assertTrue(docker.auth.INDEX_URL in cfg)
        self.assertNotEqual(cfg[docker.auth.INDEX_URL], None)
        cfg = cfg[docker.auth.INDEX_URL]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('auth'), None)


if __name__ == '__main__':
    unittest.main()
