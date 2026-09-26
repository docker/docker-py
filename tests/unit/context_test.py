import hashlib
import json
import os
import shutil
import tempfile
import unittest
from unittest import mock

import pytest

import docker
from docker.constants import DEFAULT_NPIPE, DEFAULT_UNIX_SOCKET, IS_WINDOWS_PLATFORM
from docker.context import Context, ContextAPI


class BaseContextTest(unittest.TestCase):
    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM, reason='Linux specific path check'
    )
    def test_url_compatibility_on_linux(self):
        c = Context("test")
        assert c.Host == DEFAULT_UNIX_SOCKET[5:]

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Windows specific path check'
    )
    def test_url_compatibility_on_windows(self):
        c = Context("test")
        assert c.Host == DEFAULT_NPIPE

    def test_fail_on_default_context_create(self):
        with pytest.raises(docker.errors.ContextException):
            ContextAPI.create_context("default")

    def test_default_in_context_list(self):
        found = False
        ctx = ContextAPI.contexts()
        for c in ctx:
            if c.Name == "default":
                found = True
        assert found is True

    def test_get_current_context(self):
        assert ContextAPI.get_current_context().Name == "default"

    def test_https_host(self):
        c = Context("test", host="tcp://testdomain:8080", tls=True)
        assert c.Host == "https://testdomain:8080"

    def test_context_inspect_without_params(self):
        ctx = ContextAPI.inspect_context()
        assert ctx["Name"] == "default"
        assert ctx["Metadata"]["StackOrchestrator"] == "swarm"
        assert ctx["Endpoints"]["docker"]["Host"] in (
            DEFAULT_NPIPE,
            DEFAULT_UNIX_SOCKET[5:],
        )


class LoadContextTLSTest(unittest.TestCase):
    """Contexts written by ``docker context create`` use TLS whenever the
    endpoint has TLS material or ``skip-tls-verify=true``, even without a
    client certificate."""

    def setUp(self):
        self.config_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.config_dir)
        patcher = mock.patch.dict(
            os.environ, {'DOCKER_CONFIG': self.config_dir}
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        with open(os.path.join(self.config_dir, 'config.json'), 'w') as f:
            json.dump({}, f)

    def write_context(self, name, skip_tls_verify=False, tls_files=()):
        context_id = hashlib.sha256(name.encode('utf-8')).hexdigest()
        meta_dir = os.path.join(
            self.config_dir, 'contexts', 'meta', context_id
        )
        os.makedirs(meta_dir)
        with open(os.path.join(meta_dir, 'meta.json'), 'w') as f:
            json.dump({
                'Name': name,
                'Metadata': {},
                'Endpoints': {'docker': {
                    'Host': 'tcp://testdomain:2376',
                    'SkipTLSVerify': skip_tls_verify,
                }},
            }, f)
        if tls_files:
            tls_dir = os.path.join(
                self.config_dir, 'contexts', 'tls', context_id, 'docker'
            )
            os.makedirs(tls_dir)
            for filename in tls_files:
                with open(os.path.join(tls_dir, filename), 'w') as f:
                    f.write('pem')
            return tls_dir

    def test_ca_only_context_uses_tls(self):
        tls_dir = self.write_context('ca-only', tls_files=['ca.pem'])
        ctx = ContextAPI.get_context('ca-only')
        tls = ctx.TLSConfig
        assert tls is not None
        assert tls.ca_cert == os.path.join(tls_dir, 'ca.pem')
        assert tls.cert is None
        assert tls.verify is True
        assert ctx.TLSMaterial == {'TLSMaterial': {'docker': ['ca.pem']}}

        params = ContextAPI.kwargs_from_context(name='ca-only')
        client = docker.APIClient(version='1.45', **params)
        assert client.base_url == 'https://testdomain:2376'
        assert client.verify == os.path.join(tls_dir, 'ca.pem')
        assert client.cert is None

    def test_skip_tls_verify_context_uses_tls(self):
        self.write_context('insecure', skip_tls_verify=True)
        ctx = ContextAPI.get_context('insecure')
        tls = ctx.TLSConfig
        assert tls is not None
        assert not tls.verify

        params = ContextAPI.kwargs_from_context(name='insecure')
        client = docker.APIClient(version='1.45', **params)
        assert client.base_url == 'https://testdomain:2376'
        assert not client.verify

    def test_client_cert_context_uses_tls(self):
        tls_dir = self.write_context(
            'mtls', tls_files=['ca.pem', 'cert.pem', 'key.pem']
        )
        tls = ContextAPI.get_context('mtls').TLSConfig
        assert tls.ca_cert == os.path.join(tls_dir, 'ca.pem')
        assert tls.cert == (
            os.path.join(tls_dir, 'cert.pem'),
            os.path.join(tls_dir, 'key.pem'),
        )
        assert tls.verify is True

    def test_plain_tcp_context_has_no_tls(self):
        self.write_context('plain')
        assert ContextAPI.get_context('plain').TLSConfig is None
        params = ContextAPI.kwargs_from_context(name='plain')
        assert params == {'base_url': 'tcp://testdomain:2376'}
