# -*- coding: utf-8 -*-

import unittest

import pytest

from docker.constants import DEFAULT_DOCKER_API_VERSION
from docker.errors import InvalidArgument, InvalidVersion
from docker.types import (
    EndpointConfig, HostConfig, IPAMConfig, IPAMPool, LogConfig, Mount, Ulimit,
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


class TestMounts(unittest.TestCase):
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


class TestServiceMounts(unittest.TestCase):

    def test_parse_mount_string_defaults(self):
        mount = Mount.parse_mount_string(
            "source=/foo/bar,target=/abc/xyz")
        self.assertEqual(mount['Source'], '/foo/bar')
        self.assertEqual(mount['Target'], '/abc/xyz')
        self.assertEqual(mount['Type'], 'volume')
        self.assertEqual(mount['ReadOnly'], False)

    def test_parse_mount_string_common(self):
        mount = Mount.parse_mount_string(
            "type=bind,src=/foo/bar,dst=/abc/xyz,readonly,propagation=slave")
        self.assertEqual(mount['Source'], '/foo/bar')
        self.assertEqual(mount['Target'], '/abc/xyz')
        self.assertEqual(mount['Type'], 'bind')
        self.assertEqual(mount['ReadOnly'], True)
        self.assertEqual(mount['BindOptions']['Propagation'], 'slave')

    def test_parse_mount_string_advanced(self):
        mount = Mount.parse_mount_string(
            "src=/foo/bar,dst=/abc/xyz,ro,volume-label=color1=red,"
            "volume-label='color2=blue'")
        self.assertEqual(mount['Source'], '/foo/bar')
        self.assertEqual(mount['Target'], '/abc/xyz')
        self.assertEqual(mount['ReadOnly'], True)
        self.assertDictEqual(
            mount['VolumeOptions']['Labels'],
            {'color1': 'red', 'color2': 'blue'})

    @pytest.mark.xfail
    def test_parse_mount_bind_windows(self):
        with mock.patch('docker.types.services.IS_WINDOWS_PLATFORM', True):
            mount = Mount.parse_mount_string(
                "source=C:/foo/bar,target=/baz")
        assert mount['Source'] == "C:/foo/bar"
        assert mount['Target'] == "/baz"
        assert mount['Type'] == 'volume'
