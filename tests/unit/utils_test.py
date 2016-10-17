# -*- coding: utf-8 -*-

import base64
import json
import os
import os.path
import shutil
import sys
import tarfile
import tempfile

import pytest
import six

from docker.client import Client
from docker.constants import (
    DEFAULT_DOCKER_API_VERSION, IS_WINDOWS_PLATFORM
)
from docker.errors import DockerException, InvalidVersion
from docker.utils import (
    parse_repository_tag, parse_host, convert_filters, kwargs_from_env,
    create_host_config, Ulimit, LogConfig, parse_bytes, parse_env_file,
    exclude_paths, convert_volume_binds, decode_json_header, tar,
    split_command, create_ipam_config, create_ipam_pool, parse_devices,
    update_headers
)

from docker.utils.ports import build_port_bindings, split_port
from docker.utils.utils import create_endpoint_config, format_environment

from .. import base
from ..helpers import make_tree


TEST_CERT_DIR = os.path.join(
    os.path.dirname(__file__),
    'testdata/certs',
)


class DecoratorsTest(base.BaseTestCase):
    def test_update_headers(self):
        sample_headers = {
            'X-Docker-Locale': 'en-US',
        }

        def f(self, headers=None):
            return headers

        client = Client()
        client._auth_configs = {}

        g = update_headers(f)
        assert g(client, headers=None) is None
        assert g(client, headers={}) == {}
        assert g(client, headers={'Content-type': 'application/json'}) == {
            'Content-type': 'application/json',
        }

        client._auth_configs = {
            'HttpHeaders': sample_headers
        }

        assert g(client, headers=None) == sample_headers
        assert g(client, headers={}) == sample_headers
        assert g(client, headers={'Content-type': 'application/json'}) == {
            'Content-type': 'application/json',
            'X-Docker-Locale': 'en-US',
        }


class HostConfigTest(base.BaseTestCase):
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

    def test_create_endpoint_config_with_aliases(self):
        config = create_endpoint_config(version='1.22', aliases=['foo', 'bar'])
        assert config == {'Aliases': ['foo', 'bar']}

        with pytest.raises(InvalidVersion):
            create_endpoint_config(version='1.21', aliases=['foo', 'bar'])

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
            create_host_config(version='1.22', pids_limit='1024')


class UlimitTest(base.BaseTestCase):
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


class LogConfigTest(base.BaseTestCase):
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


