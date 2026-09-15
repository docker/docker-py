import unittest
from unittest import mock

import pytest

from docker.constants import DEFAULT_DOCKER_API_VERSION
from docker.errors import InvalidArgument, InvalidVersion
from docker.types import (
    AccessibilityRequirement,
    AccessMode,
    CapacityRange,
    ClusterVolumeSpec,
    ContainerSpec,
    EndpointConfig,
    HostConfig,
    IPAMConfig,
    IPAMPool,
    LogConfig,
    Mount,
    Secret,
    ServiceMode,
    Ulimit,
)
from docker.types.services import convert_service_ports


def create_host_config(*args, **kwargs):
    return HostConfig(*args, **kwargs)


class HostConfigTest(unittest.TestCase):
    def test_create_host_config_no_options_newer_api_version(self):
        config = create_host_config(version='1.21')
        assert config['NetworkMode'] == 'default'

    def test_create_host_config_invalid_cpu_cfs_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.21', cpu_quota='0')

        with pytest.raises(TypeError):
            create_host_config(version='1.21', cpu_period='0')

        with pytest.raises(TypeError):
            create_host_config(version='1.21', cpu_quota=23.11)

        with pytest.raises(TypeError):
            create_host_config(version='1.21', cpu_period=1999.0)

    def test_create_host_config_with_cpu_quota(self):
        config = create_host_config(version='1.21', cpu_quota=1999)
        assert config.get('CpuQuota') == 1999

    def test_create_host_config_with_cpu_period(self):
        config = create_host_config(version='1.21', cpu_period=1999)
        assert config.get('CpuPeriod') == 1999

    def test_create_host_config_with_blkio_constraints(self):
        blkio_rate = [{"Path": "/dev/sda", "Rate": 1000}]
        config = create_host_config(
            version='1.22', blkio_weight=1999, blkio_weight_device=blkio_rate,
            device_read_bps=blkio_rate, device_write_bps=blkio_rate,
            device_read_iops=blkio_rate, device_write_iops=blkio_rate
        )

        assert config.get('BlkioWeight') == 1999
        assert config.get('BlkioWeightDevice') is blkio_rate
        assert config.get('BlkioDeviceReadBps') is blkio_rate
        assert config.get('BlkioDeviceWriteBps') is blkio_rate
        assert config.get('BlkioDeviceReadIOps') is blkio_rate
        assert config.get('BlkioDeviceWriteIOps') is blkio_rate
        assert blkio_rate[0]['Path'] == "/dev/sda"
        assert blkio_rate[0]['Rate'] == 1000

    def test_create_host_config_with_shm_size(self):
        config = create_host_config(version='1.22', shm_size=67108864)
        assert config.get('ShmSize') == 67108864

    def test_create_host_config_with_shm_size_in_mb(self):
        config = create_host_config(version='1.22', shm_size='64M')
        assert config.get('ShmSize') == 67108864

    def test_create_host_config_with_oom_kill_disable(self):
        config = create_host_config(version='1.21', oom_kill_disable=True)
        assert config.get('OomKillDisable') is True

    def test_create_host_config_with_userns_mode(self):
        config = create_host_config(version='1.23', userns_mode='host')
        assert config.get('UsernsMode') == 'host'
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.22', userns_mode='host')
        with pytest.raises(ValueError):
            create_host_config(version='1.23', userns_mode='host12')

    def test_create_host_config_with_uts(self):
        config = create_host_config(version='1.15', uts_mode='host')
        assert config.get('UTSMode') == 'host'
        with pytest.raises(ValueError):
            create_host_config(version='1.15', uts_mode='host12')

    def test_create_host_config_with_oom_score_adj(self):
        config = create_host_config(version='1.22', oom_score_adj=100)
        assert config.get('OomScoreAdj') == 100
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.21', oom_score_adj=100)
        with pytest.raises(TypeError):
            create_host_config(version='1.22', oom_score_adj='100')

    def test_create_host_config_with_dns_opt(self):

        tested_opts = ['use-vc', 'no-tld-query']
        config = create_host_config(version='1.21', dns_opt=tested_opts)
        dns_opts = config.get('DnsOptions')

        assert 'use-vc' in dns_opts
        assert 'no-tld-query' in dns_opts

    def test_create_host_config_with_mem_reservation(self):
        config = create_host_config(version='1.21', mem_reservation=67108864)
        assert config.get('MemoryReservation') == 67108864

    def test_create_host_config_with_kernel_memory(self):
        config = create_host_config(version='1.21', kernel_memory=67108864)
        assert config.get('KernelMemory') == 67108864

    def test_create_host_config_with_pids_limit(self):
        config = create_host_config(version='1.23', pids_limit=1024)
        assert config.get('PidsLimit') == 1024

        with pytest.raises(InvalidVersion):
            create_host_config(version='1.22', pids_limit=1024)
        with pytest.raises(TypeError):
            create_host_config(version='1.23', pids_limit='1024')

    def test_create_host_config_with_isolation(self):
        config = create_host_config(version='1.24', isolation='hyperv')
        assert config.get('Isolation') == 'hyperv'

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
        config = create_host_config(version='1.21', volume_driver='local')
        assert config.get('VolumeDriver') == 'local'

    def test_create_host_config_invalid_cpu_count_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', cpu_count='1')

    def test_create_host_config_with_cpu_count(self):
        config = create_host_config(version='1.25', cpu_count=2)
        assert config.get('CpuCount') == 2
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.24', cpu_count=1)

    def test_create_host_config_invalid_cpu_percent_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', cpu_percent='1')

    def test_create_host_config_with_cpu_percent(self):
        config = create_host_config(version='1.25', cpu_percent=15)
        assert config.get('CpuPercent') == 15
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.24', cpu_percent=10)

    def test_create_host_config_invalid_nano_cpus_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', nano_cpus='0')

    def test_create_host_config_with_nano_cpus(self):
        config = create_host_config(version='1.25', nano_cpus=1000)
        assert config.get('NanoCpus') == 1000
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.24', nano_cpus=1)

    def test_create_host_config_with_cpu_rt_period_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', cpu_rt_period='1000')

    def test_create_host_config_with_cpu_rt_period(self):
        config = create_host_config(version='1.25', cpu_rt_period=1000)
        assert config.get('CPURealtimePeriod') == 1000
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.24', cpu_rt_period=1000)

    def test_ctrate_host_config_with_cpu_rt_runtime_types(self):
        with pytest.raises(TypeError):
            create_host_config(version='1.25', cpu_rt_runtime='1000')

    def test_create_host_config_with_cpu_rt_runtime(self):
        config = create_host_config(version='1.25', cpu_rt_runtime=1000)
        assert config.get('CPURealtimeRuntime') == 1000
        with pytest.raises(InvalidVersion):
            create_host_config(version='1.24', cpu_rt_runtime=1000)


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


