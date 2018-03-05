# -*- coding: utf-8 -*-

import base64
import json
import os
import os.path
import shutil
import socket
import sys
import tarfile
import tempfile
import unittest

import pytest
import six

from docker.api.client import APIClient
from docker.constants import IS_WINDOWS_PLATFORM
from docker.errors import DockerException
from docker.utils import (
    parse_repository_tag, parse_host, convert_filters, kwargs_from_env,
    parse_bytes, parse_env_file, exclude_paths, convert_volume_binds,
    decode_json_header, tar, split_command, parse_devices, update_headers,
)

from docker.utils.ports import build_port_bindings, split_port
from docker.utils.utils import format_environment

from ..helpers import make_tree


TEST_CERT_DIR = os.path.join(
    os.path.dirname(__file__),
    'testdata/certs',
)


class DecoratorsTest(unittest.TestCase):
    def test_update_headers(self):
        sample_headers = {
            'X-Docker-Locale': 'en-US',
        }

        def f(self, headers=None):
            return headers

        client = APIClient()
        client._general_configs = {}

        g = update_headers(f)
        assert g(client, headers=None) is None
        assert g(client, headers={}) == {}
        assert g(client, headers={'Content-type': 'application/json'}) == {
            'Content-type': 'application/json',
        }

        client._general_configs = {
            'HttpHeaders': sample_headers
        }

        assert g(client, headers=None) == sample_headers
        assert g(client, headers={}) == sample_headers
        assert g(client, headers={'Content-type': 'application/json'}) == {
            'Content-type': 'application/json',
            'X-Docker-Locale': 'en-US',
        }


class KwargsFromEnvTest(unittest.TestCase):
    def setUp(self):
        self.os_environ = os.environ.copy()

    def tearDown(self):
        os.environ = self.os_environ

    def test_kwargs_from_env_empty(self):
        os.environ.update(DOCKER_HOST='',
                          DOCKER_CERT_PATH='')
        os.environ.pop('DOCKER_TLS_VERIFY', None)

        kwargs = kwargs_from_env()
        assert kwargs.get('base_url') is None
        assert kwargs.get('tls') is None

    def test_kwargs_from_env_tls(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='1')
        kwargs = kwargs_from_env(assert_hostname=False)
        assert 'https://192.168.59.103:2376' == kwargs['base_url']
        assert 'ca.pem' in kwargs['tls'].ca_cert
        assert 'cert.pem' in kwargs['tls'].cert[0]
        assert 'key.pem' in kwargs['tls'].cert[1]
        assert kwargs['tls'].assert_hostname is False
        assert kwargs['tls'].verify
        try:
            client = APIClient(**kwargs)
            assert kwargs['base_url'] == client.base_url
            assert kwargs['tls'].ca_cert == client.verify
            assert kwargs['tls'].cert == client.cert
        except TypeError as e:
            self.fail(e)

    def test_kwargs_from_env_tls_verify_false(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=TEST_CERT_DIR,
                          DOCKER_TLS_VERIFY='')
        kwargs = kwargs_from_env(assert_hostname=True)
        assert 'https://192.168.59.103:2376' == kwargs['base_url']
        assert 'ca.pem' in kwargs['tls'].ca_cert
        assert 'cert.pem' in kwargs['tls'].cert[0]
        assert 'key.pem' in kwargs['tls'].cert[1]
        assert kwargs['tls'].assert_hostname is True
        assert kwargs['tls'].verify is False
        try:
            client = APIClient(**kwargs)
            assert kwargs['base_url'] == client.base_url
            assert kwargs['tls'].cert == client.cert
            assert not kwargs['tls'].verify
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
        assert 'tcp://192.168.59.103:2376' == kwargs['base_url']

    def test_kwargs_from_env_no_cert_path(self):
        try:
            temp_dir = tempfile.mkdtemp()
            cert_dir = os.path.join(temp_dir, '.docker')
            shutil.copytree(TEST_CERT_DIR, cert_dir)

            os.environ.update(HOME=temp_dir,
                              DOCKER_CERT_PATH='',
                              DOCKER_TLS_VERIFY='1')

            kwargs = kwargs_from_env()
            assert kwargs['tls'].verify
            assert cert_dir in kwargs['tls'].ca_cert
            assert cert_dir in kwargs['tls'].cert[0]
            assert cert_dir in kwargs['tls'].cert[1]
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


