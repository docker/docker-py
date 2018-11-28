import paramiko
import requests.adapters
import six

from .. import constants

if six.PY3:
    import http.client as httplib
else:
    import httplib

try:
    import requests.packages.urllib3 as urllib3
except ImportError:
    import urllib3

RecentlyUsedContainer = urllib3._collections.RecentlyUsedContainer


class SSHConnection(httplib.HTTPConnection, object):
    def __init__(self, ssh_transport, timeout=60):
        super(SSHConnection, self).__init__(
            'localhost', timeout=timeout
        )
        self.ssh_transport = ssh_transport
        self.timeout = timeout

    def connect(self):
        sock = self.ssh_transport.open_session()
        sock.settimeout(self.timeout)
        sock.exec_command('docker system dial-stdio')
        self.sock = sock


class SSHConnectionPool(urllib3.connectionpool.HTTPConnectionPool):
    scheme = 'ssh'

    def __init__(self, ssh_client, timeout=60, maxsize=10):
        super(SSHConnectionPool, self).__init__(
            'localhost', timeout=timeout, maxsize=maxsize
        )
        self.ssh_transport = ssh_client.get_transport()
        self.timeout = timeout

    def _new_conn(self):
        return SSHConnection(self.ssh_transport, self.timeout)

    # When re-using connections, urllib3 calls fileno() on our
    # SSH channel instance, quickly overloading our fd limit. To avoid this,
    # we override _get_conn
    def _get_conn(self, timeout):
        conn = None
        try:
            conn = self.pool.get(block=self.block, timeout=timeout)

        except AttributeError:  # self.pool is None
            raise urllib3.exceptions.ClosedPoolError(self, "Pool is closed.")

        except six.moves.queue.Empty:
            if self.block:
                raise urllib3.exceptions.EmptyPoolError(
                    self,
                    "Pool reached maximum size and no more "
                    "connections are allowed."
                )
            pass  # Oh well, we'll create a new connection then

        return conn or self._new_conn()


class SSHAdapter(requests.adapters.HTTPAdapter):

    __attrs__ = requests.adapters.HTTPAdapter.__attrs__ + [
        'pools', 'timeout', 'ssh_client',
    ]

    def __init__(self, base_url, timeout=60,
                 pool_connections=constants.DEFAULT_NUM_POOLS):
        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()

        parsed = six.moves.urllib_parse.urlparse(base_url)
        self.ssh_client.connect(
            parsed.hostname, parsed.port, parsed.username,
        )
        self.timeout = timeout
        self.pools = RecentlyUsedContainer(
            pool_connections, dispose_func=lambda p: p.close()
        )
        super(SSHAdapter, self).__init__()

    def get_connection(self, url, proxies=None):
        with self.pools.lock:
            pool = self.pools.get(url)
            if pool:
                return pool

            pool = SSHConnectionPool(
                self.ssh_client, self.timeout
            )
            self.pools[url] = pool

        return pool

    def close(self):
        self.pools.clear()
        self.ssh_client.close()
