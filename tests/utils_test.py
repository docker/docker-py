import unittest

from docker.errors import DockerException
from docker.utils import parse_repository_tag, parse_host


class UtilsTest(unittest.TestCase):
    longMessage = True

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

if __name__ == '__main__':
    unittest.main()
