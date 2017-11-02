import six
import requests.adapters
import socket

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


class UnixHTTPResponse(httplib.HTTPResponse, object):
    def __init__(self, sock, *args, **kwargs):
        disable_buffering = kwargs.pop('disable_buffering', False)
        super(UnixHTTPResponse, self).__init__(sock, *args, **kwargs)
        if disable_buffering is True:
            # We must first create a new pointer then close the old one
            # to avoid closing the underlying socket.
            new_fp = sock.makefile('rb', 0)
            self.fp.close()
            self.fp = new_fp


class UnixHTTPConnection(httplib.HTTPConnection, object):

    def __init__(self, base_url, unix_socket, timeout=60):
        super(UnixHTTPConnection, self).__init__(
            'localhost', timeout=timeout
        )
        self.base_url = base_url
        self.unix_socket = unix_socket
        self.timeout = timeout
        self.disable_buffering = False

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.unix_socket)
        self.sock = sock

    def putheader(self, header, *values):
        super(UnixHTTPConnection, self).putheader(header, *values)
        if header == 'Connection' and 'Upgrade' in values:
            self.disable_buffering = True

    def response_class(self, sock, *args, **kwargs):
        if self.disable_buffering:
            kwargs['disable_buffering'] = True

        return UnixHTTPResponse(sock, *args, **kwargs)


class AttachHTTPResponse(httplib.HTTPResponse):
    '''
    A HTTPResponse object that doesn't use a buffered fileobject.
    '''
    def __init__(self, sock, *args, **kwargs):
        # Delegate to super class
        httplib.HTTPResponse.__init__(self, sock, *args, **kwargs)

        # Override fp with a fileobject that doesn't buffer
        self.fp = sock.makefile('rb', 0)


class AttachUnixHTTPConnection(UnixHTTPConnection):
    '''
    A HTTPConnection that returns responses that don't used buffering.
    '''
    response_class = AttachHTTPResponse


class UnixHTTPConnectionPool(urllib3.connectionpool.HTTPConnectionPool):
    def __init__(self, base_url, socket_path, timeout=60, maxsize=10):
        super(UnixHTTPConnectionPool, self).__init__(
            'localhost', timeout=timeout, maxsize=maxsize
        )
        self.base_url = base_url
        self.socket_path = socket_path
        self.timeout = timeout

    def _new_conn(self):
        # Special case for attach url, as we do a http upgrade to tcp and
        # a buffered connection can cause data loss.
        path = urllib3.util.parse_url(self.base_url).path
        if path.endswith('attach'):
            return AttachUnixHTTPConnection(
                self.base_url, self.socket_path, self.timeout
            )
        else:
            return UnixHTTPConnection(
                self.base_url, self.socket_path, self.timeout
            )


class UnixAdapter(requests.adapters.HTTPAdapter):

    __attrs__ = requests.adapters.HTTPAdapter.__attrs__ + ['pools',
                                                           'socket_path',
                                                           'timeout']

    def __init__(self, socket_url, timeout=60,
                 pool_connections=constants.DEFAULT_NUM_POOLS):
        socket_path = socket_url.replace('http+unix://', '')
        if not socket_path.startswith('/'):
            socket_path = '/' + socket_path
        self.socket_path = socket_path
        self.timeout = timeout
        self.pools = RecentlyUsedContainer(
            pool_connections, dispose_func=lambda p: p.close()
        )
        super(UnixAdapter, self).__init__()

    def get_connection(self, url, proxies=None):
        with self.pools.lock:
            pool = self.pools.get(url)
            if pool:
                return pool

            pool = UnixHTTPConnectionPool(
                url, self.socket_path, self.timeout
            )
            self.pools[url] = pool

        return pool

    def request_url(self, request, proxies):
        # The select_proxy utility in requests errors out when the provided URL
        # doesn't have a hostname, like is the case when using a UNIX socket.
        # Since proxies are an irrelevant notion in the case of UNIX sockets
        # anyway, we simply return the path URL directly.
        # See also: https://github.com/docker/docker-py/issues/811
        return request.path_url

    def close(self):
        self.pools.clear()
