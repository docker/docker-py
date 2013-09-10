import httplib
import requests.adapters
import requests.packages.urllib3.connectionpool
import socket

HTTPConnectionPool = requests.packages.urllib3.connectionpool.HTTPConnectionPool


class UnixHTTPConnection(httplib.HTTPConnection, object):
    def __init__(self, base_url, unix_socket):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.base_url = base_url
        self.unix_socket = unix_socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.base_url.replace("unix:/",""))
        self.sock = sock

    def _extract_path(self, url):
        #remove the base_url entirely..
        return url.replace(self.base_url, "")

    def request(self, method, url, **kwargs):
        url = self._extract_path(self.unix_socket)
        super(UnixHTTPConnection, self).request(method, url, **kwargs)


class UnixHTTPConnectionPool(HTTPConnectionPool):
    def __init__(self, base_url, socket_path):
        self.socket_path = socket_path
        self.base_url = base_url
        super(UnixHTTPConnectionPool, self).__init__(self, 'localhost')

    def _new_conn(self):
        return UnixHTTPConnection(self.base_url, self.socket_path)


class UnixAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, base_url):
        self.base_url = base_url
        super(UnixAdapter, self).__init__()

    def get_connection(self, socket_path, proxies=None):
        return UnixHTTPConnectionPool(self.base_url, socket_path)