class ConverVolumeBindsTest(unittest.TestCase):
    def test_convert_volume_binds_empty(self):
        assert convert_volume_binds({}) == []
        assert convert_volume_binds([]) == []

    def test_convert_volume_binds_list(self):
        data = ['/a:/a:ro', '/b:/c:z']
        assert convert_volume_binds(data) == data

    def test_convert_volume_binds_complete(self):
        data = {
            '/mnt/vol1': {
                'bind': '/data',
                'mode': 'ro'
            }
        }
        assert convert_volume_binds(data) == ['/mnt/vol1:/data:ro']

    def test_convert_volume_binds_compact(self):
        data = {
            '/mnt/vol1': '/data'
        }
        assert convert_volume_binds(data) == ['/mnt/vol1:/data:rw']

    def test_convert_volume_binds_no_mode(self):
        data = {
            '/mnt/vol1': {
                'bind': '/data'
            }
        }
        assert convert_volume_binds(data) == ['/mnt/vol1:/data:rw']

    def test_convert_volume_binds_unicode_bytes_input(self):
        expected = [u'/mnt/지연:/unicode/박:rw']

        data = {
            u'/mnt/지연'.encode('utf-8'): {
                'bind': u'/unicode/박'.encode('utf-8'),
                'mode': 'rw'
            }
        }
        assert convert_volume_binds(data) == expected

    def test_convert_volume_binds_unicode_unicode_input(self):
        expected = [u'/mnt/지연:/unicode/박:rw']

        data = {
            u'/mnt/지연': {
                'bind': u'/unicode/박',
                'mode': 'rw'
            }
        }
        assert convert_volume_binds(data) == expected


class ParseEnvFileTest(unittest.TestCase):
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
        assert get_parse_env_file == {'USER': 'jdoe', 'PASS': 'secret'}
        os.unlink(env_file)

    def test_parse_env_file_with_equals_character(self):
        env_file = self.generate_tempfile(
            file_content='USER=jdoe\nPASS=sec==ret')
        get_parse_env_file = parse_env_file(env_file)
        assert get_parse_env_file == {'USER': 'jdoe', 'PASS': 'sec==ret'}
        os.unlink(env_file)

    def test_parse_env_file_commented_line(self):
        env_file = self.generate_tempfile(
            file_content='USER=jdoe\n#PASS=secret')
        get_parse_env_file = parse_env_file(env_file)
        assert get_parse_env_file == {'USER': 'jdoe'}
        os.unlink(env_file)

    def test_parse_env_file_newline(self):
        env_file = self.generate_tempfile(
            file_content='\nUSER=jdoe\n\n\nPASS=secret')
        get_parse_env_file = parse_env_file(env_file)
        assert get_parse_env_file == {'USER': 'jdoe', 'PASS': 'secret'}
        os.unlink(env_file)

    def test_parse_env_file_invalid_line(self):
        env_file = self.generate_tempfile(
            file_content='USER jdoe')
        with pytest.raises(DockerException):
            parse_env_file(env_file)
        os.unlink(env_file)


class ParseHostTest(unittest.TestCase):
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