class UlimitTest(unittest.TestCase):
    def test_create_host_config_dict_ulimit(self):
        ulimit_dct = {'name': 'nofile', 'soft': 8096}
        config = create_host_config(
            ulimits=[ulimit_dct], version=DEFAULT_DOCKER_API_VERSION
        )
        assert 'Ulimits' in config
        assert len(config['Ulimits']) == 1
        ulimit_obj = config['Ulimits'][0]
        assert isinstance(ulimit_obj, Ulimit)
        assert ulimit_obj.name == ulimit_dct['name']
        assert ulimit_obj.soft == ulimit_dct['soft']
        assert ulimit_obj['Soft'] == ulimit_obj.soft

    def test_create_host_config_dict_ulimit_capitals(self):
        ulimit_dct = {'Name': 'nofile', 'Soft': 8096, 'Hard': 8096 * 4}
        config = create_host_config(
            ulimits=[ulimit_dct], version=DEFAULT_DOCKER_API_VERSION
        )
        assert 'Ulimits' in config
        assert len(config['Ulimits']) == 1
        ulimit_obj = config['Ulimits'][0]
        assert isinstance(ulimit_obj, Ulimit)
        assert ulimit_obj.name == ulimit_dct['Name']
        assert ulimit_obj.soft == ulimit_dct['Soft']
        assert ulimit_obj.hard == ulimit_dct['Hard']
        assert ulimit_obj['Soft'] == ulimit_obj.soft

    def test_create_host_config_obj_ulimit(self):
        ulimit_dct = Ulimit(name='nofile', soft=8096)
        config = create_host_config(
            ulimits=[ulimit_dct], version=DEFAULT_DOCKER_API_VERSION
        )
        assert 'Ulimits' in config
        assert len(config['Ulimits']) == 1
        ulimit_obj = config['Ulimits'][0]
        assert isinstance(ulimit_obj, Ulimit)
        assert ulimit_obj == ulimit_dct

    def test_ulimit_invalid_type(self):
        with pytest.raises(ValueError):
            Ulimit(name=None)
        with pytest.raises(ValueError):
            Ulimit(name='hello', soft='123')
        with pytest.raises(ValueError):
            Ulimit(name='hello', hard='456')


