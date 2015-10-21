# Copyright 2013 dotCloud inc.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import datetime
import json
import os
import re
import shutil
import socket
import sys
import tempfile
import threading
import time

import docker
import requests
import six

from .. import base
from . import fake_api

import pytest

try:
    from unittest import mock
except ImportError:
    import mock


DEFAULT_TIMEOUT_SECONDS = docker.constants.DEFAULT_TIMEOUT_SECONDS


def response(status_code=200, content='', headers=None, reason=None, elapsed=0,
             request=None):
    res = requests.Response()
    res.status_code = status_code
    if not isinstance(content, six.binary_type):
        content = json.dumps(content).encode('ascii')
    res._content = content
    res.headers = requests.structures.CaseInsensitiveDict(headers or {})
    res.reason = reason
    res.elapsed = datetime.timedelta(elapsed)
    res.request = request
    return res


def fake_resolve_authconfig(authconfig, registry=None):
    return None


def fake_inspect_container(self, container, tty=False):
    return fake_api.get_fake_inspect_container(tty=tty)[1]


def fake_resp(method, url, *args, **kwargs):
    key = None
    if url in fake_api.fake_responses:
        key = url
    elif (url, method) in fake_api.fake_responses:
        key = (url, method)
    if not key:
        raise Exception('{0} {1}'.format(method, url))
    status_code, content = fake_api.fake_responses[key]()
    return response(status_code=status_code, content=content)


fake_request = mock.Mock(side_effect=fake_resp)


def fake_get(self, url, *args, **kwargs):
    return fake_request('GET', url, *args, **kwargs)


def fake_post(self, url, *args, **kwargs):
    return fake_request('POST', url, *args, **kwargs)


def fake_put(self, url, *args, **kwargs):
    return fake_request('PUT', url, *args, **kwargs)


def fake_delete(self, url, *args, **kwargs):
    return fake_request('DELETE', url, *args, **kwargs)

url_base = 'http+docker://localunixsocket/'
url_prefix = '{0}v{1}/'.format(
    url_base,
    docker.constants.DEFAULT_DOCKER_API_VERSION)


class DockerClientTest(base.Cleanup, base.BaseTestCase):
    def setUp(self):
        self.patcher = mock.patch.multiple(
            'docker.Client', get=fake_get, post=fake_post, put=fake_put,
            delete=fake_delete
        )
        self.patcher.start()
        self.client = docker.Client()
        # Force-clear authconfig to avoid tampering with the tests
        self.client._cfg = {'Configs': {}}

    def tearDown(self):
        self.client.close()
        self.patcher.stop()

    def assertIn(self, object, collection):
        if six.PY2 and sys.version_info[1] <= 6:
            return self.assertTrue(object in collection)
        return super(DockerClientTest, self).assertIn(object, collection)

    def base_create_payload(self, img='busybox', cmd=None):
        if not cmd:
            cmd = ['true']
        return {"Tty": False, "Image": img, "Cmd": cmd,
                "AttachStdin": False,
                "AttachStderr": True, "AttachStdout": True,
                "StdinOnce": False,
                "OpenStdin": False, "NetworkDisabled": False,
                }


