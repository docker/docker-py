import unittest
import docker
from docker.transport.sshconn import SSHSocket


class SSHAdapterTest(unittest.TestCase):
    @staticmethod
    def test_ssh_hostname_prefix_trim():
        conn = docker.transport.SSHHTTPAdapter(
            base_url="ssh://user@hostname:1234", shell_out=True)
        assert conn.ssh_host == "user@hostname:1234"

    @staticmethod
    def test_ssh_parse_url():
        c = SSHSocket(host="user@hostname:1234")
        assert c.host == "hostname"
        assert c.port == "1234"
        assert c.user == "user"

    @staticmethod
    def test_ssh_parse_hostname_only():
        c = SSHSocket(host="hostname")
        assert c.host == "hostname"
        assert c.port is None
        assert c.user is None

    @staticmethod
    def test_ssh_parse_user_and_hostname():
        c = SSHSocket(host="user@hostname")
        assert c.host == "hostname"
        assert c.port is None
        assert c.user == "user"

    @staticmethod
    def test_ssh_parse_hostname_and_port():
        c = SSHSocket(host="hostname:22")
        assert c.host == "hostname"
        assert c.port == "22"
        assert c.user is None
