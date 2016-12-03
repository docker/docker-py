import gzip
import io
import tempfile as tf

import docker
from docker import auth

from .api_test import BaseAPIClientTest, fake_request, url_prefix


class BuildTest(BaseAPIClientTest):
    def test_build_container(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))

        self.client.build(fileobj=script)

    def test_build_container_pull(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))

        self.client.build(fileobj=script, pull=True)

    def test_build_container_stream(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))

        self.client.build(fileobj=script, stream=True)

    def test_build_container_custom_context(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script)

        self.client.build(fileobj=context, custom_context=True)

    def test_build_container_custom_context_with_files(self):
        d0 = tf.mkdtemp()
        d1 = tf.mkdtemp(dir=d0)
        d2 = tf.mkdtemp(dir=d1)
        f1 = tf.NamedTemporaryFile(suffix="docker", dir=d0, delete=True)
        f2 = tf.NamedTemporaryFile(suffix="docker", dir=d0, delete=True)
        f3 = tf.NamedTemporaryFile(suffix="docker", dir=d0, delete=True)
        p1 = tf.NamedTemporaryFile(suffix="docker", dir=d1, delete=True)
        p2 = tf.NamedTemporaryFile(suffix="docker", dir=d1, delete=True)
        p3 = tf.NamedTemporaryFile(suffix="docker", dir=d1, delete=True)
        w1 = tf.NamedTemporaryFile(suffix="docker", dir=d2, delete=True)
        w2 = tf.NamedTemporaryFile(suffix="docker", dir=d2, delete=True)
        w3 = tf.NamedTemporaryFile(suffix="docker", dir=d2, delete=True)
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD '+f1.name+' /tmp/f1',
            'ADD '+f2.name+' /tmp/f2',
            'ADD '+f3.name+' /tmp/f3',
            'ADD '+p1.name+' /tmp/p1',
            'ADD '+p2.name+' /tmp/p2',
            'ADD '+p3.name+' /tmp/p3',
            'ADD '+w1.name+' /tmp/w1',
            'ADD '+w2.name+' /tmp/w2',
            'ADD '+w3.name+' /tmp/w3'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script,
                                              [f1.name,
                                               f2.name,
                                               d1])

        self.client.build(fileobj=context, custom_context=True)

    def test_build_container_custom_context_gzip(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        context = docker.utils.mkbuildcontext(script)
        gz_context = gzip.GzipFile(fileobj=context)

        self.client.build(
            fileobj=gz_context,
            custom_context=True,
            encoding="gzip"
        )

    def test_build_remote_with_registry_auth(self):
        self.client._auth_configs = {
            'https://example.com': {
                'user': 'example',
                'password': 'example',
                'email': 'example@example.com'
            }
        }

        expected_params = {'t': None, 'q': False, 'dockerfile': None,
                           'rm': False, 'nocache': False, 'pull': False,
                           'forcerm': False,
                           'remote': 'https://github.com/docker-library/mongo'}
        expected_headers = {
            'X-Registry-Config': auth.encode_header(self.client._auth_configs)}

        self.client.build(path='https://github.com/docker-library/mongo')

        fake_request.assert_called_with(
            'POST',
            url_prefix + 'build',
            stream=True,
            data=None,
            headers=expected_headers,
            params=expected_params,
            timeout=None
        )

    def test_build_container_with_named_dockerfile(self):
        self.client.build('.', dockerfile='nameddockerfile')

    def test_build_container_with_container_limits(self):
        self.client.build('.', container_limits={
            'memory': 1024 * 1024,
            'cpusetcpus': 1,
            'cpushares': 1000,
            'memswap': 1024 * 1024 * 8
        })

    def test_build_container_invalid_container_limits(self):
        self.assertRaises(
            docker.errors.DockerException,
            lambda: self.client.build('.', container_limits={
                'foo': 'bar'
            })
        )

    def test_set_auth_headers_with_empty_dict_and_auth_configs(self):
        self.client._auth_configs = {
            'https://example.com': {
                'user': 'example',
                'password': 'example',
                'email': 'example@example.com'
            }
        }

        headers = {}
        expected_headers = {
            'X-Registry-Config': auth.encode_header(self.client._auth_configs)}
        self.client._set_auth_headers(headers)
        self.assertEqual(headers, expected_headers)

    def test_set_auth_headers_with_dict_and_auth_configs(self):
        self.client._auth_configs = {
            'https://example.com': {
                'user': 'example',
                'password': 'example',
                'email': 'example@example.com'
            }
        }

        headers = {'foo': 'bar'}
        expected_headers = {
            'foo': 'bar',
            'X-Registry-Config': auth.encode_header(self.client._auth_configs)}

        self.client._set_auth_headers(headers)
        self.assertEqual(headers, expected_headers)

    def test_set_auth_headers_with_dict_and_no_auth_configs(self):
        headers = {'foo': 'bar'}
        expected_headers = {
            'foo': 'bar'
        }

        self.client._set_auth_headers(headers)
        self.assertEqual(headers, expected_headers)