class ParseRepositoryTagTest(unittest.TestCase):
    sha = 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855'

    def test_index_image_no_tag(self):
        assert parse_repository_tag("root") == ("root", None)

    def test_index_image_tag(self):
        assert parse_repository_tag("root:tag") == ("root", "tag")

    def test_index_user_image_no_tag(self):
        assert parse_repository_tag("user/repo") == ("user/repo", None)

    def test_index_user_image_tag(self):
        assert parse_repository_tag("user/repo:tag") == ("user/repo", "tag")

    def test_private_reg_image_no_tag(self):
        assert parse_repository_tag("url:5000/repo") == ("url:5000/repo", None)

    def test_private_reg_image_tag(self):
        assert parse_repository_tag("url:5000/repo:tag") == (
            "url:5000/repo", "tag"
        )

    def test_index_image_sha(self):
        assert parse_repository_tag("root@sha256:{0}".format(self.sha)) == (
            "root", "sha256:{0}".format(self.sha)
        )

    def test_private_reg_image_sha(self):
        assert parse_repository_tag(
            "url:5000/repo@sha256:{0}".format(self.sha)
        ) == ("url:5000/repo", "sha256:{0}".format(self.sha))


class ParseDeviceTest(unittest.TestCase):
    def test_dict(self):
        devices = parse_devices([{
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'r'
        }])
        assert devices[0] == {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'r'
        }

    def test_partial_string_definition(self):
        devices = parse_devices(['/dev/sda1'])
        assert devices[0] == {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/sda1',
            'CgroupPermissions': 'rwm'
        }

    def test_permissionless_string_definition(self):
        devices = parse_devices(['/dev/sda1:/dev/mnt1'])
        assert devices[0] == {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'rwm'
        }

    def test_full_string_definition(self):
        devices = parse_devices(['/dev/sda1:/dev/mnt1:r'])
        assert devices[0] == {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'r'
        }

    def test_hybrid_list(self):
        devices = parse_devices([
            '/dev/sda1:/dev/mnt1:rw',
            {
                'PathOnHost': '/dev/sda2',
                'PathInContainer': '/dev/mnt2',
                'CgroupPermissions': 'r'
            }
        ])

        assert devices[0] == {
            'PathOnHost': '/dev/sda1',
            'PathInContainer': '/dev/mnt1',
            'CgroupPermissions': 'rw'
        }
        assert devices[1] == {
            'PathOnHost': '/dev/sda2',
            'PathInContainer': '/dev/mnt2',
            'CgroupPermissions': 'r'
        }


class ParseBytesTest(unittest.TestCase):
    def test_parse_bytes_valid(self):
        assert parse_bytes("512MB") == 536870912
        assert parse_bytes("512M") == 536870912
        assert parse_bytes("512m") == 536870912

    def test_parse_bytes_invalid(self):
        with pytest.raises(DockerException):
            parse_bytes("512MK")
        with pytest.raises(DockerException):
            parse_bytes("512L")
        with pytest.raises(DockerException):
            parse_bytes("127.0.0.1K")

    def test_parse_bytes_float(self):
        with pytest.raises(DockerException):
            parse_bytes("1.5k")

    def test_parse_bytes_maxint(self):
        assert parse_bytes("{0}k".format(sys.maxsize)) == sys.maxsize * 1024


class UtilsTest(unittest.TestCase):
    longMessage = True

    def test_convert_filters(self):
        tests = [
            ({'dangling': True}, '{"dangling": ["true"]}'),
            ({'dangling': "true"}, '{"dangling": ["true"]}'),
            ({'exited': 0}, '{"exited": [0]}'),
            ({'exited': [0, 1]}, '{"exited": [0, 1]}'),
        ]

        for filters, expected in tests:
            assert convert_filters(filters) == expected

    def test_decode_json_header(self):
        obj = {'a': 'b', 'c': 1}
        data = None
        if six.PY3:
            data = base64.urlsafe_b64encode(bytes(json.dumps(obj), 'utf-8'))
        else:
            data = base64.urlsafe_b64encode(json.dumps(obj))
        decoded_data = decode_json_header(data)
        assert obj == decoded_data


