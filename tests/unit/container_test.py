import datetime
import json
import signal

import docker
import pytest
import six

from . import fake_api
from .api_test import (
    DockerClientTest, url_prefix, fake_request, DEFAULT_TIMEOUT_SECONDS,
    fake_inspect_container
)

try:
    from unittest import mock
except ImportError:
    import mock


def fake_inspect_container_tty(self, container):
    return fake_inspect_container(self, container, tty=True)


class StartContainerTest(DockerClientTest):
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


class CreateContainerTest(DockerClientTest):
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


class ContainerTest(DockerClientTest):
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

    def test_log_since(self):
        ts = 809222400
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             since=ts)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 'all', 'since': ts},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_log_since_with_datetime(self):
        ts = 809222400
        time = datetime.datetime.utcfromtimestamp(ts)
        with mock.patch('docker.Client.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             since=time)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 'all', 'since': ts},
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