class KwargsFromEnvTest(base.BaseTestCase):
    def setUp(self):
        self.os_environ = os.environ.copy()

    def tearDown(self):
        os.environ = self.os_environ

    def test_kwargs_from_env_empty(self):
        os.environ.update(DOCKER_HOST='',
                          DOCKER_CERT_PATH='')
        os.environ.pop('DOCKER_TLS_VERIFY', None)

        kwargs = kwargs_from_env()
        self.assertEqual(None, kwargs.get('base_url'))
        self.assertEqual(None, kwargs.get('tls'))

    def test_kwargs_from_env_tls(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='1')
        kwargs = kwargs_from_env(assert_hostname=False)
        self.assertEqual('https://192.168.59.103:2376', kwargs['base_url'])
        self.assertTrue('ca.pem' in kwargs['tls'].ca_cert)
        self.assertTrue('cert.pem' in kwargs['tls'].cert[0])
        self.assertTrue('key.pem' in kwargs['tls'].cert[1])
        self.assertEqual(False, kwargs['tls'].assert_hostname)
        self.assertTrue(kwargs['tls'].verify)
        try:
            client = Client(**kwargs)
            self.assertEqual(kwargs['base_url'], client.base_url)
            self.assertEqual(kwargs['tls'].ca_cert, client.verify)
            self.assertEqual(kwargs['tls'].cert, client.cert)
        except TypeError as e:
            self.fail(e)

    def test_kwargs_from_env_tls_verify_false(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='')
        kwargs = kwargs_from_env(assert_hostname=True)
        self.assertEqual('https://192.168.59.103:2376', kwargs['base_url'])
        self.assertTrue('ca.pem' in kwargs['tls'].ca_cert)
        self.assertTrue('cert.pem' in kwargs['tls'].cert[0])
        self.assertTrue('key.pem' in kwargs['tls'].cert[1])
        self.assertEqual(True, kwargs['tls'].assert_hostname)
        self.assertEqual(False, kwargs['tls'].verify)
        try:
            client = Client(**kwargs)
            self.assertEqual(kwargs['base_url'], client.base_url)
            self.assertEqual(kwargs['tls'].cert, client.cert)
            self.assertFalse(kwargs['tls'].verify)
        except TypeError as e:
            self.fail(e)

    def test_kwargs_from_env_tls_verify_false_no_cert(self):
        temp_dir = tempfile.mkdtemp()
        cert_dir = os.path.join(temp_dir, '.docker')
        shutil.copytree(TEST_CERT_DIR, cert_dir)

        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          HOME=temp_dir,
                          DOCKER_TLS_VERIFY='')
        os.environ.pop('DOCKER_CERT_PATH', None)
        kwargs = kwargs_from_env(assert_hostname=True)
        self.assertEqual('tcp://192.168.59.103:2376', kwargs['base_url'])

    def test_kwargs_from_env_no_cert_path(self):
        try:
            temp_dir = tempfile.mkdtemp()
            cert_dir = os.path.join(temp_dir, '.docker')
            shutil.copytree(TEST_CERT_DIR, cert_dir)

            os.environ.update(HOME=temp_dir,
                              DOCKER_CERT_PATH='',
                              DOCKER_TLS_VERIFY='1')

            kwargs = kwargs_from_env()
            self.assertTrue(kwargs['tls'].verify)
            self.assertIn(cert_dir, kwargs['tls'].ca_cert)
            self.assertIn(cert_dir, kwargs['tls'].cert[0])
            self.assertIn(cert_dir, kwargs['tls'].cert[1])
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir)

    def test_kwargs_from_env_alternate_env(self):
        # Values in os.environ are entirely ignored if an alternate is
        # provided
        os.environ.update(
            DOCKER_HOST='tcp://192.168.59.103:2376',
            DOCKER_CERT_PATH=TEST_CERT_DIR,
            DOCKER_TLS_VERIFY=''
        )
        kwargs = kwargs_from_env(environment={
            'DOCKER_HOST': 'http://docker.gensokyo.jp:2581',
        })
        assert 'http://docker.gensokyo.jp:2581' == kwargs['base_url']
        assert 'tls' not in kwargs


class ConverVolumeBindsTest(base.BaseTestCase):
    def test_convert_volume_binds_empty(self):
        self.assertEqual(convert_volume_binds({}), [])
        self.assertEqual(convert_volume_binds([]), [])

    def test_convert_volume_binds_list(self):
        data = ['/a:/a:ro', '/b:/c:z']
        self.assertEqual(convert_volume_binds(data), data)

    def test_convert_volume_binds_complete(self):
        data = {
            '/mnt/vol1': {
                'bind': '/data',
                'mode': 'ro'
            }
        }
        self.assertEqual(convert_volume_binds(data), ['/mnt/vol1:/data:ro'])

    def test_convert_volume_binds_compact(self):
        data = {
            '/mnt/vol1': '/data'
        }
        self.assertEqual(convert_volume_binds(data), ['/mnt/vol1:/data:rw'])

    def test_convert_volume_binds_no_mode(self):
        data = {
            '/mnt/vol1': {
                'bind': '/data'
            }
        }
        self.assertEqual(convert_volume_binds(data), ['/mnt/vol1:/data:rw'])

    def test_convert_volume_binds_unicode_bytes_input(self):
        expected = [u'/mnt/지연:/unicode/박:rw']

        data = {
            u'/mnt/지연'.encode('utf-8'): {
                'bind': u'/unicode/박'.encode('utf-8'),
                'mode': 'rw'
            }
        }
        self.assertEqual(
            convert_volume_binds(data), expected
        )

    def test_convert_volume_binds_unicode_unicode_input(self):
        expected = [u'/mnt/지연:/unicode/박:rw']

        data = {
            u'/mnt/지연': {
                'bind': u'/unicode/박',
                'mode': 'rw'
            }
        }
        self.assertEqual(
            convert_volume_binds(data), expected
        )


