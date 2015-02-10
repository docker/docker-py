# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
import six
import requests.adapters
import socket

if six.PY3:
    import http.client as httplib
else:
    import httplib

try:
    import requests.packages.urllib3 as urllib3
except ImportError:
    import urllib3


class UnixHTTPConnection(httplib.HTTPConnection, object):
    def __init__(self, base_url, unix_socket, timeout=60):
        httplib.HTTPConnection.__init__(self, 'localhost', timeout=timeout)
        self.base_url = base_url
        self.unix_socket = unix_socket
        self.timeout = timeout

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.base_url.replace("http+unix:/", ""))
        self.sock = sock

    def _extract_path(self, url):
        # remove the base_url entirely..
        return url.replace(self.base_url, "")

    def request(self, method, url, **kwargs):
        url = self._extract_path(self.unix_socket)
        super(UnixHTTPConnection, self).request(method, url, **kwargs)


class UnixHTTPConnectionPool(urllib3.connectionpool.HTTPConnectionPool):
    def __init__(self, base_url, socket_path, timeout=60):
        urllib3.connectionpool.HTTPConnectionPool.__init__(
            self, 'localhost', timeout=timeout
        )
        self.base_url = base_url
        self.socket_path = socket_path
        self.timeout = timeout

    def _new_conn(self):
        return UnixHTTPConnection(self.base_url, self.socket_path,
                                  self.timeout)


class UnixAdapter(requests.adapters.HTTPAdapter):
    def __init__(self, base_url, timeout=60):
        RecentlyUsedContainer = urllib3._collections.RecentlyUsedContainer
        self.base_url = base_url
        self.timeout = timeout
        self.pools = RecentlyUsedContainer(10,
                                           dispose_func=lambda p: p.close())
        super(UnixAdapter, self).__init__()

    def get_connection(self, socket_path, proxies=None):
        with self.pools.lock:
            pool = self.pools.get(socket_path)
            if pool:
                return pool

            pool = UnixHTTPConnectionPool(
                self.base_url, socket_path, self.timeout
            )
            self.pools[socket_path] = pool

        return pool

    def close(self):
        self.pools.clear()
