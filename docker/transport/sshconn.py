import paramiko
import requests.adapters
import six
import logging
import os
import signal
import socket
import subprocess

from docker.transport.basehttpadapter import BaseHTTPAdapter
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


class SSHSocket(socket.socket):
    def __init__(self, host):
        super(SSHSocket, self).__init__(
            socket.AF_INET, socket.SOCK_STREAM)
        self.host = host
        self.port = None
        if ':' in host:
            self.host, self.port = host.split(':')
        self.proc = None

    def connect(self, **kwargs):
        port = '' if not self.port else '-p {}'.format(self.port)
        args = [
            'ssh',
            '-q',
            self.host,
            port,
            'docker system dial-stdio'
        ]
        self.proc = subprocess.Popen(
            ' '.join(args),
            shell=True,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_IGN))

    def _write(self, data):
        if not self.proc or self.proc.stdin.closed:
            raise Exception('SSH subprocess not initiated.'
                            'connect() must be called first.')
        written = self.proc.stdin.write(data)
        self.proc.stdin.flush()
        return written

    def sendall(self, data):
        self._write(data)

    def send(self, data):
        return self._write(data)

    def recv(self, n):
        if not self.proc:
            raise Exception('SSH subprocess not initiated.'
                            'connect() must be called first.')
        return self.proc.stdout.read(n)

    def makefile(self, mode):
        if not self.proc:
            self.connect()
        if six.PY3:
            self.proc.stdout.channel = self

        return self.proc.stdout

    def close(self):
        if not self.proc or self.proc.stdin.closed:
            return
        self.proc.stdin.write(b'\n\n')
        self.proc.stdin.flush()
        self.proc.terminate()


class SSHConnection(httplib.HTTPConnection, object):
    def __init__(self, ssh_transport=None, timeout=60, host=None):
        super(SSHConnection, self).__init__(
            'localhost', timeout=timeout
        )
        self.ssh_transport = ssh_transport
        self.timeout = timeout
        self.ssh_host = host

    def connect(self):
        if self.ssh_transport:
            sock = self.ssh_transport.open_session()
            sock.settimeout(self.timeout)
            sock.exec_command('docker system dial-stdio')
        else:
            sock = SSHSocket(self.ssh_host)
            sock.settimeout(self.timeout)
            sock.connect()

        self.sock = sock


class SSHConnectionPool(urllib3.connectionpool.HTTPConnectionPool):
    scheme = 'ssh'

    def __init__(self, ssh_client=None, timeout=60, maxsize=10, host=None):
        super(SSHConnectionPool, self).__init__(
            'localhost', timeout=timeout, maxsize=maxsize
        )
        self.ssh_transport = None
        self.timeout = timeout
        if ssh_client:
            self.ssh_transport = ssh_client.get_transport()
        self.ssh_host = host
        self.ssh_port = None
        if ':' in host:
            self.ssh_host, self.ssh_port = host.split(':')

    def _new_conn(self):
        return SSHConnection(self.ssh_transport, self.timeout, self.ssh_host)

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


class SSHHTTPAdapter(BaseHTTPAdapter):

    __attrs__ = requests.adapters.HTTPAdapter.__attrs__ + [
        'pools', 'timeout', 'ssh_client', 'ssh_params', 'max_pool_size'
    ]

    def __init__(self, base_url, timeout=60,
                 pool_connections=constants.DEFAULT_NUM_POOLS,
                 max_pool_size=constants.DEFAULT_MAX_POOL_SIZE,
                 shell_out=True):
        self.ssh_client = None
        if not shell_out:
            self._create_paramiko_client(base_url)
            self._connect()

        self.ssh_host = base_url.lstrip('ssh://')
        self.timeout = timeout
        self.max_pool_size = max_pool_size
        self.pools = RecentlyUsedContainer(
            pool_connections, dispose_func=lambda p: p.close()
        )
        super(SSHHTTPAdapter, self).__init__()

    def _create_paramiko_client(self, base_url):
        logging.getLogger("paramiko").setLevel(logging.WARNING)
        self.ssh_client = paramiko.SSHClient()
        base_url = six.moves.urllib_parse.urlparse(base_url)
        self.ssh_params = {
            "hostname": base_url.hostname,
            "port": base_url.port,
            "username": base_url.username
            }
        ssh_config_file = os.path.expanduser("~/.ssh/config")
        if os.path.exists(ssh_config_file):
            conf = paramiko.SSHConfig()
            with open(ssh_config_file) as f:
                conf.parse(f)
            host_config = conf.lookup(base_url.hostname)
            self.ssh_conf = host_config
            if 'proxycommand' in host_config:
                self.ssh_params["sock"] = paramiko.ProxyCommand(
                    self.ssh_conf['proxycommand']
                )
            if 'hostname' in host_config:
                self.ssh_params['hostname'] = host_config['hostname']
            if base_url.port is None and 'port' in host_config:
                self.ssh_params['port'] = self.ssh_conf['port']
            if base_url.username is None and 'user' in host_config:
                self.ssh_params['username'] = self.ssh_conf['user']

        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.WarningPolicy())

    def _connect(self):
        if self.ssh_client:
            self.ssh_client.connect(**self.ssh_params)

    def get_connection(self, url, proxies=None):
        if not self.ssh_client:
            return SSHConnectionPool(
                ssh_client=self.ssh_client,
                timeout=self.timeout,
                maxsize=self.max_pool_size,
                host=self.ssh_host
            )
        with self.pools.lock:
            pool = self.pools.get(url)
            if pool:
                return pool

            # Connection is closed try a reconnect
            if self.ssh_client and not self.ssh_client.get_transport():
                self._connect()

            pool = SSHConnectionPool(
                ssh_client=self.ssh_client,
                timeout=self.timeout,
                maxsize=self.max_pool_size,
                host=self.ssh_host
            )
            self.pools[url] = pool

        return pool

    def close(self):
        super(SSHHTTPAdapter, self).close()
        if self.ssh_client:
            self.ssh_client.close()