class LogConfigTest(unittest.TestCase):
    def test_create_host_config_dict_logconfig(self):
        dct = {'type': LogConfig.types.SYSLOG, 'config': {'key1': 'val1'}}
        config = create_host_config(
            version=DEFAULT_DOCKER_API_VERSION, log_config=dct
        )
        assert 'LogConfig' in config
        assert isinstance(config['LogConfig'], LogConfig)
        assert dct['type'] == config['LogConfig'].type

    def test_create_host_config_obj_logconfig(self):
        obj = LogConfig(type=LogConfig.types.SYSLOG, config={'key1': 'val1'})
        config = create_host_config(
            version=DEFAULT_DOCKER_API_VERSION, log_config=obj
        )
        assert 'LogConfig' in config
        assert isinstance(config['LogConfig'], LogConfig)
        assert obj == config['LogConfig']

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
        assert ipam_config == {
            'Driver': 'default',
            'Config': [{
                'Subnet': '192.168.52.0/24',
                'Gateway': '192.168.52.254',
                'AuxiliaryAddresses': None,
                'IPRange': None,
            }]
        }


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

    def test_replicated_job_simple(self):
        mode = ServiceMode('replicated-job')
        assert mode == {'ReplicatedJob': {}}
        assert mode.mode == 'ReplicatedJob'
        assert mode.replicas is None

    def test_global_job_simple(self):
        mode = ServiceMode('global-job')
        assert mode == {'GlobalJob': {}}
        assert mode.mode == 'GlobalJob'
        assert mode.replicas is None

    def test_global_replicas_error(self):
        with pytest.raises(InvalidArgument):
            ServiceMode('global', 21)

    def test_global_job_replicas_simple(self):
        with pytest.raises(InvalidArgument):
            ServiceMode('global-job', 21)

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


class ServicePortsTest(unittest.TestCase):
    def test_convert_service_ports_simple(self):
        ports = {8080: 80}
        assert convert_service_ports(ports) == [{
            'Protocol': 'tcp',
            'PublishedPort': 8080,
            'TargetPort': 80,
        }]

    def test_convert_service_ports_with_protocol(self):
        ports = {8080: (80, 'udp')}

        assert convert_service_ports(ports) == [{
            'Protocol': 'udp',
            'PublishedPort': 8080,
            'TargetPort': 80,
        }]

    def test_convert_service_ports_with_protocol_and_mode(self):
        ports = {8080: (80, 'udp', 'ingress')}

        assert convert_service_ports(ports) == [{
            'Protocol': 'udp',
            'PublishedPort': 8080,
            'TargetPort': 80,
            'PublishMode': 'ingress',
        }]

    def test_convert_service_ports_invalid(self):
        ports = {8080: ('way', 'too', 'many', 'items', 'here')}

        with pytest.raises(ValueError):
            convert_service_ports(ports)

    def test_convert_service_ports_no_protocol_and_mode(self):
        ports = {8080: (80, None, 'host')}

        assert convert_service_ports(ports) == [{
            'Protocol': 'tcp',
            'PublishedPort': 8080,
            'TargetPort': 80,
            'PublishMode': 'host',
        }]

    def test_convert_service_ports_multiple(self):
        ports = {
            8080: (80, None, 'host'),
            9999: 99,
            2375: (2375,)
        }

        converted_ports = convert_service_ports(ports)
        assert {
            'Protocol': 'tcp',
            'PublishedPort': 8080,
            'TargetPort': 80,
            'PublishMode': 'host',
        } in converted_ports

        assert {
            'Protocol': 'tcp',
            'PublishedPort': 9999,
            'TargetPort': 99,
        } in converted_ports

        assert {
            'Protocol': 'tcp',
            'PublishedPort': 2375,
            'TargetPort': 2375,
        } in converted_ports

        assert len(converted_ports) == 3