class DockerApiTest(DockerClientTest):
    def test_ctor(self):
        with pytest.raises(docker.errors.DockerException) as excinfo:
            docker.Client(version=1.12)

        self.assertEqual(
            str(excinfo.value),
            'Version parameter must be a string or None. Found float'
        )

    def test_url_valid_resource(self):
        url = self.client._url('/hello/{0}/world', 'somename')
        self.assertEqual(
            url, '{0}{1}'.format(url_prefix, 'hello/somename/world')
        )

        url = self.client._url(
            '/hello/{0}/world/{1}', 'somename', 'someothername'
        )
        self.assertEqual(
            url,
            '{0}{1}'.format(url_prefix, 'hello/somename/world/someothername')
        )

        url = self.client._url('/hello/{0}/world', '/some?name')
        self.assertEqual(
            url, '{0}{1}'.format(url_prefix, 'hello/%2Fsome%3Fname/world')
        )

    def test_url_invalid_resource(self):
        with pytest.raises(ValueError):
            self.client._url('/hello/{0}/world', ['sakuya', 'izayoi'])

    def test_url_no_resource(self):
        url = self.client._url('/simple')
        self.assertEqual(url, '{0}{1}'.format(url_prefix, 'simple'))

    def test_url_unversioned_api(self):
        url = self.client._url(
            '/hello/{0}/world', 'somename', versioned_api=False
        )
        self.assertEqual(
            url, '{0}{1}'.format(url_base, 'hello/somename/world')
        )

    def test_version(self):
        self.client.version()

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'version',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_version_no_api_version(self):
        self.client.version(False)

        fake_request.assert_called_with(
            'GET',
            url_base + 'version',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_retrieve_server_version(self):
        client = docker.Client(version="auto")
        self.assertTrue(isinstance(client._version, six.string_types))
        self.assertFalse(client._version == "auto")
        client.close()

    def test_auto_retrieve_server_version(self):
        version = self.client._retrieve_server_version()
        self.assertTrue(isinstance(version, six.string_types))

    def test_info(self):
        self.client.info()

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'info',
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_search(self):
        self.client.search('busybox')

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'images/search',
            params={'term': 'busybox'},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_events(self):
        self.client.events()

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'events',
            params={'since': None, 'until': None, 'filters': None},
            stream=True
        )

    def test_events_with_since_until(self):
        ts = 1356048000
        now = datetime.datetime.utcfromtimestamp(ts)
        since = now - datetime.timedelta(seconds=10)
        until = now + datetime.timedelta(seconds=10)

        self.client.events(since=since, until=until)

        fake_request.assert_called_with(
            'GET',
            url_prefix + 'events',
            params={
                'since': ts - 10,
                'until': ts + 10,
                'filters': None
            },
            stream=True
        )

    def test_events_with_filters(self):
        filters = {'event': ['die', 'stop'],
                   'container': fake_api.FAKE_CONTAINER_ID}

        self.client.events(filters=filters)

        expected_filters = docker.utils.convert_filters(filters)
        fake_request.assert_called_with(
            'GET',
            url_prefix + 'events',
            params={
                'since': None,
                'until': None,
                'filters': expected_filters
            },
            stream=True
        )

    def _socket_path_for_client_session(self, client):
        socket_adapter = client.get_adapter('http+docker://')
        return socket_adapter.socket_path

    def test_url_compatibility_unix(self):
        c = docker.Client(base_url="unix://socket")

        assert self._socket_path_for_client_session(c) == '/socket'

    def test_url_compatibility_unix_triple_slash(self):
        c = docker.Client(base_url="unix:///socket")

        assert self._socket_path_for_client_session(c) == '/socket'

    def test_url_compatibility_http_unix_triple_slash(self):
        c = docker.Client(base_url="http+unix:///socket")

        assert self._socket_path_for_client_session(c) == '/socket'

    def test_url_compatibility_http(self):
        c = docker.Client(base_url="http://hostname:1234")

        assert c.base_url == "http://hostname:1234"

    def test_url_compatibility_tcp(self):
        c = docker.Client(base_url="tcp://hostname:1234")

        assert c.base_url == "http://hostname:1234"

    def test_remove_link(self):
        self.client.remove_container(fake_api.FAKE_CONTAINER_ID, link=True)

        fake_request.assert_called_with(
            'DELETE',
            url_prefix + 'containers/3cc2351ab11b',
            params={'v': False, 'link': True, 'force': False},
            timeout=DEFAULT_TIMEOUT_SECONDS
        )

    def test_create_host_config_secopt(self):
        security_opt = ['apparmor:test_profile']
        result = self.client.create_host_config(security_opt=security_opt)
        self.assertIn('SecurityOpt', result)
        self.assertEqual(result['SecurityOpt'], security_opt)
        self.assertRaises(
            docker.errors.DockerException, self.client.create_host_config,
            security_opt='wrong'
        )


class StreamTest(base.Cleanup, base.BaseTestCase):
    def setUp(self):
        socket_dir = tempfile.mkdtemp()
        self.build_context = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, socket_dir)
        self.addCleanup(shutil.rmtree, self.build_context)
        self.socket_file = os.path.join(socket_dir, 'test_sock.sock')
        self.server_socket = self._setup_socket()
        self.stop_server = False
        server_thread = threading.Thread(target=self.run_server)
        server_thread.setDaemon(True)
        server_thread.start()
        self.response = None
        self.request_handler = None
        self.addCleanup(server_thread.join)
        self.addCleanup(self.stop)

    def stop(self):
        self.stop_server = True

    def _setup_socket(self):
        server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server_sock.bind(self.socket_file)
        # Non-blocking mode so that we can shut the test down easily
        server_sock.setblocking(0)
        server_sock.listen(5)
        return server_sock

    def run_server(self):
        try:
            while not self.stop_server:
                try:
                    connection, client_address = self.server_socket.accept()
                except socket.error:
                    # Probably no connection to accept yet
                    time.sleep(0.01)
                    continue

                connection.setblocking(1)
                try:
                    self.request_handler(connection)
                finally:
                    connection.close()
        finally:
            self.server_socket.close()

    def early_response_sending_handler(self, connection):
        data = b''
        headers = None

        connection.sendall(self.response)
        while not headers:
            data += connection.recv(2048)
            parts = data.split(b'\r\n\r\n', 1)
            if len(parts) == 2:
                headers, data = parts

        mo = re.search(r'Content-Length: ([0-9]+)', headers.decode())
        assert mo
        content_length = int(mo.group(1))

        while True:
            if len(data) >= content_length:
                break

            data += connection.recv(2048)

    def test_early_stream_response(self):
        self.request_handler = self.early_response_sending_handler
        lines = []
        for i in range(0, 50):
            line = str(i).encode()
            lines += [('%x' % len(line)).encode(), line]
        lines.append(b'0')
        lines.append(b'')

        self.response = (
            b'HTTP/1.1 200 OK\r\n'
            b'Transfer-Encoding: chunked\r\n'
            b'\r\n'
        ) + b'\r\n'.join(lines)

        with docker.Client(base_url="http+unix://" + self.socket_file) \
                as client:
            for i in range(5):
                try:
                    stream = client.build(
                        path=self.build_context,
                        stream=True
                    )
                    break
                except requests.ConnectionError as e:
                    if i == 4:
                        raise e

            self.assertEqual(list(stream), [
                str(i).encode() for i in range(50)])