class ParseEnvFileTest(base.BaseTestCase):
    def generate_tempfile(self, file_content=None):
        """
        Generates a temporary file for tests with the content
        of 'file_content' and returns the filename.
        Don't forget to unlink the file with os.unlink() after.
        """
        local_tempfile = tempfile.NamedTemporaryFile(delete=False)
        local_tempfile.write(file_content.encode('UTF-8'))
        local_tempfile.close()
        return local_tempfile.name

    def test_parse_env_file_proper(self):
        env_file = self.generate_tempfile(
            file_content='USER=jdoe\nPASS=secret')
        get_parse_env_file = parse_env_file(env_file)
        self.assertEqual(get_parse_env_file,
                         {'USER': 'jdoe', 'PASS': 'secret'})
        os.unlink(env_file)

    def test_parse_env_file_with_equals_character(self):
        env_file = self.generate_tempfile(
            file_content='USER=jdoe\nPASS=sec==ret')
        get_parse_env_file = parse_env_file(env_file)
        self.assertEqual(get_parse_env_file,
                         {'USER': 'jdoe', 'PASS': 'sec==ret'})
        os.unlink(env_file)

    def test_parse_env_file_commented_line(self):
        env_file = self.generate_tempfile(
            file_content='USER=jdoe\n#PASS=secret')
        get_parse_env_file = parse_env_file((env_file))
        self.assertEqual(get_parse_env_file, {'USER': 'jdoe'})
        os.unlink(env_file)

    def test_parse_env_file_invalid_line(self):
        env_file = self.generate_tempfile(
            file_content='USER jdoe')
        self.assertRaises(
            DockerException, parse_env_file, env_file)
        os.unlink(env_file)


class ParseHostTest(base.BaseTestCase):
    def test_parse_host(self):
        invalid_hosts = [
            '0.0.0.0',
            'tcp://',
            'udp://127.0.0.1',
            'udp://127.0.0.1:2375',
        ]

        valid_hosts = {
            '0.0.0.1:5555': 'http://0.0.0.1:5555',
            ':6666': 'http://127.0.0.1:6666',
            'tcp://:7777': 'http://127.0.0.1:7777',
            'http://:7777': 'http://127.0.0.1:7777',
            'https://kokia.jp:2375': 'https://kokia.jp:2375',
            'unix:///var/run/docker.sock': 'http+unix:///var/run/docker.sock',
            'unix://': 'http+unix://var/run/docker.sock',
            '12.234.45.127:2375/docker/engine': (
                'http://12.234.45.127:2375/docker/engine'
            ),
            'somehost.net:80/service/swarm': (
                'http://somehost.net:80/service/swarm'
            ),
            'npipe:////./pipe/docker_engine': 'npipe:////./pipe/docker_engine',
            '[fd12::82d1]:2375': 'http://[fd12::82d1]:2375',
            'https://[fd12:5672::12aa]:1090': 'https://[fd12:5672::12aa]:1090',
            '[fd12::82d1]:2375/docker/engine': (
                'http://[fd12::82d1]:2375/docker/engine'
            ),
        }

        for host in invalid_hosts:
            with pytest.raises(DockerException):
                parse_host(host, None)

        for host, expected in valid_hosts.items():
            assert parse_host(host, None) == expected

    def test_parse_host_empty_value(self):
        unix_socket = 'http+unix://var/run/docker.sock'
        npipe = 'npipe:////./pipe/docker_engine'

        for val in [None, '']:
            assert parse_host(val, is_win32=False) == unix_socket
            assert parse_host(val, is_win32=True) == npipe

    def test_parse_host_tls(self):
        host_value = 'myhost.docker.net:3348'
        expected_result = 'https://myhost.docker.net:3348'
        assert parse_host(host_value, tls=True) == expected_result

    def test_parse_host_tls_tcp_proto(self):
        host_value = 'tcp://myhost.docker.net:3348'
        expected_result = 'https://myhost.docker.net:3348'
        assert parse_host(host_value, tls=True) == expected_result

    def test_parse_host_trailing_slash(self):
        host_value = 'tcp://myhost.docker.net:2376/'
        expected_result = 'http://myhost.docker.net:2376'
        assert parse_host(host_value) == expected_result


