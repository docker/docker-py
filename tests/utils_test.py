import os
import os.path
import unittest

from docker.client import Client
from docker.errors import DockerException
from docker.utils import (
    parse_repository_tag, parse_host, convert_filters, kwargs_from_env,
    create_host_config, Ulimit, LogConfig
)
from docker.utils.ports import build_port_bindings, split_port
from docker.auth import resolve_authconfig

import base


class UtilsTest(base.BaseTestCase):
    longMessage = True

    def setUp(self):
        self.os_environ = os.environ.copy()

    def tearDown(self):
        os.environ = self.os_environ

    def test_parse_repository_tag(self):
        self.assertEqual(parse_repository_tag("root"),
                         ("root", None))
        self.assertEqual(parse_repository_tag("root:tag"),
                         ("root", "tag"))
        self.assertEqual(parse_repository_tag("user/repo"),
                         ("user/repo", None))
        self.assertEqual(parse_repository_tag("user/repo:tag"),
                         ("user/repo", "tag"))
        self.assertEqual(parse_repository_tag("url:5000/repo"),
                         ("url:5000/repo", None))
        self.assertEqual(parse_repository_tag("url:5000/repo:tag"),
                         ("url:5000/repo", "tag"))

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
            '': 'http+unix://var/run/docker.sock',
            None: 'http+unix://var/run/docker.sock',
            'unix:///var/run/docker.sock': 'http+unix:///var/run/docker.sock',
            'unix://': 'http+unix://var/run/docker.sock'
        }

        for host in invalid_hosts:
            try:
                parsed = parse_host(host)
                self.fail('Expected to fail but success: %s -> %s' % (
                    host, parsed
                ))
            except DockerException:
                pass

        for host, expected in valid_hosts.items():
            self.assertEqual(parse_host(host), expected, msg=host)

    def test_kwargs_from_env(self):
        os.environ.update(DOCKER_HOST='tcp://192.168.59.103:2376',
                          DOCKER_CERT_PATH=os.path.join(
                              os.path.dirname(__file__),
                              'testdata/certs'),
                          DOCKER_TLS_VERIFY='1')
        kwargs = kwargs_from_env(assert_hostname=False)
        self.assertEqual('https://192.168.59.103:2376', kwargs['base_url'])
        self.assertTrue('ca.pem' in kwargs['tls'].verify)
        self.assertTrue('cert.pem' in kwargs['tls'].cert[0])
        self.assertTrue('key.pem' in kwargs['tls'].cert[1])
        self.assertEqual(False, kwargs['tls'].assert_hostname)
        try:
            client = Client(**kwargs)
            self.assertEqual(kwargs['base_url'], client.base_url)
            self.assertEqual(kwargs['tls'].verify, client.verify)
            self.assertEqual(kwargs['tls'].cert, client.cert)
        except TypeError as e:
            self.fail(e)

    def test_convert_filters(self):
        tests = [
            ({'dangling': True}, '{"dangling": ["true"]}'),
            ({'dangling': "true"}, '{"dangling": ["true"]}'),
            ({'exited': 0}, '{"exited": [0]}'),
            ({'exited': [0, 1]}, '{"exited": [0, 1]}'),
        ]

        for filters, expected in tests:
            self.assertEqual(convert_filters(filters), expected)

    def test_create_empty_host_config(self):
        empty_config = create_host_config()
        self.assertEqual(empty_config, {})

    def test_create_host_config_dict_ulimit(self):
        ulimit_dct = {'name': 'nofile', 'soft': 8096}
        config = create_host_config(ulimits=[ulimit_dct])
        self.assertIn('Ulimits', config)
        self.assertEqual(len(config['Ulimits']), 1)
        ulimit_obj = config['Ulimits'][0]
        self.assertTrue(isinstance(ulimit_obj, Ulimit))
        self.assertEqual(ulimit_obj.name, ulimit_dct['name'])
        self.assertEqual(ulimit_obj.soft, ulimit_dct['soft'])
        self.assertEqual(ulimit_obj['Soft'], ulimit_obj.soft)

    def test_create_host_config_dict_ulimit_capitals(self):
        ulimit_dct = {'Name': 'nofile', 'Soft': 8096, 'Hard': 8096 * 4}
        config = create_host_config(ulimits=[ulimit_dct])
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
        config = create_host_config(ulimits=[ulimit_dct])
        self.assertIn('Ulimits', config)
        self.assertEqual(len(config['Ulimits']), 1)
        ulimit_obj = config['Ulimits'][0]
        self.assertTrue(isinstance(ulimit_obj, Ulimit))
        self.assertEqual(ulimit_obj, ulimit_dct)

    def test_ulimit_invalid_type(self):
        self.assertRaises(ValueError, lambda: Ulimit(name=None))
        self.assertRaises(ValueError, lambda: Ulimit(name='hello', soft='123'))
        self.assertRaises(ValueError, lambda: Ulimit(name='hello', hard='456'))

    def test_create_host_config_dict_logconfig(self):
        dct = {'type': LogConfig.types.SYSLOG, 'config': {'key1': 'val1'}}
        config = create_host_config(log_config=dct)
        self.assertIn('LogConfig', config)
        self.assertTrue(isinstance(config['LogConfig'], LogConfig))
        self.assertEqual(dct['type'], config['LogConfig'].type)

    def test_create_host_config_obj_logconfig(self):
        obj = LogConfig(type=LogConfig.types.SYSLOG, config={'key1': 'val1'})
        config = create_host_config(log_config=obj)
        self.assertIn('LogConfig', config)
        self.assertTrue(isinstance(config['LogConfig'], LogConfig))
        self.assertEqual(obj, config['LogConfig'])

    def test_logconfig_invalid_type(self):
        self.assertRaises(ValueError, lambda: LogConfig(type='xxx', config={}))
        self.assertRaises(ValueError, lambda: LogConfig(
            type=LogConfig.types.JSON, config='helloworld'
        ))

    def test_resolve_authconfig(self):
        auth_config = {
            'https://index.docker.io/v1/': {'auth': 'indexuser'},
            'my.registry.net': {'auth': 'privateuser'},
            'http://legacy.registry.url/v1/': {'auth': 'legacyauth'}
        }
        # hostname only
        self.assertEqual(
            resolve_authconfig(auth_config, 'my.registry.net'),
            {'auth': 'privateuser'}
        )
        # no protocol
        self.assertEqual(
            resolve_authconfig(auth_config, 'my.registry.net/v1/'),
            {'auth': 'privateuser'}
        )
        # no path
        self.assertEqual(
            resolve_authconfig(auth_config, 'http://my.registry.net'),
            {'auth': 'privateuser'}
        )
        # no path, trailing slash
        self.assertEqual(
            resolve_authconfig(auth_config, 'http://my.registry.net/'),
            {'auth': 'privateuser'}
        )
        # no path, wrong secure protocol
        self.assertEqual(
            resolve_authconfig(auth_config, 'https://my.registry.net'),
            {'auth': 'privateuser'}
        )
        # no path, wrong insecure protocol
        self.assertEqual(
            resolve_authconfig(auth_config, 'http://index.docker.io'),
            {'auth': 'indexuser'}
        )
        # with path, wrong protocol
        self.assertEqual(
            resolve_authconfig(auth_config, 'https://my.registry.net/v1/'),
            {'auth': 'privateuser'}
        )
        # default registry
        self.assertEqual(
            resolve_authconfig(auth_config), {'auth': 'indexuser'}
        )
        # default registry (explicit None)
        self.assertEqual(
            resolve_authconfig(auth_config, None), {'auth': 'indexuser'}
        )
        # fully explicit
        self.assertEqual(
            resolve_authconfig(auth_config, 'http://my.registry.net/v1/'),
            {'auth': 'privateuser'}
        )
        # legacy entry in config
        self.assertEqual(
            resolve_authconfig(auth_config, 'legacy.registry.url'),
            {'auth': 'legacyauth'}
        )
        # no matching entry
        self.assertTrue(
            resolve_authconfig(auth_config, 'does.not.exist') is None
        )

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

if __name__ == '__main__':
    unittest.main()
