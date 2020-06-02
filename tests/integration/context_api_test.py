import os
import tempfile
import pytest
from docker import errors
from docker.context import ContextAPI
from docker.tls import TLSConfig
from .base import BaseAPIIntegrationTest


class ContextLifecycleTest(BaseAPIIntegrationTest):
    def test_lifecycle(self):
        assert ContextAPI.get_context().Name == "default"
        assert not ContextAPI.get_context("test")
        assert ContextAPI.get_current_context().Name == "default"

        dirpath = tempfile.mkdtemp()
        ca = tempfile.NamedTemporaryFile(
            prefix=os.path.join(dirpath, "ca.pem"), mode="r")
        cert = tempfile.NamedTemporaryFile(
            prefix=os.path.join(dirpath, "cert.pem"), mode="r")
        key = tempfile.NamedTemporaryFile(
            prefix=os.path.join(dirpath, "key.pem"), mode="r")

        # create context 'test
        docker_tls = TLSConfig(
            client_cert=(cert.name, key.name),
            ca_cert=ca.name)
        ContextAPI.create_context(
            "test", tls_cfg=docker_tls)

        # check for a context 'test' in the context store
        assert any([ctx.Name == "test" for ctx in ContextAPI.contexts()])
        # retrieve a context object for 'test'
        assert ContextAPI.get_context("test")
        # remove context
        ContextAPI.remove_context("test")
        with pytest.raises(errors.ContextNotFound):
            ContextAPI.inspect_context("test")
        # check there is no 'test' context in store
        assert not ContextAPI.get_context("test")

        ca.close()
        key.close()
        cert.close()

    def test_context_remove(self):
        ContextAPI.create_context("test")
        assert ContextAPI.inspect_context("test")["Name"] == "test"

        ContextAPI.remove_context("test")
        with pytest.raises(errors.ContextNotFound):
            ContextAPI.inspect_context("test")

    def test_load_context_without_orchestrator(self):
        ContextAPI.create_context("test")
        ctx = ContextAPI.get_context("test")
        assert ctx
        assert ctx.Name == "test"
        assert ctx.Orchestrator is None
