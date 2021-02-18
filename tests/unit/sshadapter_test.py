import unittest
import docker
from docker.transport.sshconn import SSHSocket

class SSHAdapterTest(unittest.TestCase):
    def test_ssh_hostname_prefix_trim(self):
        conn = docker.transport.SSHHTTPAdapter(base_url="ssh://user@hostname:1234", shell_out=True)
        assert conn.ssh_host == "user@hostname:1234"

    def test_ssh_parse_url(self):
        c = SSHSocket(host="user@hostname:1234")
        assert c.host == "hostname"
        assert c.port == "1234"
        assert c.user == "user"

    def test_ssh_parse_hostname_only(self):
        c = SSHSocket(host="hostname")
        assert c.host == "hostname"
        assert c.port == None
        assert c.user == None

    def test_ssh_parse_user_and_hostname(self):
        c = SSHSocket(host="user@hostname")
        assert c.host == "hostname"
        assert c.port == None
        assert c.user == "user"

    def test_ssh_parse_hostname_and_port(self):
        c = SSHSocket(host="hostname:22")
        assert c.host == "hostname"
        assert c.port == "22"
        assert c.user == None