class ParseRepositoryTagTest(base.BaseTestCase):
    sha = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

    def test_index_image_no_tag(self):
        self.assertEqual(
            parse_repository_tag("root"), ("root", None)
        )

    def test_index_image_tag(self):
        self.assertEqual(
            parse_repository_tag("root:tag"), ("root", "tag")
        )

    def test_index_user_image_no_tag(self):
        self.assertEqual(
            parse_repository_tag("user/repo"), ("user/repo", None)
        )

    def test_index_user_image_tag(self):
        self.assertEqual(
            parse_repository_tag("user/repo:tag"), ("user/repo", "tag")
        )

    def test_private_reg_image_no_tag(self):
        self.assertEqual(
            parse_repository_tag("url:5000/repo"), ("url:5000/repo", None)
        )

    def test_private_reg_image_tag(self):
        self.assertEqual(
            parse_repository_tag("url:5000/repo:tag"), ("url:5000/repo", "tag")
        )

    def test_index_image_sha(self):
        self.assertEqual(
            parse_repository_tag("root@sha256:{0}".format(self.sha)),
            ("root", "sha256:{0}".format(self.sha))
        )

    def test_private_reg_image_sha(self):
        self.assertEqual(
            parse_repository_tag("url:5000/repo@sha256:{0}".format(self.sha)),
            ("url:5000/repo", "sha256:{0}".format(self.sha))
        )


class ParseDeviceTest(base.BaseTestCase):
    def test_dict(self):
        devices = parse_devices([{
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'r'
        }])
        self.assertEqual(devices[0], {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'r'
        })

    def test_partial_string_definition(self):
        devices = parse_devices(['/dev/sda1'])
        self.assertEqual(devices[0], {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/sda1',
            'CgroupPermissions': 'rwm'
        })

    def test_permissionless_string_definition(self):
        devices = parse_devices(['/dev/sda1:/dev/mnt1'])
        self.assertEqual(devices[0], {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'rwm'
        })

    def test_full_string_definition(self):
        devices = parse_devices(['/dev/sda1:/dev/mnt1:r'])
        self.assertEqual(devices[0], {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'r'
        })

    def test_hybrid_list(self):
        devices = parse_devices([
            '/dev/sda1:/dev/mnt1:rw',
            {
                'PathOnHost': '/dev/sda2',
                'PathInContainer': '/dev/mnt2',
                'CgroupPermissions': 'r'
            }
        ])

        self.assertEqual(devices[0], {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'rw'
        })
        self.assertEqual(devices[1], {
            'PathOnHost': '/dev/sda2',
            'PathInContainer': '/dev/mnt2',
            'CgroupPermissions': 'r'
        })


class ParseBytesTest(base.BaseTestCase):
    def test_parse_bytes_valid(self):
        self.assertEqual(parse_bytes("512MB"), 536870912)
        self.assertEqual(parse_bytes("512M"), 536870912)
        self.assertEqual(parse_bytes("512m"), 536870912)

    def test_parse_bytes_invalid(self):
        self.assertRaises(DockerException, parse_bytes, "512MK")
        self.assertRaises(DockerException, parse_bytes, "512L")
        self.assertRaises(DockerException, parse_bytes, "127.0.0.1K")

    def test_parse_bytes_float(self):
        self.assertRaises(DockerException, parse_bytes, "1.5k")

    def test_parse_bytes_maxint(self):
        self.assertEqual(
            parse_bytes("{0}k".format(sys.maxsize)), sys.maxsize * 1024
        )


class UtilsTest(base.BaseTestCase):
    longMessage = True

    def test_convert_filters(self):
        tests = [
            ({'dangling': True}, '{"dangling": ["true"]}'),
            ({'dangling': "true"}, '{"dangling": ["true"]}'),
            ({'exited': 0}, '{"exited": [0]}'),
            ({'exited': [0, 1]}, '{"exited": [0, 1]}'),
        ]

        for filters, expected in tests:
            self.assertEqual(convert_filters(filters), expected)

    def test_decode_json_header(self):
        obj = {'a': 'b', 'c': 1}
        data = None
        if six.PY3:
            data = base64.urlsafe_b64encode(bytes(json.dumps(obj), 'utf-8'))
        else:
            data = base64.urlsafe_b64encode(json.dumps(obj))
        decoded_data = decode_json_header(data)
        self.assertEqual(obj, decoded_data)

    def test_create_ipam_config(self):
        ipam_pool = create_ipam_pool(subnet='192.168.52.0/24',
                                     gateway='192.168.52.254')

        ipam_config = create_ipam_config(pool_configs=[ipam_pool])
        self.assertEqual(ipam_config, {
            'Driver': 'default',
            'Config': [{
                'Subnet': '192.168.52.0/24',
                'Gateway': '192.168.52.254',
                'AuxiliaryAddresses': None,
                'IPRange': None,
            }]
        })


