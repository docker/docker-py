# -*- coding: utf-8 -*-

import unittest
import warnings

import pytest

from docker.constants import DEFAULT_DOCKER_API_VERSION
from docker.errors import InvalidArgument, InvalidVersion
from docker.types import (
    ContainerConfig, ContainerSpec, EndpointConfig, HostConfig, IPAMConfig,
    IPAMPool, LogConfig, Mount, Resources, ServiceMode, TaskTemplate, Ulimit,
)

try:
    from unittest import mock
except:
    import mock


def create_host_config(*args, **kwargs):
    return HostConfig(*args, **kwargs)


class HostConfigTest(unittest.TestCase):
    def test_create_host_config_no_options(self):
        config = create_host_config(version='1.19')
        self.assertFalse('NetworkMode' in config)

    def test_create_host_config_no_options_newer_api_version(self):
        config = create_host_config(version='1.20')
        self.assertEqual(config['NetworkMode'], 'default')

    def test_create_host_config_invalid_cpu_cfs_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.20', cpu_quota='0')

        with pytest.raises(TypeError):
            create_host_config(version='1.20', cpu_period='0')

        with pytest.raises(TypeError):
            create_host_config(version='1.20', cpu_quota=23.11)

        with pytest.raises(TypeError):
            create_host_config(version='1.20', cpu_period=1999.0)

    def test_create_host_config_with_cpu_quota(self):
        config = create_host_config(version='1.20', cpu_quota=1999)
        self.assertEqual(config.get('CpuQuota'), 1999)

    def test_create_host_config_with_cpu_period(self):
        config = create_host_config(version='1.20', cpu_period=1999)
        self.assertEqual(config.get('CpuPeriod'), 1999)

    def test_create_host_config_with_blkio_constraints(self):
        blkio_rate = [{"Path": "/dev/sda", "Rate": 1000}]
        config = create_host_config(version='1.22',
                                    blkio_weight=1999,
                                    blkio_weight_device=blkio_rate,
                                    device_read_bps=blkio_rate,
                                    device_write_bps=blkio_rate,
                                    device_read_iops=blkio_rate,
                                    device_write_iops=blkio_rate)

        self.assertEqual(config.get('BlkioWeight'), 1999)
        self.assertTrue(config.get('BlkioWeightDevice') is blkio_rate)
        self.assertTrue(config.get('BlkioDeviceReadBps') is blkio_rate)
        self.assertTrue(config.get('BlkioDeviceWriteBps') is blkio_rate)
        self.assertTrue(config.get('BlkioDeviceReadIOps') is blkio_rate)
        self.assertTrue(config.get('BlkioDeviceWriteIOps') is blkio_rate)
        self.assertEqual(blkio_rate[0]['Path'], "/dev/sda")
        self.assertEqual(blkio_rate[0]['Rate'], 1000)

    def test_create_host_config_with_shm_size(self):
        config = create_host_config(version='1.22', shm_size=67108864)
        self.assertEqual(config.get('ShmSize'), 67108864)

    def test_create_host_config_with_shm_size_in_mb(self):
        config = create_host_config(version='1.22', shm_size='64M')
        self.assertEqual(config.get('ShmSize'), 67108864)

    def test_create_host_config_with_oom_kill_disable(self):
        config = create_host_config(version='1.20', oom_kill_disable=True)
        self.assertEqual(config.get('OomKillDisable'), True)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(version='1.18.3',
                                                       oom_kill_disable=True))

    def test_create_host_config_with_userns_mode(self):
        config = create_host_config(version='1.23', userns_mode='host')
        self.assertEqual(config.get('UsernsMode'), 'host')
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(version='1.22',
                                                       userns_mode='host'))
        self.assertRaises(
            ValueError, lambda: create_host_config(version='1.23',
                                                   userns_mode='host12'))

    def test_create_host_config_with_oom_score_adj(self):
        config = create_host_config(version='1.22', oom_score_adj=100)
        self.assertEqual(config.get('OomScoreAdj'), 100)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(version='1.21',
                                                       oom_score_adj=100))
        self.assertRaises(
            TypeError, lambda: create_host_config(version='1.22',
                                                  oom_score_adj='100'))

    def test_create_host_config_with_dns_opt(self):

        tested_opts = ['use-vc', 'no-tld-query']
        config = create_host_config(version='1.21', dns_opt=tested_opts)
        dns_opts = config.get('DnsOptions')

        self.assertTrue('use-vc' in dns_opts)
        self.assertTrue('no-tld-query' in dns_opts)

        self.assertRaises(
            InvalidVersion, lambda: create_host_config(version='1.20',
                                                       dns_opt=tested_opts))

    def test_create_host_config_with_mem_reservation(self):
        config = create_host_config(version='1.21', mem_reservation=67108864)
        self.assertEqual(config.get('MemoryReservation'), 67108864)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(
                version='1.20', mem_reservation=67108864))

    def test_create_host_config_with_kernel_memory(self):
        config = create_host_config(version='1.21', kernel_memory=67108864)
        self.assertEqual(config.get('KernelMemory'), 67108864)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(
                version='1.20', kernel_memory=67108864))

    def test_create_host_config_with_pids_limit(self):
        config = create_host_config(version='1.23', pids_limit=1024)
        self.assertEqual(config.get('PidsLimit'), 1024)

        with pytest.raises(InvalidVersion):
            create_host_config(version='1.22', pids_limit=1024)
        with pytest.raises(TypeError):
            create_host_config(version='1.23', pids_limit='1024')

    def test_create_host_config_with_isolation(self):
        config = create_host_config(version='1.24', isolation='hyperv')
        self.assertEqual(config.get('Isolation'), 'hyperv')

        with pytest.raises(InvalidVersion):
            create_host_config(version='1.23', isolation='hyperv')
        with pytest.raises(TypeError):
            create_host_config(
                version='1.24', isolation={'isolation': 'hyperv'}
            )

    def test_create_host_config_pid_mode(self):
        with pytest.raises(ValueError):
            create_host_config(version='1.23', pid_mode='baccab125')

        config = create_host_config(version='1.23', pid_mode='host')
        assert config.get('PidMode') == 'host'
        config = create_host_config(version='1.24', pid_mode='baccab125')
        assert config.get('PidMode') == 'baccab125'

    def test_create_host_config_invalid_mem_swappiness(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.24', mem_swappiness='40')

    def test_create_host_config_with_volume_driver(self):
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.20', volume_driver='local')

        config = create_host_config(version='1.21', volume_driver='local')
        assert config.get('VolumeDriver') == 'local'

    def test_create_host_config_invalid_cpu_count_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', cpu_count='1')

    def test_create_host_config_with_cpu_count(self):
        config = create_host_config(version='1.25', cpu_count=2)
        self.assertEqual(config.get('CpuCount'), 2)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(
                version='1.24', cpu_count=1))

    def test_create_host_config_invalid_cpu_percent_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', cpu_percent='1')

    def test_create_host_config_with_cpu_percent(self):
        config = create_host_config(version='1.25', cpu_percent=15)
        self.assertEqual(config.get('CpuPercent'), 15)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(
                version='1.24', cpu_percent=10))

    def test_create_host_config_invalid_nano_cpus_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', nano_cpus='0')

    def test_create_host_config_with_nano_cpus(self):
        config = create_host_config(version='1.25', nano_cpus=1000)
        self.assertEqual(config.get('NanoCpus'), 1000)
        self.assertRaises(
            InvalidVersion, lambda: create_host_config(
                version='1.24', nano_cpus=1))


