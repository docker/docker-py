import os
import re
import signal
import tempfile
from datetime import datetime

import docker
from docker.constants import IS_WINDOWS_PLATFORM
from docker.utils.socket import next_frame_size
from docker.utils.socket import read_exactly

import pytest

import requests
import six

from .base import BUSYBOX, BaseAPIIntegrationTest
from .. import helpers
from ..helpers import (
    requires_api_version, ctrl_with, assert_cat_socket_detached_with_keys
)


class ListContainersTest(BaseAPIIntegrationTest):
    def test_list_containers(self):
        res0 = self.client.containers(all=True)
        size = len(res0)
        res1 = self.client.create_container(BUSYBOX, 'true')
        assert 'Id' in res1
        self.client.start(res1['Id'])
        self.tmp_containers.append(res1['Id'])
        res2 = self.client.containers(all=True)
        assert size + 1 == len(res2)
        retrieved = [x for x in res2 if x['Id'].startswith(res1['Id'])]
        assert len(retrieved) == 1
        retrieved = retrieved[0]
        assert 'Command' in retrieved
        assert retrieved['Command'] == six.text_type('true')
        assert 'Image' in retrieved
        assert re.search(r'busybox:.*', retrieved['Image'])
        assert 'Status' in retrieved


class CreateContainerTest(BaseAPIIntegrationTest):

    def test_create(self):
        res = self.client.create_container(BUSYBOX, 'true')
        assert 'Id' in res
        self.tmp_containers.append(res['Id'])

    def test_create_with_host_pid_mode(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true', host_config=self.client.create_host_config(
                pid_mode='host', network_mode='none'
            )
        )
        assert 'Id' in ctnr
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)
        assert 'HostConfig' in inspect
        host_config = inspect['HostConfig']
        assert 'PidMode' in host_config
        assert host_config['PidMode'] == 'host'

    def test_create_with_links(self):
        res0 = self.client.create_container(
            BUSYBOX, 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)

        self.client.start(container1_id)

        res1 = self.client.create_container(
            BUSYBOX, 'cat',
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
            BUSYBOX, 'env', host_config=self.client.create_host_config(
                links={link_path1: link_alias1, link_path2: link_alias2},
                network_mode='bridge'
            )
        )
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)
        assert self.client.wait(container3_id)['StatusCode'] == 0

        logs = self.client.logs(container3_id)
        if six.PY3:
            logs = logs.decode('utf-8')
        assert '{0}_NAME='.format(link_env_prefix1) in logs
        assert '{0}_ENV_FOO=1'.format(link_env_prefix1) in logs
        assert '{0}_NAME='.format(link_env_prefix2) in logs
        assert '{0}_ENV_FOO=1'.format(link_env_prefix2) in logs

    def test_create_with_restart_policy(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '2'],
            host_config=self.client.create_host_config(
                restart_policy={"Name": "always", "MaximumRetryCount": 0},
                network_mode='none'
            )
        )
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        with pytest.raises(docker.errors.APIError) as exc:
            self.client.remove_container(id)
        err = exc.value.explanation
        assert 'You cannot remove ' in err
        self.client.remove_container(id, force=True)

    def test_create_container_with_volumes_from(self):
        vol_names = ['foobar_vol0', 'foobar_vol1']

        res0 = self.client.create_container(
            BUSYBOX, 'true', name=vol_names[0]
        )
        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        res1 = self.client.create_container(
            BUSYBOX, 'true', name=vol_names[1]
        )
        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id)

        res = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True,
            host_config=self.client.create_host_config(
                volumes_from=vol_names, network_mode='none'
            )
        )
        container3_id = res['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)

        info = self.client.inspect_container(res['Id'])
        assert len(info['HostConfig']['VolumesFrom']) == len(vol_names)

    def create_container_readonly_fs(self):
        ctnr = self.client.create_container(
            BUSYBOX, ['mkdir', '/shrine'],
            host_config=self.client.create_host_config(
                read_only=True, network_mode='none'
            )
        )
        assert 'Id' in ctnr
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        res = self.client.wait(ctnr)['StatusCode']
        assert res != 0

    def create_container_with_name(self):
        res = self.client.create_container(BUSYBOX, 'true', name='foobar')
        assert 'Id' in res
        self.tmp_containers.append(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        assert 'Name' in inspect
        assert '/foobar' == inspect['Name']

    def create_container_privileged(self):
        res = self.client.create_container(
            BUSYBOX, 'true', host_config=self.client.create_host_config(
                privileged=True, network_mode='none'
            )
        )
        assert 'Id' in res
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        assert 'Config' in inspect
        assert 'Id' in inspect
        assert inspect['Id'].startswith(res['Id'])
        assert 'Image' in inspect
        assert 'State' in inspect
        assert 'Running' in inspect['State']
        if not inspect['State']['Running']:
            assert 'ExitCode' in inspect['State']
            assert inspect['State']['ExitCode'] == 0
        # Since Nov 2013, the Privileged flag is no longer part of the
        # container's config exposed via the API (safety concerns?).
        #
        if 'Privileged' in inspect['Config']:
            assert inspect['Config']['Privileged'] is True

    def test_create_with_mac_address(self):
        mac_address_expected = "02:42:ac:11:00:0a"
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'], mac_address=mac_address_expected)

        id = container['Id']

        self.client.start(container)
        res = self.client.inspect_container(container['Id'])
        assert mac_address_expected == res['NetworkSettings']['MacAddress']

        self.client.kill(id)

    def test_group_id_ints(self):
        container = self.client.create_container(
            BUSYBOX, 'id -G',
            host_config=self.client.create_host_config(group_add=[1000, 1001])
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.wait(container)

        logs = self.client.logs(container)
        if six.PY3:
            logs = logs.decode('utf-8')
        groups = logs.strip().split(' ')
        assert '1000' in groups
        assert '1001' in groups

    def test_group_id_strings(self):
        container = self.client.create_container(
            BUSYBOX, 'id -G', host_config=self.client.create_host_config(
                group_add=['1000', '1001']
            )
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.wait(container)

        logs = self.client.logs(container)
        if six.PY3:
            logs = logs.decode('utf-8')

        groups = logs.strip().split(' ')
        assert '1000' in groups
        assert '1001' in groups

    def test_valid_log_driver_and_log_opt(self):
        log_config = docker.types.LogConfig(
            type='json-file',
            config={'max-file': '100'}
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )
        self.tmp_containers.append(container['Id'])
        self.client.start(container)

        info = self.client.inspect_container(container)
        container_log_config = info['HostConfig']['LogConfig']

        assert container_log_config['Type'] == log_config.type
        assert container_log_config['Config'] == log_config.config

    def test_invalid_log_driver_raises_exception(self):
        log_config = docker.types.LogConfig(
            type='asdf-nope',
            config={}
        )

        expected_msg = "logger: no log driver named 'asdf-nope' is registered"
        with pytest.raises(docker.errors.APIError) as excinfo:
            # raises an internal server error 500
            container = self.client.create_container(
                BUSYBOX, ['true'], host_config=self.client.create_host_config(
                    log_config=log_config
                )
            )
            self.client.start(container)

        assert excinfo.value.explanation == expected_msg

    def test_valid_no_log_driver_specified(self):
        log_config = docker.types.LogConfig(
            type="",
            config={'max-file': '100'}
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )
        self.tmp_containers.append(container['Id'])
        self.client.start(container)

        info = self.client.inspect_container(container)
        container_log_config = info['HostConfig']['LogConfig']

        assert container_log_config['Type'] == "json-file"
        assert container_log_config['Config'] == log_config.config

    def test_valid_no_config_specified(self):
        log_config = docker.types.LogConfig(
            type="json-file",
            config=None
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )
        self.tmp_containers.append(container['Id'])
        self.client.start(container)

        info = self.client.inspect_container(container)
        container_log_config = info['HostConfig']['LogConfig']

        assert container_log_config['Type'] == "json-file"
        assert container_log_config['Config'] == {}

    def test_create_with_memory_constraints_with_str(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true',
            host_config=self.client.create_host_config(
                memswap_limit='1G',
                mem_limit='700M'
            )
        )
        assert 'Id' in ctnr
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)

        assert 'HostConfig' in inspect
        host_config = inspect['HostConfig']
        for limit in ['Memory', 'MemorySwap']:
            assert limit in host_config

    def test_create_with_memory_constraints_with_int(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true',
            host_config=self.client.create_host_config(mem_swappiness=40)
        )
        assert 'Id' in ctnr
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)

        assert 'HostConfig' in inspect
        host_config = inspect['HostConfig']
        assert 'MemorySwappiness' in host_config

    def test_create_with_environment_variable_no_value(self):
        container = self.client.create_container(
            BUSYBOX,
            ['echo'],
            environment={'Foo': None, 'Other': 'one', 'Blank': ''},
        )
        self.tmp_containers.append(container['Id'])
        config = self.client.inspect_container(container['Id'])
        assert (
            sorted(config['Config']['Env']) ==
            sorted(['Foo', 'Other=one', 'Blank='])
        )

    @requires_api_version('1.22')
    def test_create_with_tmpfs(self):
        tmpfs = {
            '/tmp1': 'size=3M'
        }

        container = self.client.create_container(
            BUSYBOX,
            ['echo'],
            host_config=self.client.create_host_config(
                tmpfs=tmpfs))

        self.tmp_containers.append(container['Id'])
        config = self.client.inspect_container(container)
        assert config['HostConfig']['Tmpfs'] == tmpfs

    @requires_api_version('1.24')
    def test_create_with_isolation(self):
        container = self.client.create_container(
            BUSYBOX, ['echo'], host_config=self.client.create_host_config(
                isolation='default'
            )
        )
        self.tmp_containers.append(container['Id'])
        config = self.client.inspect_container(container)
        assert config['HostConfig']['Isolation'] == 'default'

    @requires_api_version('1.25')
    def test_create_with_auto_remove(self):
        host_config = self.client.create_host_config(
            auto_remove=True
        )
        container = self.client.create_container(
            BUSYBOX, ['echo', 'test'], host_config=host_config
        )
        self.tmp_containers.append(container['Id'])
        config = self.client.inspect_container(container)
        assert config['HostConfig']['AutoRemove'] is True

    @requires_api_version('1.25')
    def test_create_with_stop_timeout(self):
        container = self.client.create_container(
            BUSYBOX, ['echo', 'test'], stop_timeout=25
        )
        self.tmp_containers.append(container['Id'])
        config = self.client.inspect_container(container)
        assert config['Config']['StopTimeout'] == 25

    @requires_api_version('1.24')
    @pytest.mark.xfail(True, reason='Not supported on most drivers')
    def test_create_with_storage_opt(self):
        host_config = self.client.create_host_config(
            storage_opt={'size': '120G'}
        )
        container = self.client.create_container(
            BUSYBOX, ['echo', 'test'], host_config=host_config
        )
        self.tmp_containers.append(container)
        config = self.client.inspect_container(container)
        assert config['HostConfig']['StorageOpt'] == {
            'size': '120G'
        }

    @requires_api_version('1.25')
    def test_create_with_init(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true',
            host_config=self.client.create_host_config(
                init=True
            )
        )
        self.tmp_containers.append(ctnr['Id'])
        config = self.client.inspect_container(ctnr)
        assert config['HostConfig']['Init'] is True

    @pytest.mark.xfail(True, reason='init-path removed in 17.05.0')
    @requires_api_version('1.25')
    def test_create_with_init_path(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true',
            host_config=self.client.create_host_config(
                init_path="/usr/libexec/docker-init"
            )
        )
        self.tmp_containers.append(ctnr['Id'])
        config = self.client.inspect_container(ctnr)
        assert config['HostConfig']['InitPath'] == "/usr/libexec/docker-init"

    @requires_api_version('1.24')
    @pytest.mark.xfail(not os.path.exists('/sys/fs/cgroup/cpu.rt_runtime_us'),
                       reason='CONFIG_RT_GROUP_SCHED isn\'t enabled')
    def test_create_with_cpu_rt_options(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true', host_config=self.client.create_host_config(
                cpu_rt_period=1000, cpu_rt_runtime=500
            )
        )
        self.tmp_containers.append(ctnr)
        config = self.client.inspect_container(ctnr)
        assert config['HostConfig']['CpuRealtimeRuntime'] == 500
        assert config['HostConfig']['CpuRealtimePeriod'] == 1000

    @requires_api_version('1.28')
    def test_create_with_device_cgroup_rules(self):
        rule = 'c 7:128 rwm'
        ctnr = self.client.create_container(
            BUSYBOX, 'cat /sys/fs/cgroup/devices/devices.list',
            host_config=self.client.create_host_config(
                device_cgroup_rules=[rule]
            )
        )
        self.tmp_containers.append(ctnr)
        config = self.client.inspect_container(ctnr)
        assert config['HostConfig']['DeviceCgroupRules'] == [rule]
        self.client.start(ctnr)
        assert rule in self.client.logs(ctnr).decode('utf-8')


class VolumeBindTest(BaseAPIIntegrationTest):
    def setUp(self):
        super(VolumeBindTest, self).setUp()

        self.mount_dest = '/mnt'

        # Get a random pathname - we don't need it to exist locally
        self.mount_origin = tempfile.mkdtemp()
        self.filename = 'shared.txt'

        self.run_with_volume(
            False,
            BUSYBOX,
            ['touch', os.path.join(self.mount_dest, self.filename)],
        )

    @pytest.mark.xfail(
        IS_WINDOWS_PLATFORM, reason='Test not designed for Windows platform'
    )
    def test_create_with_binds_rw(self):

        container = self.run_with_volume(
            False,
            BUSYBOX,
            ['ls', self.mount_dest],
        )
        logs = self.client.logs(container)

        if six.PY3:
            logs = logs.decode('utf-8')
        assert self.filename in logs
        inspect_data = self.client.inspect_container(container)
        self.check_container_data(inspect_data, True)

    @pytest.mark.xfail(
        IS_WINDOWS_PLATFORM, reason='Test not designed for Windows platform'
    )
    def test_create_with_binds_ro(self):
        self.run_with_volume(
            False,
            BUSYBOX,
            ['touch', os.path.join(self.mount_dest, self.filename)],
        )
        container = self.run_with_volume(
            True,
            BUSYBOX,
            ['ls', self.mount_dest],
        )
        logs = self.client.logs(container)

        if six.PY3:
            logs = logs.decode('utf-8')
        assert self.filename in logs

        inspect_data = self.client.inspect_container(container)
        self.check_container_data(inspect_data, False)

    @pytest.mark.xfail(
        IS_WINDOWS_PLATFORM, reason='Test not designed for Windows platform'
    )
    @requires_api_version('1.30')
    def test_create_with_mounts(self):
        mount = docker.types.Mount(
            type="bind", source=self.mount_origin, target=self.mount_dest
        )
        host_config = self.client.create_host_config(mounts=[mount])
        container = self.run_container(
            BUSYBOX, ['ls', self.mount_dest],
            host_config=host_config
        )
        assert container
        logs = self.client.logs(container)
        if six.PY3:
            logs = logs.decode('utf-8')
        assert self.filename in logs
        inspect_data = self.client.inspect_container(container)
        self.check_container_data(inspect_data, True)

    @pytest.mark.xfail(
        IS_WINDOWS_PLATFORM, reason='Test not designed for Windows platform'
    )
    @requires_api_version('1.30')
    def test_create_with_mounts_ro(self):
        mount = docker.types.Mount(
            type="bind", source=self.mount_origin, target=self.mount_dest,
            read_only=True
        )
        host_config = self.client.create_host_config(mounts=[mount])
        container = self.run_container(
            BUSYBOX, ['ls', self.mount_dest],
            host_config=host_config
        )
        assert container
        logs = self.client.logs(container)
        if six.PY3:
            logs = logs.decode('utf-8')
        assert self.filename in logs
        inspect_data = self.client.inspect_container(container)
        self.check_container_data(inspect_data, False)

    @requires_api_version('1.30')
    def test_create_with_volume_mount(self):
        mount = docker.types.Mount(
            type="volume", source=helpers.random_name(),
            target=self.mount_dest, labels={'com.dockerpy.test': 'true'}
        )
        host_config = self.client.create_host_config(mounts=[mount])
        container = self.client.create_container(
            BUSYBOX, ['true'], host_config=host_config,
        )
        assert container
        inspect_data = self.client.inspect_container(container)
        assert 'Mounts' in inspect_data
        filtered = list(filter(
            lambda x: x['Destination'] == self.mount_dest,
            inspect_data['Mounts']
        ))
        assert len(filtered) == 1
        mount_data = filtered[0]
        assert mount['Source'] == mount_data['Name']
        assert mount_data['RW'] is True

    def check_container_data(self, inspect_data, rw):
        assert 'Mounts' in inspect_data
        filtered = list(filter(
            lambda x: x['Destination'] == self.mount_dest,
            inspect_data['Mounts']
        ))
        assert len(filtered) == 1
        mount_data = filtered[0]
        assert mount_data['Source'] == self.mount_origin
        assert mount_data['RW'] == rw

    def run_with_volume(self, ro, *args, **kwargs):
        return self.run_container(
            *args,
            volumes={self.mount_dest: {}},
            host_config=self.client.create_host_config(
                binds={
                    self.mount_origin: {
                        'bind': self.mount_dest,
                        'ro': ro,
                    },
                },
                network_mode='none'
            ),
            **kwargs
        )


class ArchiveTest(BaseAPIIntegrationTest):
    def test_get_file_archive_from_container(self):
        data = 'The Maid and the Pocket Watch of Blood'
        ctnr = self.client.create_container(
            BUSYBOX, 'sh -c "echo {0} > /vol1/data.txt"'.format(data),
            volumes=['/vol1']
        )
        self.tmp_containers.append(ctnr)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        with tempfile.NamedTemporaryFile() as destination:
            strm, stat = self.client.get_archive(ctnr, '/vol1/data.txt')
            for d in strm:
                destination.write(d)
            destination.seek(0)
            retrieved_data = helpers.untar_file(destination, 'data.txt')
            if six.PY3:
                retrieved_data = retrieved_data.decode('utf-8')
            assert data == retrieved_data.strip()

    def test_get_file_stat_from_container(self):
        data = 'The Maid and the Pocket Watch of Blood'
        ctnr = self.client.create_container(
            BUSYBOX, 'sh -c "echo -n {0} > /vol1/data.txt"'.format(data),
            volumes=['/vol1']
        )
        self.tmp_containers.append(ctnr)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        strm, stat = self.client.get_archive(ctnr, '/vol1/data.txt')
        assert 'name' in stat
        assert stat['name'] == 'data.txt'
        assert 'size' in stat
        assert stat['size'] == len(data)

    def test_copy_file_to_container(self):
        data = b'Deaf To All But The Song'
        with tempfile.NamedTemporaryFile(delete=False) as test_file:
            test_file.write(data)
            test_file.seek(0)
            ctnr = self.client.create_container(
                BUSYBOX,
                'cat {0}'.format(
                    os.path.join('/vol1/', os.path.basename(test_file.name))
                ),
                volumes=['/vol1']
            )
            self.tmp_containers.append(ctnr)
            with helpers.simple_tar(test_file.name) as test_tar:
                self.client.put_archive(ctnr, '/vol1', test_tar)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        logs = self.client.logs(ctnr)
        if six.PY3:
            logs = logs.decode('utf-8')
            data = data.decode('utf-8')
        assert logs.strip() == data

    def test_copy_directory_to_container(self):
        files = ['a.py', 'b.py', 'foo/b.py']
        dirs = ['foo', 'bar']
        base = helpers.make_tree(dirs, files)
        ctnr = self.client.create_container(
            BUSYBOX, 'ls -p /vol1', volumes=['/vol1']
        )
        self.tmp_containers.append(ctnr)
        with docker.utils.tar(base) as test_tar:
            self.client.put_archive(ctnr, '/vol1', test_tar)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        logs = self.client.logs(ctnr)
        if six.PY3:
            logs = logs.decode('utf-8')
        results = logs.strip().split()
        assert 'a.py' in results
        assert 'b.py' in results
        assert 'foo/' in results
        assert 'bar/' in results


class RenameContainerTest(BaseAPIIntegrationTest):
    def test_rename_container(self):
        version = self.client.version()['Version']
        name = 'hong_meiling'
        res = self.client.create_container(BUSYBOX, 'true')
        assert 'Id' in res
        self.tmp_containers.append(res['Id'])
        self.client.rename(res, name)
        inspect = self.client.inspect_container(res['Id'])
        assert 'Name' in inspect
        if version == '1.5.0':
            assert name == inspect['Name']
        else:
            assert '/{0}'.format(name) == inspect['Name']


class StartContainerTest(BaseAPIIntegrationTest):
    def test_start_container(self):
        res = self.client.create_container(BUSYBOX, 'true')
        assert 'Id' in res
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        assert 'Config' in inspect
        assert 'Id' in inspect
        assert inspect['Id'].startswith(res['Id'])
        assert 'Image' in inspect
        assert 'State' in inspect
        assert 'Running' in inspect['State']
        if not inspect['State']['Running']:
            assert 'ExitCode' in inspect['State']
            assert inspect['State']['ExitCode'] == 0

    def test_start_container_with_dict_instead_of_id(self):
        res = self.client.create_container(BUSYBOX, 'true')
        assert 'Id' in res
        self.tmp_containers.append(res['Id'])
        self.client.start(res)
        inspect = self.client.inspect_container(res['Id'])
        assert 'Config' in inspect
        assert 'Id' in inspect
        assert inspect['Id'].startswith(res['Id'])
        assert 'Image' in inspect
        assert 'State' in inspect
        assert 'Running' in inspect['State']
        if not inspect['State']['Running']:
            assert 'ExitCode' in inspect['State']
            assert inspect['State']['ExitCode'] == 0

    def test_run_shlex_commands(self):
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
            container = self.client.create_container(BUSYBOX, cmd)
            id = container['Id']
            self.client.start(id)
            self.tmp_containers.append(id)
            exitcode = self.client.wait(id)['StatusCode']
            assert exitcode == 0, cmd


class WaitTest(BaseAPIIntegrationTest):
    def test_wait(self):
        res = self.client.create_container(BUSYBOX, ['sleep', '3'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        inspect = self.client.inspect_container(id)
        assert 'Running' in inspect['State']
        assert inspect['State']['Running'] is False
        assert 'ExitCode' in inspect['State']
        assert inspect['State']['ExitCode'] == exitcode

    def test_wait_with_dict_instead_of_id(self):
        res = self.client.create_container(BUSYBOX, ['sleep', '3'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(res)
        exitcode = self.client.wait(res)['StatusCode']
        assert exitcode == 0
        inspect = self.client.inspect_container(res)
        assert 'Running' in inspect['State']
        assert inspect['State']['Running'] is False
        assert 'ExitCode' in inspect['State']
        assert inspect['State']['ExitCode'] == exitcode

    @requires_api_version('1.30')
    def test_wait_with_condition(self):
        ctnr = self.client.create_container(BUSYBOX, 'true')
        self.tmp_containers.append(ctnr)
        with pytest.raises(requests.exceptions.ConnectionError):
            self.client.wait(ctnr, condition='removed', timeout=1)

        ctnr = self.client.create_container(
            BUSYBOX, ['sleep', '3'],
            host_config=self.client.create_host_config(auto_remove=True)
        )
        self.tmp_containers.append(ctnr)
        self.client.start(ctnr)
        assert self.client.wait(
            ctnr, condition='removed', timeout=5
        )['StatusCode'] == 0


class LogsTest(BaseAPIIntegrationTest):
    def test_logs(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        logs = self.client.logs(id)
        assert logs == (snippet + '\n').encode(encoding='ascii')

    def test_logs_tail_option(self):
        snippet = '''Line1
Line2'''
        container = self.client.create_container(
            BUSYBOX, 'echo "{0}"'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        logs = self.client.logs(id, tail=1)
        assert logs == 'Line2\n'.encode(encoding='ascii')

    def test_logs_streaming_and_follow(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        logs = six.binary_type()
        for chunk in self.client.logs(id, stream=True, follow=True):
            logs += chunk

        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0

        assert logs == (snippet + '\n').encode(encoding='ascii')

    def test_logs_with_dict_instead_of_id(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        logs = self.client.logs(container)
        assert logs == (snippet + '\n').encode(encoding='ascii')

    def test_logs_with_tail_0(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo "{0}"'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        logs = self.client.logs(id, tail=0)
        assert logs == ''.encode(encoding='ascii')

    @requires_api_version('1.35')
    def test_logs_with_until(self):
        snippet = 'Shanghai Teahouse (Hong Meiling)'
        container = self.client.create_container(
            BUSYBOX, 'echo "{0}"'.format(snippet)
        )

        self.tmp_containers.append(container)
        self.client.start(container)
        exitcode = self.client.wait(container)['StatusCode']
        assert exitcode == 0
        logs_until_1 = self.client.logs(container, until=1)
        assert logs_until_1 == b''
        logs_until_now = self.client.logs(container, datetime.now())
        assert logs_until_now == (snippet + '\n').encode(encoding='ascii')


class DiffTest(BaseAPIIntegrationTest):
    def test_diff(self):
        container = self.client.create_container(BUSYBOX, ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        diff = self.client.diff(id)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        assert len(test_diff) == 1
        assert 'Kind' in test_diff[0]
        assert test_diff[0]['Kind'] == 1

    def test_diff_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode == 0
        diff = self.client.diff(container)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        assert len(test_diff) == 1
        assert 'Kind' in test_diff[0]
        assert test_diff[0]['Kind'] == 1


class StopTest(BaseAPIIntegrationTest):
    def test_stop(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.stop(id, timeout=2)
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'Running' in state
        assert state['Running'] is False

    def test_stop_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        assert 'Id' in container
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        self.client.stop(container, timeout=2)
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'Running' in state
        assert state['Running'] is False


class KillTest(BaseAPIIntegrationTest):
    def test_kill(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id)
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] != 0
        assert 'Running' in state
        assert state['Running'] is False

    def test_kill_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(container)
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] != 0
        assert 'Running' in state
        assert state['Running'] is False

    def test_kill_with_signal(self):
        id = self.client.create_container(BUSYBOX, ['sleep', '60'])
        self.tmp_containers.append(id)
        self.client.start(id)
        self.client.kill(
            id, signal=signal.SIGKILL if not IS_WINDOWS_PLATFORM else 9
        )
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode != 0
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] != 0
        assert 'Running' in state
        assert state['Running'] is False, state

    def test_kill_with_signal_name(self):
        id = self.client.create_container(BUSYBOX, ['sleep', '60'])
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id, signal='SIGKILL')
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode != 0
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] != 0
        assert 'Running' in state
        assert state['Running'] is False, state

    def test_kill_with_signal_integer(self):
        id = self.client.create_container(BUSYBOX, ['sleep', '60'])
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id, signal=9)
        exitcode = self.client.wait(id)['StatusCode']
        assert exitcode != 0
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] != 0
        assert 'Running' in state
        assert state['Running'] is False, state


class PortTest(BaseAPIIntegrationTest):
    def test_port(self):

        port_bindings = {
            '1111': ('127.0.0.1', '4567'),
            '2222': ('127.0.0.1', '4568')
        }

        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'], ports=list(port_bindings.keys()),
            host_config=self.client.create_host_config(
                port_bindings=port_bindings, network_mode='bridge'
            )
        )
        id = container['Id']

        self.client.start(container)

        # Call the port function on each biding and compare expected vs actual
        for port in port_bindings:
            actual_bindings = self.client.port(container, port)
            port_binding = actual_bindings.pop()

            ip, host_port = port_binding['HostIp'], port_binding['HostPort']

            assert ip == port_bindings[port][0]
            assert host_port == port_bindings[port][1]

        self.client.kill(id)


class ContainerTopTest(BaseAPIIntegrationTest):
    def test_top(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60']
        )

        self.tmp_containers.append(container)

        self.client.start(container)
        res = self.client.top(container)
        if IS_WINDOWS_PLATFORM:
            assert res['Titles'] == ['PID', 'USER', 'TIME', 'COMMAND']
        else:
            assert res['Titles'] == [
                'UID', 'PID', 'PPID', 'C', 'STIME', 'TTY', 'TIME', 'CMD'
            ]
        assert len(res['Processes']) == 1
        assert res['Processes'][0][-1] == 'sleep 60'
        self.client.kill(container)

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='No psargs support on windows'
    )
    def test_top_with_psargs(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'])

        self.tmp_containers.append(container)

        self.client.start(container)
        res = self.client.top(container, 'waux')
        assert res['Titles'] == [
            'USER', 'PID', '%CPU', '%MEM', 'VSZ', 'RSS',
            'TTY', 'STAT', 'START', 'TIME', 'COMMAND'
        ]
        assert len(res['Processes']) == 1
        assert res['Processes'][0][10] == 'sleep 60'


class RestartContainerTest(BaseAPIIntegrationTest):
    def test_restart(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        assert 'State' in info
        assert 'StartedAt' in info['State']
        start_time1 = info['State']['StartedAt']
        self.client.restart(id, timeout=2)
        info2 = self.client.inspect_container(id)
        assert 'State' in info2
        assert 'StartedAt' in info2['State']
        start_time2 = info2['State']['StartedAt']
        assert start_time1 != start_time2
        assert 'Running' in info2['State']
        assert info2['State']['Running'] is True
        self.client.kill(id)

    def test_restart_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        assert 'Id' in container
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        assert 'State' in info
        assert 'StartedAt' in info['State']
        start_time1 = info['State']['StartedAt']
        self.client.restart(container, timeout=2)
        info2 = self.client.inspect_container(id)
        assert 'State' in info2
        assert 'StartedAt' in info2['State']
        start_time2 = info2['State']['StartedAt']
        assert start_time1 != start_time2
        assert 'Running' in info2['State']
        assert info2['State']['Running'] is True
        self.client.kill(id)


class RemoveContainerTest(BaseAPIIntegrationTest):
    def test_remove(self):
        container = self.client.create_container(BUSYBOX, ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(id)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        assert len(res) == 0

    def test_remove_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(container)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        assert len(res) == 0


class AttachContainerTest(BaseAPIIntegrationTest):
    def test_run_container_streaming(self):
        container = self.client.create_container(BUSYBOX, '/bin/sh',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        sock = self.client.attach_socket(container, ws=False)
        assert sock.fileno() > -1

    def test_run_container_reading_socket(self):
        line = 'hi there and stuff and things, words!'
        # `echo` appends CRLF, `printf` doesn't
        command = "printf '{0}'".format(line)
        container = self.client.create_container(BUSYBOX, command,
                                                 detach=True, tty=False)
        self.tmp_containers.append(container)

        opts = {"stdout": 1, "stream": 1, "logs": 1}
        pty_stdout = self.client.attach_socket(container, opts)
        self.addCleanup(pty_stdout.close)

        self.client.start(container)

        next_size = next_frame_size(pty_stdout)
        assert next_size == len(line)
        data = read_exactly(pty_stdout, next_size)
        assert data.decode('utf-8') == line

    def test_attach_no_stream(self):
        container = self.client.create_container(
            BUSYBOX, 'echo hello'
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        output = self.client.attach(container, stream=False, logs=True)
        assert output == 'hello\n'.encode(encoding='ascii')

    def test_detach_with_default(self):
        container = self.client.create_container(
            BUSYBOX, 'cat',
            detach=True, stdin_open=True, tty=True
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        sock = self.client.attach_socket(
            container,
            {'stdin': True, 'stream': True}
        )

        assert_cat_socket_detached_with_keys(
            sock, [ctrl_with('p'), ctrl_with('q')]
        )

    def test_detach_with_config_file(self):
        self.client._general_configs['detachKeys'] = 'ctrl-p'

        container = self.client.create_container(
            BUSYBOX, 'cat',
            detach=True, stdin_open=True, tty=True
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        sock = self.client.attach_socket(
            container,
            {'stdin': True, 'stream': True}
        )

        assert_cat_socket_detached_with_keys(sock, [ctrl_with('p')])

    def test_detach_with_arg(self):
        self.client._general_configs['detachKeys'] = 'ctrl-p'

        container = self.client.create_container(
            BUSYBOX, 'cat',
            detach=True, stdin_open=True, tty=True
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        sock = self.client.attach_socket(
            container,
            {'stdin': True, 'stream': True, 'detachKeys': 'ctrl-x'}
        )

        assert_cat_socket_detached_with_keys(sock, [ctrl_with('x')])


class PauseTest(BaseAPIIntegrationTest):
    def test_pause_unpause(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(container)
        self.client.pause(id)
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] == 0
        assert 'Running' in state
        assert state['Running'] is True
        assert 'Paused' in state
        assert state['Paused'] is True

        self.client.unpause(id)
        container_info = self.client.inspect_container(id)
        assert 'State' in container_info
        state = container_info['State']
        assert 'ExitCode' in state
        assert state['ExitCode'] == 0
        assert 'Running' in state
        assert state['Running'] is True
        assert 'Paused' in state
        assert state['Paused'] is False


class PruneTest(BaseAPIIntegrationTest):
    @requires_api_version('1.25')
    def test_prune_containers(self):
        container1 = self.client.create_container(
            BUSYBOX, ['sh', '-c', 'echo hello > /data.txt']
        )
        container2 = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        self.client.start(container1)
        self.client.start(container2)
        self.client.wait(container1)
        result = self.client.prune_containers()
        assert container1['Id'] in result['ContainersDeleted']
        assert result['SpaceReclaimed'] > 0
        assert container2['Id'] not in result['ContainersDeleted']


class GetContainerStatsTest(BaseAPIIntegrationTest):
    def test_get_container_stats_no_stream(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'],
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        response = self.client.stats(container, stream=0)
        self.client.kill(container)

        assert type(response) == dict
        for key in ['read', 'networks', 'precpu_stats', 'cpu_stats',
                    'memory_stats', 'blkio_stats']:
            assert key in response

        def test_get_container_stats_stream(self):
            container = self.client.create_container(
                BUSYBOX, ['sleep', '60'],
            )
            self.tmp_containers.append(container)
            self.client.start(container)
            stream = self.client.stats(container)
            for chunk in stream:
                assert type(chunk) == dict
                for key in ['read', 'network', 'precpu_stats', 'cpu_stats',
                            'memory_stats', 'blkio_stats']:
                    assert key in chunk


class ContainerUpdateTest(BaseAPIIntegrationTest):
    @requires_api_version('1.22')
    def test_update_container(self):
        old_mem_limit = 400 * 1024 * 1024
        new_mem_limit = 300 * 1024 * 1024
        container = self.client.create_container(
            BUSYBOX, 'top', host_config=self.client.create_host_config(
                mem_limit=old_mem_limit
            )
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.update_container(container, mem_limit=new_mem_limit)
        inspect_data = self.client.inspect_container(container)
        assert inspect_data['HostConfig']['Memory'] == new_mem_limit

    @requires_api_version('1.23')
    def test_restart_policy_update(self):
        old_restart_policy = {
            'MaximumRetryCount': 0,
            'Name': 'always'
        }
        new_restart_policy = {
            'MaximumRetryCount': 42,
            'Name': 'on-failure'
        }
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'],
            host_config=self.client.create_host_config(
                restart_policy=old_restart_policy
            )
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.update_container(container,
                                     restart_policy=new_restart_policy)
        inspect_data = self.client.inspect_container(container)
        assert (
            inspect_data['HostConfig']['RestartPolicy']['MaximumRetryCount'] ==
            new_restart_policy['MaximumRetryCount']
        )
        assert (
            inspect_data['HostConfig']['RestartPolicy']['Name'] ==
            new_restart_policy['Name']
        )


class ContainerCPUTest(BaseAPIIntegrationTest):
    def test_container_cpu_shares(self):
        cpu_shares = 512
        container = self.client.create_container(
            BUSYBOX, 'ls', host_config=self.client.create_host_config(
                cpu_shares=cpu_shares
            )
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        inspect_data = self.client.inspect_container(container)
        assert inspect_data['HostConfig']['CpuShares'] == 512

    def test_container_cpuset(self):
        cpuset_cpus = "0,1"
        container = self.client.create_container(
            BUSYBOX, 'ls', host_config=self.client.create_host_config(
                cpuset_cpus=cpuset_cpus
            )
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        inspect_data = self.client.inspect_container(container)
        assert inspect_data['HostConfig']['CpusetCpus'] == cpuset_cpus

    @requires_api_version('1.25')
    def test_create_with_runtime(self):
        container = self.client.create_container(
            BUSYBOX, ['echo', 'test'], runtime='runc'
        )
        self.tmp_containers.append(container['Id'])
        config = self.client.inspect_container(container)
        assert config['HostConfig']['Runtime'] == 'runc'


class LinkTest(BaseAPIIntegrationTest):
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
        assert len(retrieved) == 0

        # Containers are still there
        retrieved = [
            x for x in containers if x['Id'].startswith(container1_id) or
            x['Id'].startswith(container2_id)
        ]
        assert len(retrieved) == 2