class SplitCommandTest(base.BaseTestCase):
    def test_split_command_with_unicode(self):
        self.assertEqual(split_command(u'echo μμ'), ['echo', 'μμ'])

    @pytest.mark.skipif(six.PY3, reason="shlex doesn't support bytes in py3")
    def test_split_command_with_bytes(self):
        self.assertEqual(split_command('echo μμ'), ['echo', 'μμ'])


class PortsTest(base.BaseTestCase):
    def test_split_port_with_host_ip(self):
        internal_port, external_port = split_port("127.0.0.1:1000:2000")
        self.assertEqual(internal_port, ["2000"])
        self.assertEqual(external_port, [("127.0.0.1", "1000")])

    def test_split_port_with_protocol(self):
        internal_port, external_port = split_port("127.0.0.1:1000:2000/udp")
        self.assertEqual(internal_port, ["2000/udp"])
        self.assertEqual(external_port, [("127.0.0.1", "1000")])

    def test_split_port_with_host_ip_no_port(self):
        internal_port, external_port = split_port("127.0.0.1::2000")
        self.assertEqual(internal_port, ["2000"])
        self.assertEqual(external_port, [("127.0.0.1", None)])

    def test_split_port_range_with_host_ip_no_port(self):
        internal_port, external_port = split_port("127.0.0.1::2000-2001")
        self.assertEqual(internal_port, ["2000", "2001"])
        self.assertEqual(external_port,
                         [("127.0.0.1", None), ("127.0.0.1", None)])

    def test_split_port_with_host_port(self):
        internal_port, external_port = split_port("1000:2000")
        self.assertEqual(internal_port, ["2000"])
        self.assertEqual(external_port, ["1000"])

    def test_split_port_range_with_host_port(self):
        internal_port, external_port = split_port("1000-1001:2000-2001")
        self.assertEqual(internal_port, ["2000", "2001"])
        self.assertEqual(external_port, ["1000", "1001"])

    def test_split_port_no_host_port(self):
        internal_port, external_port = split_port("2000")
        self.assertEqual(internal_port, ["2000"])
        self.assertEqual(external_port, None)

    def test_split_port_range_no_host_port(self):
        internal_port, external_port = split_port("2000-2001")
        self.assertEqual(internal_port, ["2000", "2001"])
        self.assertEqual(external_port, None)

    def test_split_port_range_with_protocol(self):
        internal_port, external_port = split_port(
            "127.0.0.1:1000-1001:2000-2001/udp")
        self.assertEqual(internal_port, ["2000/udp", "2001/udp"])
        self.assertEqual(external_port,
                         [("127.0.0.1", "1000"), ("127.0.0.1", "1001")])

    def test_split_port_invalid(self):
        self.assertRaises(ValueError,
                          lambda: split_port("0.0.0.0:1000:2000:tcp"))

    def test_non_matching_length_port_ranges(self):
        self.assertRaises(
            ValueError,
            lambda: split_port("0.0.0.0:1000-1010:2000-2002/tcp")
        )

    def test_port_and_range_invalid(self):
        self.assertRaises(ValueError,
                          lambda: split_port("0.0.0.0:1000:2000-2002/tcp"))

    def test_port_only_with_colon(self):
        self.assertRaises(ValueError,
                          lambda: split_port(":80"))

    def test_host_only_with_colon(self):
        self.assertRaises(ValueError,
                          lambda: split_port("localhost:"))

    def test_build_port_bindings_with_one_port(self):
        port_bindings = build_port_bindings(["127.0.0.1:1000:1000"])
        self.assertEqual(port_bindings["1000"], [("127.0.0.1", "1000")])

    def test_build_port_bindings_with_matching_internal_ports(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000:1000", "127.0.0.1:2000:1000"])
        self.assertEqual(port_bindings["1000"],
                         [("127.0.0.1", "1000"), ("127.0.0.1", "2000")])

    def test_build_port_bindings_with_nonmatching_internal_ports(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000:1000", "127.0.0.1:2000:2000"])
        self.assertEqual(port_bindings["1000"], [("127.0.0.1", "1000")])
        self.assertEqual(port_bindings["2000"], [("127.0.0.1", "2000")])

    def test_build_port_bindings_with_port_range(self):
        port_bindings = build_port_bindings(["127.0.0.1:1000-1001:1000-1001"])
        self.assertEqual(port_bindings["1000"], [("127.0.0.1", "1000")])
        self.assertEqual(port_bindings["1001"], [("127.0.0.1", "1001")])

    def test_build_port_bindings_with_matching_internal_port_ranges(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000-1001:1000-1001", "127.0.0.1:2000-2001:1000-1001"])
        self.assertEqual(port_bindings["1000"],
                         [("127.0.0.1", "1000"), ("127.0.0.1", "2000")])
        self.assertEqual(port_bindings["1001"],
                         [("127.0.0.1", "1001"), ("127.0.0.1", "2001")])

    def test_build_port_bindings_with_nonmatching_internal_port_ranges(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000:1000", "127.0.0.1:2000:2000"])
        self.assertEqual(port_bindings["1000"], [("127.0.0.1", "1000")])
        self.assertEqual(port_bindings["2000"], [("127.0.0.1", "2000")])


def convert_paths(collection):
    if not IS_WINDOWS_PLATFORM:
        return collection
    return set(map(lambda x: x.replace('/', '\\'), collection))


class ExcludePathsTest(base.BaseTestCase):
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
        'foo/Dockerfile3',
    ]

    all_paths = set(dirs + files)

    def setUp(self):
        self.base = make_tree(self.dirs, self.files)

    def tearDown(self):
        shutil.rmtree(self.base)

    def exclude(self, patterns, dockerfile=None):
        return set(exclude_paths(self.base, patterns, dockerfile=dockerfile))

    def test_no_excludes(self):
        assert self.exclude(['']) == convert_paths(self.all_paths)

    def test_no_dupes(self):
        paths = exclude_paths(self.base, ['!a.py'])
        assert sorted(paths) == sorted(set(paths))

    def test_wildcard_exclude(self):
        assert self.exclude(['*']) == set(['Dockerfile', '.dockerignore'])

    def test_exclude_dockerfile_dockerignore(self):
        """
        Even if the .dockerignore file explicitly says to exclude
        Dockerfile and/or .dockerignore, don't exclude them from
        the actual tar file.
        """
        assert self.exclude(['Dockerfile', '.dockerignore']) == convert_paths(
            self.all_paths
        )

    def test_exclude_custom_dockerfile(self):
        """
        If we're using a custom Dockerfile, make sure that's not
        excluded.
        """
        assert self.exclude(['*'], dockerfile='Dockerfile.alt') == \
            set(['Dockerfile.alt', '.dockerignore'])

        assert self.exclude(['*'], dockerfile='foo/Dockerfile3') == \
            set(['foo/Dockerfile3', '.dockerignore'])

    def test_exclude_dockerfile_child(self):
        includes = self.exclude(['foo/'], dockerfile='foo/Dockerfile3')
        assert 'foo/Dockerfile3' in includes
        assert 'foo/a.py' not in includes

    def test_single_filename(self):
        assert self.exclude(['a.py']) == convert_paths(
            self.all_paths - set(['a.py'])
        )

    def test_single_filename_leading_dot_slash(self):
        assert self.exclude(['./a.py']) == convert_paths(
            self.all_paths - set(['a.py'])
        )

    # As odd as it sounds, a filename pattern with a trailing slash on the
    # end *will* result in that file being excluded.
    def test_single_filename_trailing_slash(self):
        assert self.exclude(['a.py/']) == convert_paths(
            self.all_paths - set(['a.py'])
        )

    def test_wildcard_filename_start(self):
        assert self.exclude(['*.py']) == convert_paths(
            self.all_paths - set(['a.py', 'b.py', 'cde.py'])
        )

    def test_wildcard_with_exception(self):
        assert self.exclude(['*.py', '!b.py']) == convert_paths(
            self.all_paths - set(['a.py', 'cde.py'])
        )

    def test_wildcard_with_wildcard_exception(self):
        assert self.exclude(['*.*', '!*.go']) == convert_paths(
            self.all_paths - set([
                'a.py', 'b.py', 'cde.py', 'Dockerfile.alt',
            ])
        )

    def test_wildcard_filename_end(self):
        assert self.exclude(['a.*']) == convert_paths(
            self.all_paths - set(['a.py', 'a.go'])
        )

    def test_question_mark(self):
        assert self.exclude(['?.py']) == convert_paths(
            self.all_paths - set(['a.py', 'b.py'])
        )

    def test_single_subdir_single_filename(self):
        assert self.exclude(['foo/a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py'])
        )

    def test_single_subdir_with_path_traversal(self):
        assert self.exclude(['foo/whoops/../a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py'])
        )

    def test_single_subdir_wildcard_filename(self):
        assert self.exclude(['foo/*.py']) == convert_paths(
            self.all_paths - set(['foo/a.py', 'foo/b.py'])
        )

    def test_wildcard_subdir_single_filename(self):
        assert self.exclude(['*/a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py', 'bar/a.py'])
        )

    def test_wildcard_subdir_wildcard_filename(self):
        assert self.exclude(['*/*.py']) == convert_paths(
            self.all_paths - set(['foo/a.py', 'foo/b.py', 'bar/a.py'])
        )

    def test_directory(self):
        assert self.exclude(['foo']) == convert_paths(
            self.all_paths - set([
                'foo', 'foo/a.py', 'foo/b.py', 'foo/bar', 'foo/bar/a.py',
                'foo/Dockerfile3'
            ])
        )

    def test_directory_with_trailing_slash(self):
        assert self.exclude(['foo']) == convert_paths(
            self.all_paths - set([
                'foo', 'foo/a.py', 'foo/b.py',
                'foo/bar', 'foo/bar/a.py', 'foo/Dockerfile3'
            ])
        )

    def test_directory_with_single_exception(self):
        assert self.exclude(['foo', '!foo/bar/a.py']) == convert_paths(
            self.all_paths - set([
                'foo/a.py', 'foo/b.py', 'foo', 'foo/bar',
                'foo/Dockerfile3'
            ])
        )

    def test_directory_with_subdir_exception(self):
        assert self.exclude(['foo', '!foo/bar']) == convert_paths(
            self.all_paths - set([
                'foo/a.py', 'foo/b.py', 'foo', 'foo/Dockerfile3'
            ])
        )

    def test_directory_with_wildcard_exception(self):
        assert self.exclude(['foo', '!foo/*.py']) == convert_paths(
            self.all_paths - set([
                'foo/bar', 'foo/bar/a.py', 'foo', 'foo/Dockerfile3'
            ])
        )

    def test_subdirectory(self):
        assert self.exclude(['foo/bar']) == convert_paths(
            self.all_paths - set(['foo/bar', 'foo/bar/a.py'])
        )


class TarTest(base.Cleanup, base.BaseTestCase):
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

        with tar(base, exclude=exclude) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == sorted(expected_names)

    def test_tar_with_empty_directory(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            self.assertEqual(sorted(tar_data.getnames()), ['bar', 'foo'])

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_file_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        with open(os.path.join(base, 'foo'), 'w') as f:
            f.write("content")
        os.makedirs(os.path.join(base, 'bar'))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            self.assertEqual(
                sorted(tar_data.getnames()), ['bar', 'bar/foo', 'foo']
            )

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_directory_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            self.assertEqual(
                sorted(tar_data.getnames()), ['bar', 'bar/foo', 'foo']
            )


class FormatEnvironmentTest(base.BaseTestCase):
    def test_format_env_binary_unicode_value(self):
        env_dict = {
            'ARTIST_NAME': b'\xec\x86\xa1\xec\xa7\x80\xec\x9d\x80'
        }
        assert format_environment(env_dict) == [u'ARTIST_NAME=송지은']

    def test_format_env_no_value(self):
        env_dict = {
            'FOO': None,
            'BAR': '',
        }
        assert sorted(format_environment(env_dict)) == ['BAR=', 'FOO']