class ContainerConfigTest(unittest.TestCase):
    def test_create_container_config_volume_driver_warning(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter('always')
            ContainerConfig(
                version='1.21', image='scratch', command=None,
                volume_driver='local'
            )

        assert len(w) == 1
        assert 'The volume_driver option has been moved' in str(w[0].message)


class TaskTemplateTest(unittest.TestCase):
    def test_simple(self):
        spec = ContainerSpec(
            image='alpine', command='sleep 30'
        )
        task_template = TaskTemplate(
            container_spec=spec, resources=Resources(
                mem_limit=123, mem_reservation=45
            )
        )

        assert 'ContainerSpec' in task_template
        container_spec = task_template['ContainerSpec']
        assert container_spec['Image'] == 'alpine'
        assert container_spec['Command'] == ['sleep', '30']
        assert 'Resources' in task_template
        resources = task_template['Resources']
        assert resources['Limits']['MemoryBytes'] == 123
        assert resources['Reservations']['MemoryBytes'] == 45

    def test_from_spec(self):
        task_template = TaskTemplate.from_spec({
            'ContainerSpec': {
                'Image': 'alpine',
                'Command': ['sleep', '30']
            },
            'Resources': {
                'Limits': {
                    'MemoryBytes': 123
                },
                'Reservations': {
                    'MemoryBytes': 45
                }
            },
            'RestartPolicy': {
                'Condition': 'any',
                'Delay': 5678,
                'MaxAttempts': 9
            },
            'LogDriver': {
                'Name': 'json'
            },
            'ForceUpdate': 42
        })

        assert type(task_template) == TaskTemplate
        assert type(task_template.container_spec) == ContainerSpec
        assert task_template.container_spec.image == 'alpine'
        assert task_template.container_spec.command == ['sleep', '30']
        assert task_template.resources.mem_limit == 123
        assert task_template.resources.mem_reservation == 45
        assert task_template.restart_policy.condition == 'any'
        assert task_template.restart_policy.delay == 5678
        assert task_template.restart_policy.max_attempts == 9
        assert task_template.placement is None
        assert task_template.log_driver.name == 'json'
        assert task_template.networks == []
        assert task_template.force_update == 42

    def test_task_networks(self):
        task_template = TaskTemplate.from_spec({
            'ContainerSpec': {
                'Image': 'alpine',
                'Command': ['sleep', '30']
            },
            'Networks': [
                {
                    'Target': 'net1xaaa'
                },
                {
                    'Target': 'net2xbbb'
                }
            ]
        })

        assert task_template.networks == ['net1xaaa', 'net2xbbb']

    def test_task_placement(self):
        task_template = TaskTemplate.from_spec({
            'ContainerSpec': {
                'Image': 'alpine',
                'Command': ['sleep', '30']
            },
            'Placement': {
                'Constraints': [
                    'node.role==worker'
                ],
                'Preferences': [
                    {
                        'Spread': {
                            'SpreadDescriptor': 'node.labels.rack'
                        }
                    }
                ],
                'Platforms': [
                    {
                        'Architecture': 'amd64',
                        'OS': 'linux'
                    },
                    {
                        'OS': 'linux'
                    }
                ]
            }
        })

        assert task_template.placement.constraints == ['node.role==worker']
        assert task_template.placement.preferences == [{
            'Spread': {'SpreadDescriptor': 'node.labels.rack'}
        }]
        assert task_template.placement.platforms == [
            ('amd64', 'linux'), (None, 'linux')
        ]


class ContainerSpecTest(unittest.TestCase):
    def test_parse_mounts(self):
        spec = ContainerSpec(
            image='scratch', mounts=[
                '/local:/container',
                '/local2:/container2:ro',
                Mount(target='/target', source='/source')
            ]
        )

        assert 'Mounts' in spec
        assert len(spec['Mounts']) == 3
        for mount in spec['Mounts']:
            assert isinstance(mount, Mount)

    def test_from_spec(self):
        spec = ContainerSpec.from_spec({
            'Image': 'alpine',
            'Command': ['/bin/sh', '-c'],
            'Args': ['sleep', '60'],
            'Hostname': 'abcd1234',
            'Env': ['KEY=value', 'ENV_VAR=12345'],
            'Dir': '/var/workdir',
            'User': 'somebody',
            'Groups': ['sudo', 'wheel'],
            'StopSignal': 'SIGINT',
            'StopGracePeriod': 1000000000,
            'Labels': {
                'container.label': 'SampleLabel'
            },
            'Hosts': ['1.2.3.4 test.local'],
            'Mounts': [
                {
                    'Type': 'tmpfs',
                    'Target': '/var/cache'
                },
                {
                    'Type': 'bind',
                    'Source': '/var/app',
                    'Target': '/usr/local/app'
                }
            ],
            'Secrets': [
                {
                    'File': {
                        'Name': 'top-secret',
                        'UID': '0',
                        'GID': '0',
                        'Mode': 292
                    },
                    'SecretID': 'abcd12secret',
                    'SecretName': 'top-secret'
                }
            ],
            'Configs': [
                {
                    'File': {
                        'Name': 'svc-conf',
                        'UID': '0',
                        'GID': '0',
                        'Mode': 292
                    },
                    'ConfigID': 'abcd12config',
                    'ConfigName': 'svc-conf'
                }
            ],
            'DNSConfig': {
                'Nameservers': ['8.8.8.8', '8.8.4.4'],
                'Search': ['test.local']
            },
            'Healthcheck': {
                'Test': ['CMD-SHELL', 'exit 0'],
                'Interval': 2000000000,
                'Timeout': 1000000000,
                'StartPeriod': 5000000000,
                'Retries': 3
            },
            'TTY': True,
            'ReadOnly': True
        })

        assert type(spec) == ContainerSpec
        assert spec.image == 'alpine'
        assert spec.command == ['/bin/sh', '-c']
        assert spec.args == ['sleep', '60']
        assert spec.hostname == 'abcd1234'
        assert spec.env == ['KEY=value', 'ENV_VAR=12345']
        assert spec.workdir == '/var/workdir'
        assert spec.user == 'somebody'
        assert spec.groups == ['sudo', 'wheel']
        assert spec.stop_signal == 'SIGINT'
        assert spec.stop_grace_period == 1000000000
        assert spec.labels == {'container.label': 'SampleLabel'}
        assert spec.hosts == ['1.2.3.4 test.local']
        assert spec.mounts[0].type == 'tmpfs'
        assert spec.mounts[0].target == '/var/cache'
        assert spec.mounts[0].source is None
        assert spec.mounts[1].type == 'bind'
        assert spec.mounts[1].target == '/usr/local/app'
        assert spec.mounts[1].source == '/var/app'
        assert spec.secrets[0].id == 'abcd12secret'
        assert spec.secrets[0].name == 'top-secret'
        assert spec.secrets[0].options == {
            'Name': 'top-secret',
            'UID': '0',
            'GID': '0',
            'Mode': 292
        }
        assert spec.configs[0].id == 'abcd12config'
        assert spec.configs[0].name == 'svc-conf'
        assert spec.configs[0].options == {
            'Name': 'svc-conf',
            'UID': '0',
            'GID': '0',
            'Mode': 292
        }
        assert spec.dns_config.nameservers == ['8.8.8.8', '8.8.4.4']
        assert spec.dns_config.search == ['test.local']
        assert spec.healthcheck.test == ['CMD-SHELL', 'exit 0']
        assert spec.healthcheck.interval == 2000000000
        assert spec.healthcheck.timeout == 1000000000
        assert spec.healthcheck.start_period == 5000000000
        assert spec.healthcheck.retries == 3
        assert spec.tty is True
        assert spec.read_only is True


class UlimitTest(unittest.TestCase):
    def test_create_host_config_dict_ulimit(self):
        ulimit_dct = {'name': 'nofile', 'soft': 8096}
        config = create_host_config(
            ulimits=[ulimit_dct], version=DEFAULT_DOCKER_API_VERSION
        )
        self.assertIn('Ulimits', config)
        self.assertEqual(len(config['Ulimits']), 1)
        ulimit_obj = config['Ulimits'][0]
        self.assertTrue(isinstance(ulimit_obj, Ulimit))
        self.assertEqual(ulimit_obj.name, ulimit_dct['name'])
        self.assertEqual(ulimit_obj.soft, ulimit_dct['soft'])
        self.assertEqual(ulimit_obj['Soft'], ulimit_obj.soft)

    def test_create_host_config_dict_ulimit_capitals(self):
        ulimit_dct = {'Name': 'nofile', 'Soft': 8096, 'Hard': 8096 * 4}
        config = create_host_config(
            ulimits=[ulimit_dct], version=DEFAULT_DOCKER_API_VERSION
        )
        self.assertIn('Ulimits', config)
        self.assertEqual(len(config['Ulimits']), 1)
        ulimit_obj = config['Ulimits'][0]
        self.assertTrue(isinstance(ulimit_obj, Ulimit))
        self.assertEqual(ulimit_obj.name, ulimit_dct['Name'])
        self.assertEqual(ulimit_obj.soft, ulimit_dct['Soft'])
        self.assertEqual(ulimit_obj.hard, ulimit_dct['Hard'])
        self.assertEqual(ulimit_obj['Soft'], ulimit_obj.soft)

    def test_create_host_config_obj_ulimit(self):
        ulimit_dct = Ulimit(name='nofile', soft=8096)
        config = create_host_config(
            ulimits=[ulimit_dct], version=DEFAULT_DOCKER_API_VERSION
        )
        self.assertIn('Ulimits', config)
        self.assertEqual(len(config['Ulimits']), 1)
        ulimit_obj = config['Ulimits'][0]
        self.assertTrue(isinstance(ulimit_obj, Ulimit))
        self.assertEqual(ulimit_obj, ulimit_dct)

    def test_ulimit_invalid_type(self):
        self.assertRaises(ValueError, lambda: Ulimit(name=None))
        self.assertRaises(ValueError, lambda: Ulimit(name='hello', soft='123'))
        self.assertRaises(ValueError, lambda: Ulimit(name='hello', hard='456'))


class LogConfigTest(unittest.TestCase):
    def test_create_host_config_dict_logconfig(self):
        dct = {'type': LogConfig.types.SYSLOG, 'config': {'key1': 'val1'}}
        config = create_host_config(
            version=DEFAULT_DOCKER_API_VERSION, log_config=dct
        )
        self.assertIn('LogConfig', config)
        self.assertTrue(isinstance(config['LogConfig'], LogConfig))
        self.assertEqual(dct['type'], config['LogConfig'].type)

    def test_create_host_config_obj_logconfig(self):
        obj = LogConfig(type=LogConfig.types.SYSLOG, config={'key1': 'val1'})
        config = create_host_config(
            version=DEFAULT_DOCKER_API_VERSION, log_config=obj
        )
        self.assertIn('LogConfig', config)
        self.assertTrue(isinstance(config['LogConfig'], LogConfig))
        self.assertEqual(obj, config['LogConfig'])

    def test_logconfig_invalid_config_type(self):
        with pytest.raises(ValueError):
            LogConfig(type=LogConfig.types.JSON, config='helloworld')


class EndpointConfigTest(unittest.TestCase):
    def test_create_endpoint_config_with_aliases(self):
        config = EndpointConfig(version='1.22', aliases=['foo', 'bar'])
        assert config == {'Aliases': ['foo', 'bar']}

        with pytest.raises(InvalidVersion):
            EndpointConfig(version='1.21', aliases=['foo', 'bar'])


class IPAMConfigTest(unittest.TestCase):
    def test_create_ipam_config(self):
        ipam_pool = IPAMPool(subnet='192.168.52.0/24',
                             gateway='192.168.52.254')

        ipam_config = IPAMConfig(pool_configs=[ipam_pool])
        self.assertEqual(ipam_config, {
            'Driver': 'default',
            'Config': [{
                'Subnet': '192.168.52.0/24',
                'Gateway': '192.168.52.254',
                'AuxiliaryAddresses': None,
                'IPRange': None,
            }]
        })


class ServiceModeTest(unittest.TestCase):
    def test_replicated_simple(self):
        mode = ServiceMode('replicated')
        assert mode == {'replicated': {}}
        assert mode.mode == 'replicated'
        assert mode.replicas is None

    def test_global_simple(self):
        mode = ServiceMode('global')
        assert mode == {'global': {}}
        assert mode.mode == 'global'
        assert mode.replicas is None

    def test_global_replicas_error(self):
        with pytest.raises(InvalidArgument):
            ServiceMode('global', 21)

    def test_replicated_replicas(self):
        mode = ServiceMode('replicated', 21)
        assert mode == {'replicated': {'Replicas': 21}}
        assert mode.mode == 'replicated'
        assert mode.replicas == 21

    def test_replicated_replicas_0(self):
        mode = ServiceMode('replicated', 0)
        assert mode == {'replicated': {'Replicas': 0}}
        assert mode.mode == 'replicated'
        assert mode.replicas == 0

    def test_invalid_mode(self):
        with pytest.raises(InvalidArgument):
            ServiceMode('foobar')

    def test_from_spec(self):
        mode = ServiceMode.from_spec({'Replicated': {'Replicas': 3}})
        assert type(mode) == ServiceMode
        assert mode.mode == 'replicated'
        assert mode.replicas == 3

        mode = ServiceMode.from_spec({'Global': {}})
        assert mode.mode == 'global'


class MountTest(unittest.TestCase):
    def test_parse_mount_string_ro(self):
        mount = Mount.parse_mount_string("/foo/bar:/baz:ro")
        assert mount['Source'] == "/foo/bar"
        assert mount['Target'] == "/baz"
        assert mount['ReadOnly'] is True

    def test_parse_mount_string_rw(self):
        mount = Mount.parse_mount_string("/foo/bar:/baz:rw")
        assert mount['Source'] == "/foo/bar"
        assert mount['Target'] == "/baz"
        assert not mount['ReadOnly']

    def test_parse_mount_string_short_form(self):
        mount = Mount.parse_mount_string("/foo/bar:/baz")
        assert mount['Source'] == "/foo/bar"
        assert mount['Target'] == "/baz"
        assert not mount['ReadOnly']

    def test_parse_mount_string_no_source(self):
        mount = Mount.parse_mount_string("foo/bar")
        assert mount['Source'] is None
        assert mount['Target'] == "foo/bar"
        assert not mount['ReadOnly']

    def test_parse_mount_string_invalid(self):
        with pytest.raises(InvalidArgument):
            Mount.parse_mount_string("foo:bar:baz:rw")

    def test_parse_mount_named_volume(self):
        mount = Mount.parse_mount_string("foobar:/baz")
        assert mount['Source'] == 'foobar'
        assert mount['Target'] == '/baz'
        assert mount['Type'] == 'volume'

    def test_parse_mount_bind(self):
        mount = Mount.parse_mount_string('/foo/bar:/baz')
        assert mount['Source'] == "/foo/bar"
        assert mount['Target'] == "/baz"
        assert mount['Type'] == 'bind'

    @pytest.mark.xfail
    def test_parse_mount_bind_windows(self):
        with mock.patch('docker.types.services.IS_WINDOWS_PLATFORM', True):
            mount = Mount.parse_mount_string('C:/foo/bar:/baz')
        assert mount['Source'] == "C:/foo/bar"
        assert mount['Target'] == "/baz"
        assert mount['Type'] == 'bind'
