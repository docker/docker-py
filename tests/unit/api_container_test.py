# -*- coding: utf-8 -*-

import datetime
import json
import signal

import docker
import pytest
import six

from . import fake_api
from ..helpers import requires_api_version
from .api_test import (
    BaseAPIClientTest, url_prefix, fake_request, DEFAULT_TIMEOUT_SECONDS,
    fake_inspect_container
)

try:
    from unittest import mock
except ImportError:
    import mock


def fake_inspect_container_tty(self, container):
    return fake_inspect_container(self, container, tty=True)


class StartContainerTest(BaseAPIClientTest):
    def test_start_container(self):
        self.client.start(fake_api.FAKE_CONTAINER_ID)

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/3cc2351ab11b/start'
        assert 'data' not in args[1]
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_start_container_none(self):
        with pytest.raises(ValueError) as excinfo:
            self.client.start(container=None)

        assert str(excinfo.value) == 'Resource ID was not provided'

        with pytest.raises(ValueError) as excinfo:
            self.client.start(None)

        assert str(excinfo.value) == 'Resource ID was not provided'

    def test_start_container_regression_573(self):
        self.client.start(**{'container': fake_api.FAKE_CONTAINER_ID})

    def test_start_container_with_lxc_conf(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf={'lxc.conf.k': 'lxc.conf.value'}
            )

    def test_start_container_with_lxc_conf_compat(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                lxc_conf=[{'Key': 'lxc.conf.k', 'Value': 'lxc.conf.value'}]
            )

    def test_start_container_with_binds_ro(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(
                fake_api.FAKE_CONTAINER_ID, binds={
                    '/tmp': {
                        "bind": '/mnt',
                        "ro": True
                    }
                }
            )

    def test_start_container_with_binds_rw(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(
                fake_api.FAKE_CONTAINER_ID, binds={
                    '/tmp': {"bind": '/mnt', "ro": False}
                }
            )

    def test_start_container_with_port_binds(self):
        self.maxDiff = None

        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(fake_api.FAKE_CONTAINER_ID, port_bindings={
                1111: None,
                2222: 2222,
                '3333/udp': (3333,),
                4444: ('127.0.0.1',),
                5555: ('127.0.0.1', 5555),
                6666: [('127.0.0.1',), ('192.168.0.1',)]
            })

    def test_start_container_with_links(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(
                fake_api.FAKE_CONTAINER_ID, links={'path': 'alias'}
            )

    def test_start_container_with_multiple_links(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(
                fake_api.FAKE_CONTAINER_ID,
                links={
                    'path1': 'alias1',
                    'path2': 'alias2'
                }
            )

    def test_start_container_with_links_as_list_of_tuples(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(fake_api.FAKE_CONTAINER_ID,
                              links=[('path', 'alias')])

    def test_start_container_privileged(self):
        with pytest.raises(docker.errors.DeprecatedMethod):
            self.client.start(fake_api.FAKE_CONTAINER_ID, privileged=True)

    def test_start_container_with_dict_instead_of_id(self):
        self.client.start({'Id': fake_api.FAKE_CONTAINER_ID})

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/3cc2351ab11b/start'
        assert 'data' not in args[1]
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS


class CreateContainerTest(BaseAPIClientTest):
    def test_create_container(self):
        self.client.create_container('busybox', 'true')

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
             "AttachStdin": false,
             "AttachStderr": true, "AttachStdout": true,
             "StdinOnce": false,
             "OpenStdin": false, "NetworkDisabled": false}
         ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_binds(self):
        mount_dest = '/mnt'

        self.client.create_container('busybox', ['ls', mount_dest],
                                     volumes=[mount_dest])

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
             "Volumes": {"/mnt": {}},
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_volume_string(self):
        mount_dest = '/mnt'

        self.client.create_container('busybox', ['ls', mount_dest],
                                     volumes=mount_dest)

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls", "/mnt"], "AttachStdin": false,
             "Volumes": {"/mnt": {}},
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_ports(self):
        self.client.create_container('busybox', 'ls',
                                     ports=[1111, (2222, 'udp'), (3333,)])

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
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
             "NetworkDisabled": false}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_entrypoint(self):
        self.client.create_container('busybox', 'hello',
                                     entrypoint='cowsay entry')

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["hello"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "Entrypoint": ["cowsay", "entry"]}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_host_config_cpu_shares(self):
        self.client.create_container(
            'busybox', 'ls', host_config=self.client.create_host_config(
                cpu_shares=512
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'

        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "HostConfig": {
                "CpuShares": 512,
                "NetworkMode": "default"
             }}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_host_config_cpuset(self):
        self.client.create_container(
            'busybox', 'ls', host_config=self.client.create_host_config(
                cpuset_cpus='0,1'
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'

        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "HostConfig": {
                "CpusetCpus": "0,1",
                "NetworkMode": "default"
             }}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_host_config_cpuset_mems(self):
        self.client.create_container(
            'busybox', 'ls', host_config=self.client.create_host_config(
                cpuset_mems='0'
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'

        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "HostConfig": {
                "CpusetMems": "0",
                "NetworkMode": "default"
            }}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_cgroup_parent(self):
        self.client.create_container(
            'busybox', 'ls', host_config=self.client.create_host_config(
                cgroup_parent='test'
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        data = json.loads(args[1]['data'])
        assert 'HostConfig' in data
        assert 'CgroupParent' in data['HostConfig']
        assert data['HostConfig']['CgroupParent'] == 'test'

    def test_create_container_with_working_dir(self):
        self.client.create_container('busybox', 'ls',
                                     working_dir='/root')

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "WorkingDir": "/root"}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_stdin_open(self):
        self.client.create_container('busybox', 'true', stdin_open=True)

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
             "AttachStdin": true,
             "AttachStderr": true, "AttachStdout": true,
             "StdinOnce": true,
             "OpenStdin": true, "NetworkDisabled": false}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_named_container(self):
        self.client.create_container('busybox', 'true',
                                     name='marisa-kirisame')

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox", "Cmd": ["true"],
             "AttachStdin": false,
             "AttachStderr": true, "AttachStdout": true,
             "StdinOnce": false,
             "OpenStdin": false, "NetworkDisabled": false}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['params'] == {'name': 'marisa-kirisame'}

    def test_create_container_with_mem_limit_as_int(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit=128.0
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        assert data['HostConfig']['Memory'] == 128.0

    def test_create_container_with_mem_limit_as_string(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        assert data['HostConfig']['Memory'] == 128.0

    def test_create_container_with_mem_limit_as_string_with_k_unit(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128k'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        assert data['HostConfig']['Memory'] == 128.0 * 1024

    def test_create_container_with_mem_limit_as_string_with_m_unit(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128m'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        assert data['HostConfig']['Memory'] == 128.0 * 1024 * 1024

    def test_create_container_with_mem_limit_as_string_with_g_unit(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                mem_limit='128g'
            )
        )

        args = fake_request.call_args
        data = json.loads(args[1]['data'])
        assert data['HostConfig']['Memory'] == 128.0 * 1024 * 1024 * 1024

    def test_create_container_with_mem_limit_as_string_with_wrong_value(self):
        with pytest.raises(docker.errors.DockerException):
            self.client.create_host_config(mem_limit='128p')

        with pytest.raises(docker.errors.DockerException):
            self.client.create_host_config(mem_limit='1f28')

    def test_create_container_with_lxc_conf(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                lxc_conf={'lxc.conf.k': 'lxc.conf.value'}
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['LxcConf'] = [
            {"Value": "lxc.conf.value", "Key": "lxc.conf.k"}
        ]

        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_lxc_conf_compat(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                lxc_conf=[{'Key': 'lxc.conf.k', 'Value': 'lxc.conf.value'}]
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['LxcConf'] = [
            {"Value": "lxc.conf.value", "Key": "lxc.conf.k"}
        ]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["/tmp:/mnt:ro"]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["/tmp:/mnt:rw"]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = ["/tmp:/mnt:z"]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Binds'] = [
            "/tmp:/mnt/1:ro",
            "/tmp:/mnt/2",
        ]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        data = json.loads(args[1]['data'])
        port_bindings = data['HostConfig']['PortBindings']
        assert '1111/tcp' in port_bindings
        assert '2222/tcp' in port_bindings
        assert '3333/udp' in port_bindings
        assert '4444/tcp' in port_bindings
        assert '5555/tcp' in port_bindings
        assert '6666/tcp' in port_bindings
        assert [{"HostPort": "", "HostIp": ""}] == port_bindings['1111/tcp']
        assert [
            {"HostPort": "2222", "HostIp": ""}
        ] == port_bindings['2222/tcp']
        assert [
            {"HostPort": "3333", "HostIp": ""}
        ] == port_bindings['3333/udp']
        assert [
            {"HostPort": "", "HostIp": "127.0.0.1"}
        ] == port_bindings['4444/tcp']
        assert [
            {"HostPort": "5555", "HostIp": "127.0.0.1"}
        ] == port_bindings['5555/tcp']
        assert len(port_bindings['6666/tcp']) == 2
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_mac_address(self):
        expected = "02:42:ac:11:00:0a"

        self.client.create_container(
            'busybox',
            ['sleep', '60'],
            mac_address=expected
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        data = json.loads(args[1]['data'])
        assert data['MacAddress'] == expected

    def test_create_container_with_links(self):
        link_path = 'path'
        alias = 'alias'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                links={link_path: alias}
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Links'] = ['path:alias']

        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

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
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Links'] = [
            'path1:alias1', 'path2:alias2'
        ]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_with_links_as_list_of_tuples(self):
        link_path = 'path'
        alias = 'alias'

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                links=[(link_path, alias)]
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Links'] = ['path:alias']

        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    def test_create_container_privileged(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(privileged=True)
        )

        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Privileged'] = True
        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'

        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['RestartPolicy'] = {
            "MaximumRetryCount": 0, "Name": "always"
        }
        assert json.loads(args[1]['data']) == expected_payload

        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_added_capabilities(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(cap_add=['MKNOD'])
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['CapAdd'] = ['MKNOD']
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_dropped_capabilities(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(cap_drop=['MKNOD'])
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['CapDrop'] = ['MKNOD']
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_devices(self):
        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                devices=['/dev/sda:/dev/xvda:rwm',
                         '/dev/sdb:/dev/xvdb',
                         '/dev/sdc']
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
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
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data'])['Labels'] == labels_dict
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

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
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data'])['Labels'] == labels_dict
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_named_volume(self):
        mount_dest = '/mnt'
        volume_name = 'name'

        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(
                volume_driver='foodriver',
                binds={volume_name: {
                    "bind": mount_dest,
                    "ro": False
                }}),
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['VolumeDriver'] = 'foodriver'
        expected_payload['HostConfig']['Binds'] = ["name:/mnt:rw"]
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_stop_signal(self):
        self.client.create_container('busybox', 'ls',
                                     stop_signal='SIGINT')

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "StopSignal": "SIGINT"}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}

    @requires_api_version('1.22')
    def test_create_container_with_aliases(self):
        self.client.create_container(
            'busybox', 'ls',
            host_config=self.client.create_host_config(
                network_mode='some-network',
            ),
            networking_config=self.client.create_networking_config({
                'some-network': self.client.create_endpoint_config(
                    aliases=['foo', 'bar'],
                ),
            }),
        )

        args = fake_request.call_args
        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "HostConfig": {
               "NetworkMode": "some-network"
             },
             "NetworkingConfig": {
               "EndpointsConfig": {
                 "some-network": {"Aliases": ["foo", "bar"]}
               }
            }}
        ''')

    @requires_api_version('1.22')
    def test_create_container_with_tmpfs_list(self):

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                tmpfs=[
                    "/tmp",
                    "/mnt:size=3G,uid=100"
                ]
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Tmpfs'] = {
            "/tmp": "",
            "/mnt": "size=3G,uid=100"
        }
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    @requires_api_version('1.22')
    def test_create_container_with_tmpfs_dict(self):

        self.client.create_container(
            'busybox', 'true', host_config=self.client.create_host_config(
                tmpfs={
                    "/tmp": "",
                    "/mnt": "size=3G,uid=100"
                }
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Tmpfs'] = {
            "/tmp": "",
            "/mnt": "size=3G,uid=100"
        }
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    @requires_api_version('1.24')
    def test_create_container_with_sysctl(self):
        self.client.create_container(
            'busybox', 'true',
            host_config=self.client.create_host_config(
                sysctls={
                    'net.core.somaxconn': 1024,
                    'net.ipv4.tcp_syncookies': '0',
                }
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        expected_payload = self.base_create_payload()
        expected_payload['HostConfig'] = self.client.create_host_config()
        expected_payload['HostConfig']['Sysctls'] = {
            'net.core.somaxconn': '1024', 'net.ipv4.tcp_syncookies': '0',
        }
        assert json.loads(args[1]['data']) == expected_payload
        assert args[1]['headers'] == {'Content-Type': 'application/json'}
        assert args[1]['timeout'] == DEFAULT_TIMEOUT_SECONDS

    def test_create_container_with_unicode_envvars(self):
        envvars_dict = {
            'foo': u'☃',
        }

        expected = [
            u'foo=☃'
        ]

        self.client.create_container(
            'busybox', 'true',
            environment=envvars_dict,
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'
        assert json.loads(args[1]['data'])['Env'] == expected

    @requires_api_version('1.25')
    def test_create_container_with_host_config_cpus(self):
        self.client.create_container(
            'busybox', 'ls', host_config=self.client.create_host_config(
                cpu_count=1,
                cpu_percent=20,
                nano_cpus=1000
            )
        )

        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/create'

        assert json.loads(args[1]['data']) == json.loads('''
            {"Tty": false, "Image": "busybox",
             "Cmd": ["ls"], "AttachStdin": false,
             "AttachStderr": true,
             "AttachStdout": true, "OpenStdin": false,
             "StdinOnce": false,
             "NetworkDisabled": false,
             "HostConfig": {
                "CpuCount": 1,
                "CpuPercent": 20,
                "NanoCpus": 1000,
                "NetworkMode": "default"
            }}
        ''')
        assert args[1]['headers'] == {'Content-Type': 'application/json'}


class ContainerTest(BaseAPIClientTest):
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
            timeout=None,
            params={}
        )

    def test_wait_with_dict_instead_of_id(self):
        self.client.wait({'Id': fake_api.FAKE_CONTAINER_ID})

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'containers/3cc2351ab11b/wait',
            timeout=None,
            params={}
        )

    def test_logs(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
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

        assert logs == 'Flowering Nights\n(Sakuya Iyazoi)\n'.encode('ascii')

    def test_logs_with_dict_instead_of_id(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
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

        assert logs == 'Flowering Nights\n(Sakuya Iyazoi)\n'.encode('ascii')

    def test_log_streaming(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=True,
                             follow=False)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=True
        )

    def test_log_following(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             follow=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 1, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_log_following_backwards(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
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

    def test_log_streaming_and_following(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=True,
                             follow=True)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 1, 'stderr': 1, 'stdout': 1,
                    'tail': 'all'},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=True
        )

    def test_log_tail(self):

        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             follow=False, tail=10)

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
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             follow=False, since=ts)

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
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                             follow=False, since=time)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'containers/3cc2351ab11b/logs',
            params={'timestamps': 0, 'follow': 0, 'stderr': 1, 'stdout': 1,
                    'tail': 'all', 'since': ts},
            timeout=DEFAULT_TIMEOUT_SECONDS,
            stream=False
        )

    def test_log_since_with_invalid_value_raises_error(self):
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container):
            with pytest.raises(docker.errors.InvalidArgument):
                self.client.logs(fake_api.FAKE_CONTAINER_ID, stream=False,
                                 follow=False, since=42.42)

    def test_log_tty(self):
        m = mock.Mock()
        with mock.patch('docker.api.client.APIClient.inspect_container',
                        fake_inspect_container_tty):
            with mock.patch('docker.api.client.APIClient._stream_raw_result',
                            m):
                self.client.logs(fake_api.FAKE_CONTAINER_ID,
                                 follow=True, stream=True)

        assert m.called
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

            assert excinfo.value.args[0] == 'Resource ID was not provided'

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

    @requires_api_version('1.22')
    def test_container_update(self):
        self.client.update_container(
            fake_api.FAKE_CONTAINER_ID, mem_limit='2k', cpu_shares=124,
            blkio_weight=345
        )
        args = fake_request.call_args
        assert args[0][1] == url_prefix + 'containers/3cc2351ab11b/update'
        assert json.loads(args[1]['data']) == {
            'Memory': 2 * 1024, 'CpuShares': 124, 'BlkioWeight': 345
        }
        assert args[1]['headers']['Content-Type'] == 'application/json'