class ClusterVolumeSpecTest(unittest.TestCase):
    def test_cluster_volume_spec_with_fully_populated_access_mode(self):
        secrets = [
            Secret(key="api_key1", secret="secret1"),
            Secret(key="api_key2", secret="secret2"),
        ]

        capacity_range = CapacityRange(limit_bytes=10240, required_bytes=1024)

        accessibility_requirements = AccessibilityRequirement(
            requisite=["zone1", "zone2"], preferred=["zone1"]
        )

        access_mode = AccessMode(
            scope="global",
            sharing="readonly",
            mount_volume="nfs",
            availabilty="high",
            secrets=secrets,
            capacity_range=capacity_range,
            accessibility_requirements=accessibility_requirements,
        )

        cluster_spec = ClusterVolumeSpec(group="production", access_mode=access_mode)

        self.assertEqual(cluster_spec["Group"], "production")
        self.assertIs(cluster_spec["AccessMode"], access_mode)

        self.assertEqual(cluster_spec["AccessMode"]["Scope"], "global")
        self.assertEqual(cluster_spec["AccessMode"]["Sharing"], "readonly")
        self.assertEqual(cluster_spec["AccessMode"]["MountVolume"]['Target'], "nfs")
        self.assertEqual(cluster_spec["AccessMode"]["Availabilty"], "high")

        self.assertEqual(len(cluster_spec["AccessMode"]["Secrets"]), 2)
        self.assertEqual(cluster_spec["AccessMode"]["Secrets"][0]["Key"], "api_key1")
        self.assertEqual(cluster_spec["AccessMode"]["Secrets"][0]["Secret"], "secret1")
        self.assertEqual(cluster_spec["AccessMode"]["Secrets"][1]["Key"], "api_key2")
        self.assertEqual(cluster_spec["AccessMode"]["Secrets"][1]["Secret"], "secret2")

        self.assertEqual(
            cluster_spec["AccessMode"]["CapacityRange"]["LimitBytes"], 10240
        )
        self.assertEqual(
            cluster_spec["AccessMode"]["CapacityRange"]["RequiredBytes"], 1024
        )

        self.assertEqual(
            cluster_spec["AccessMode"]["AccessibilityRequirements"]["Requisite"],
            ["zone1", "zone2"],
        )
        self.assertEqual(
            cluster_spec["AccessMode"]["AccessibilityRequirements"]["Preferred"],
            ["zone1"],
        )

    def test_cluster_volume_spec_with_dict_based_access_mode(self):
        access_mode = AccessMode(
            scope="team",
            sharing="readwrite",
            secrets=[
                {"key": "db_user", "secret": "password123"},
                {"key": "api_token", "secret": "abc123xyz"},
            ],
            capacity_range={"limit_bytes": 20480, "required_bytes": 2048},
            accessibility_requirements={
                "requisite": ["datacenter1"],
                "preferred": ["rack1", "rack2"],
            },
        )

        cluster_spec = ClusterVolumeSpec(group="development", access_mode=access_mode)

        self.assertEqual(cluster_spec["Group"], "development")

        self.assertIsInstance(cluster_spec["AccessMode"]["Secrets"][0], Secret)
        self.assertIsInstance(cluster_spec["AccessMode"]["Secrets"][1], Secret)
        self.assertIsInstance(
            cluster_spec["AccessMode"]["CapacityRange"], CapacityRange
        )
        self.assertIsInstance(
            cluster_spec["AccessMode"]["AccessibilityRequirements"],
            AccessibilityRequirement,
        )

        self.assertEqual(cluster_spec["AccessMode"]["Secrets"][0].key, "db_user")
        self.assertEqual(
            cluster_spec["AccessMode"]["Secrets"][0].secret, "password123"
        )
        self.assertEqual(
            cluster_spec["AccessMode"]["CapacityRange"].limit_bytes, 20480
        )
        self.assertEqual(
            cluster_spec["AccessMode"]["AccessibilityRequirements"].requisite,
            ["datacenter1"],
        )

    def test_cluster_volume_spec_with_minimal_access_mode(self):
        access_mode = AccessMode(scope="local", sharing="exclusive")

        cluster_spec = ClusterVolumeSpec(group="testing", access_mode=access_mode)

        self.assertEqual(cluster_spec["Group"], "testing")
        self.assertEqual(cluster_spec["AccessMode"]["Scope"], "local")
        self.assertEqual(cluster_spec["AccessMode"]["Sharing"], "exclusive")

        self.assertNotIn("Secrets", cluster_spec["AccessMode"])
        self.assertNotIn("CapacityRange", cluster_spec["AccessMode"])
        self.assertNotIn("AccessibilityRequirements", cluster_spec["AccessMode"])

    def test_cluster_volume_spec_with_mixed_nested_objects(self):
        access_mode = AccessMode(
            scope="container",
            secrets=[Secret(key="api_key", secret="secret_value")],
            capacity_range=CapacityRange(limit_bytes=5120),
        )

        cluster_spec = ClusterVolumeSpec(group="staging", access_mode=access_mode)

        self.assertEqual(cluster_spec["Group"], "staging")
        self.assertEqual(cluster_spec["AccessMode"]["Scope"], "container")

        self.assertIn("Secrets", cluster_spec["AccessMode"])
        self.assertEqual(len(cluster_spec["AccessMode"]["Secrets"]), 1)
        self.assertEqual(cluster_spec["AccessMode"]["Secrets"][0].key, "api_key")

        self.assertIn("CapacityRange", cluster_spec["AccessMode"])
        self.assertEqual(cluster_spec["AccessMode"]["CapacityRange"].limit_bytes, 5120)
        self.assertIsNone(cluster_spec["AccessMode"]["CapacityRange"].required_bytes)

        self.assertNotIn("AccessibilityRequirements", cluster_spec["AccessMode"])

    def test_cluster_volume_spec_with_pascal_case_input(self):
        access_mode = AccessMode(
            scope="namespace",
            capacity_range={"LimitBytes": 8192, "RequiredBytes": 4096},
            accessibility_requirements={"Requisite": ["zone3"], "Preferred": ["zone3"]},
        )

        cluster_spec = ClusterVolumeSpec(group="utility", access_mode=access_mode)

        self.assertEqual(cluster_spec["Group"], "utility")

        self.assertEqual(cluster_spec["AccessMode"]["CapacityRange"].limit_bytes, 8192)
        self.assertEqual(
            cluster_spec["AccessMode"]["CapacityRange"].required_bytes, 4096
        )
        self.assertEqual(
            cluster_spec["AccessMode"]["AccessibilityRequirements"].requisite,
            ["zone3"],
        )
        self.assertEqual(
            cluster_spec["AccessMode"]["AccessibilityRequirements"].preferred,
            ["zone3"],
        )

    def test_cluster_volume_spec_only_group(self):
        cluster_spec = ClusterVolumeSpec(group="backup")

        self.assertEqual(cluster_spec["Group"], "backup")
        self.assertNotIn("access_mode", cluster_spec)

    def test_cluster_volume_spec_only_access_mode(self):
        access_mode = AccessMode(scope="volume")
        cluster_spec = ClusterVolumeSpec(access_mode=access_mode)

        self.assertNotIn("Group", cluster_spec)
        self.assertEqual(cluster_spec["AccessMode"]["Scope"], "volume")

    def test_access_mode_direct_creation_in_cluster_volume_spec(self):
        with self.assertRaises(TypeError):
            ClusterVolumeSpec(
                group="direct", access_mode={"Scope": "direct", "Sharing": "shared"}
            )
