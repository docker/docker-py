import os
import os.path
import unittest

from docker.client import Client
from docker.errors import DockerException
from docker.utils import (
    parse_repository_tag, parse_host, convert_filters, kwargs_from_env,
    create_host_config
)
from docker.auth import resolve_authconfig


class UtilsTest(unittest.TestCase):
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

    def test_create_host_config(self):
        empty_config = create_host_config()
        self.assertEqual(empty_config, {})

    def test_resolve_authconfig(self):
        auth_config = {
            'https://index.docker.io/v1/': {'auth': 'indexuser'},
            'http://my.registry.net/v1/': {'auth': 'privateuser'}
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


if __name__ == '__main__':
    unittest.main()