class SplitCommandTest(unittest.TestCase):
    def test_split_command_with_unicode(self):
        assert split_command(u'echo μμ') == ['echo', 'μμ']

    @pytest.mark.skipif(six.PY3, reason="shlex doesn't support bytes in py3")
    def test_split_command_with_bytes(self):
        assert split_command('echo μμ') == ['echo', 'μμ']


class PortsTest(unittest.TestCase):
    def test_split_port_with_host_ip(self):
        internal_port, external_port = split_port("127.0.0.1:1000:2000")
        assert internal_port == ["2000"]
        assert external_port == [("127.0.0.1", "1000")]

    def test_split_port_with_protocol(self):
        internal_port, external_port = split_port("127.0.0.1:1000:2000/udp")
        assert internal_port == ["2000/udp"]
        assert external_port == [("127.0.0.1", "1000")]

    def test_split_port_with_host_ip_no_port(self):
        internal_port, external_port = split_port("127.0.0.1::2000")
        assert internal_port == ["2000"]
        assert external_port == [("127.0.0.1", None)]

    def test_split_port_range_with_host_ip_no_port(self):
        internal_port, external_port = split_port("127.0.0.1::2000-2001")
        assert internal_port == ["2000", "2001"]
        assert external_port == [("127.0.0.1", None), ("127.0.0.1", None)]

    def test_split_port_with_host_port(self):
        internal_port, external_port = split_port("1000:2000")
        assert internal_port == ["2000"]
        assert external_port == ["1000"]

    def test_split_port_range_with_host_port(self):
        internal_port, external_port = split_port("1000-1001:2000-2001")
        assert internal_port == ["2000", "2001"]
        assert external_port == ["1000", "1001"]

    def test_split_port_random_port_range_with_host_port(self):
        internal_port, external_port = split_port("1000-1001:2000")
        assert internal_port == ["2000"]
        assert external_port == ["1000-1001"]

    def test_split_port_no_host_port(self):
        internal_port, external_port = split_port("2000")
        assert internal_port == ["2000"]
        assert external_port is None

    def test_split_port_range_no_host_port(self):
        internal_port, external_port = split_port("2000-2001")
        assert internal_port == ["2000", "2001"]
        assert external_port is None

    def test_split_port_range_with_protocol(self):
        internal_port, external_port = split_port(
            "127.0.0.1:1000-1001:2000-2001/udp")
        assert internal_port == ["2000/udp", "2001/udp"]
        assert external_port == [("127.0.0.1", "1000"), ("127.0.0.1", "1001")]

    def test_split_port_with_ipv6_address(self):
        internal_port, external_port = split_port(
            "2001:abcd:ef00::2:1000:2000")
        assert internal_port == ["2000"]
        assert external_port == [("2001:abcd:ef00::2", "1000")]

    def test_split_port_invalid(self):
        with pytest.raises(ValueError):
            split_port("0.0.0.0:1000:2000:tcp")

    def test_non_matching_length_port_ranges(self):
        with pytest.raises(ValueError):
            split_port("0.0.0.0:1000-1010:2000-2002/tcp")

    def test_port_and_range_invalid(self):
        with pytest.raises(ValueError):
            split_port("0.0.0.0:1000:2000-2002/tcp")

    def test_port_only_with_colon(self):
        with pytest.raises(ValueError):
            split_port(":80")

    def test_host_only_with_colon(self):
        with pytest.raises(ValueError):
            split_port("localhost:")

    def test_with_no_container_port(self):
        with pytest.raises(ValueError):
            split_port("localhost:80:")

    def test_split_port_empty_string(self):
        with pytest.raises(ValueError):
            split_port("")

    def test_split_port_non_string(self):
        assert split_port(1243) == (['1243'], None)

    def test_build_port_bindings_with_one_port(self):
        port_bindings = build_port_bindings(["127.0.0.1:1000:1000"])
        assert port_bindings["1000"] == [("127.0.0.1", "1000")]

    def test_build_port_bindings_with_matching_internal_ports(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000:1000", "127.0.0.1:2000:1000"])
        assert port_bindings["1000"] == [
            ("127.0.0.1", "1000"), ("127.0.0.1", "2000")
        ]

    def test_build_port_bindings_with_nonmatching_internal_ports(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000:1000", "127.0.0.1:2000:2000"])
        assert port_bindings["1000"] == [("127.0.0.1", "1000")]
        assert port_bindings["2000"] == [("127.0.0.1", "2000")]

    def test_build_port_bindings_with_port_range(self):
        port_bindings = build_port_bindings(["127.0.0.1:1000-1001:1000-1001"])
        assert port_bindings["1000"] == [("127.0.0.1", "1000")]
        assert port_bindings["1001"] == [("127.0.0.1", "1001")]

    def test_build_port_bindings_with_matching_internal_port_ranges(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000-1001:1000-1001", "127.0.0.1:2000-2001:1000-1001"])
        assert port_bindings["1000"] == [
            ("127.0.0.1", "1000"), ("127.0.0.1", "2000")
        ]
        assert port_bindings["1001"] == [
            ("127.0.0.1", "1001"), ("127.0.0.1", "2001")
        ]

    def test_build_port_bindings_with_nonmatching_internal_port_ranges(self):
        port_bindings = build_port_bindings(
            ["127.0.0.1:1000:1000", "127.0.0.1:2000:2000"])
        assert port_bindings["1000"] == [("127.0.0.1", "1000")]
        assert port_bindings["2000"] == [("127.0.0.1", "2000")]


def convert_paths(collection):
    return set(map(convert_path, collection))


def convert_path(path):
    return path.replace('/', os.path.sep)


class ExcludePathsTest(unittest.TestCase):
    dirs = [
        'foo',
        'foo/bar',
        'bar',
        'target',
        'target/subdir',
        'subdir',
        'subdir/target',
        'subdir/target/subdir',
        'subdir/subdir2',
        'subdir/subdir2/target',
        'subdir/subdir2/target/subdir'
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
        'target/file.txt',
        'target/subdir/file.txt',
        'subdir/file.txt',
        'subdir/target/file.txt',
        'subdir/target/subdir/file.txt',
        'subdir/subdir2/file.txt',
        'subdir/subdir2/target/file.txt',
        'subdir/subdir2/target/subdir/file.txt',
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
        assert self.exclude(['*'], dockerfile='Dockerfile.alt') == set(
            ['Dockerfile.alt', '.dockerignore']
        )

        assert self.exclude(
            ['*'], dockerfile='foo/Dockerfile3'
        ) == convert_paths(set(['foo/Dockerfile3', '.dockerignore']))

    def test_exclude_dockerfile_child(self):
        includes = self.exclude(['foo/'], dockerfile='foo/Dockerfile3')
        assert convert_path('foo/Dockerfile3') in includes
        assert convert_path('foo/a.py') not in includes

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

    def test_single_subdir_single_filename_leading_slash(self):
        assert self.exclude(['/foo/a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py'])
        )

    def test_exclude_include_absolute_path(self):
        base = make_tree([], ['a.py', 'b.py'])
        assert exclude_paths(
            base,
            ['/*', '!/*.py']
        ) == set(['a.py', 'b.py'])

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

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Backslash patterns only on Windows'
    )
    def test_directory_with_subdir_exception_win32_pathsep(self):
        assert self.exclude(['foo', '!foo\\bar']) == convert_paths(
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

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Backslash patterns only on Windows'
    )
    def test_subdirectory_win32_pathsep(self):
        assert self.exclude(['foo\\bar']) == convert_paths(
            self.all_paths - set(['foo/bar', 'foo/bar/a.py'])
        )

    def test_double_wildcard(self):
        assert self.exclude(['**/a.py']) == convert_paths(
            self.all_paths - set(
                ['a.py', 'foo/a.py', 'foo/bar/a.py', 'bar/a.py']
            )
        )

        assert self.exclude(['foo/**/bar']) == convert_paths(
            self.all_paths - set(['foo/bar', 'foo/bar/a.py'])
        )

    def test_single_and_double_wildcard(self):
        assert self.exclude(['**/target/*/*']) == convert_paths(
            self.all_paths - set(
                ['target/subdir/file.txt',
                 'subdir/target/subdir/file.txt',
                 'subdir/subdir2/target/subdir/file.txt']
            )
        )

    def test_trailing_double_wildcard(self):
        assert self.exclude(['subdir/**']) == convert_paths(
            self.all_paths - set(
                ['subdir/file.txt',
                 'subdir/target/file.txt',
                 'subdir/target/subdir/file.txt',
                 'subdir/subdir2/file.txt',
                 'subdir/subdir2/target/file.txt',
                 'subdir/subdir2/target/subdir/file.txt',
                 'subdir/target',
                 'subdir/target/subdir',
                 'subdir/subdir2',
                 'subdir/subdir2/target',
                 'subdir/subdir2/target/subdir']
            )
        )

    def test_include_wildcard(self):
        base = make_tree(['a'], ['a/b.py'])
        assert exclude_paths(
            base,
            ['*', '!*/b.py']
        ) == convert_paths(['a/b.py'])

    def test_last_line_precedence(self):
        base = make_tree(
            [],
            ['garbage.md',
             'thrash.md',
             'README.md',
             'README-bis.md',
             'README-secret.md'])
        assert exclude_paths(
            base,
            ['*.md', '!README*.md', 'README-secret.md']
        ) == set(['README.md', 'README-bis.md'])

    def test_parent_directory(self):
        base = make_tree(
            [],
            ['a.py',
             'b.py',
             'c.py'])
        # Dockerignore reference stipulates that absolute paths are
        # equivalent to relative paths, hence /../foo should be
        # equivalent to ../foo. It also stipulates that paths are run
        # through Go's filepath.Clean, which explicitely "replace
        # "/.."  by "/" at the beginning of a path".
        assert exclude_paths(
            base,
            ['../a.py', '/../b.py']
        ) == set(['c.py'])


class TarTest(unittest.TestCase):
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
            assert sorted(tar_data.getnames()) == ['bar', 'foo']

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM or os.geteuid() == 0,
        reason='root user always has access ; no chmod on Windows'
    )
    def test_tar_with_inaccessible_file(self):
        base = tempfile.mkdtemp()
        full_path = os.path.join(base, 'foo')
        self.addCleanup(shutil.rmtree, base)
        with open(full_path, 'w') as f:
            f.write('content')
        os.chmod(full_path, 0o222)
        with pytest.raises(IOError) as ei:
            tar(base)

        assert 'Can not read file in context: {}'.format(full_path) in (
            ei.exconly()
        )

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
            assert sorted(tar_data.getnames()) == ['bar', 'bar/foo', 'foo']

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_directory_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'bar/foo', 'foo']

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_broken_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))

        os.symlink('../baz', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'bar/foo', 'foo']

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No UNIX sockets on Win32')
    def test_tar_socket_file(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        sock = socket.socket(socket.AF_UNIX)
        self.addCleanup(sock.close)
        sock.bind(os.path.join(base, 'test.sock'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'foo']

    def tar_test_negative_mtime_bug(self):
        base = tempfile.mkdtemp()
        filename = os.path.join(base, 'th.txt')
        self.addCleanup(shutil.rmtree, base)
        with open(filename, 'w') as f:
            f.write('Invisible Full Moon')
        os.utime(filename, (12345, -3600.0))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert tar_data.getnames() == ['th.txt']
            assert tar_data.getmember('th.txt').mtime == -3600


class FormatEnvironmentTest(unittest.TestCase):
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
