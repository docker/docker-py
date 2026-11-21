import json
import os
import tempfile
import unittest
from unittest import mock

import pytest

import docker
from docker.constants import DEFAULT_NPIPE, DEFAULT_UNIX_SOCKET, IS_WINDOWS_PLATFORM
from docker.context import Context, ContextAPI
from docker.context.config import get_context_dir, get_meta_dir, get_tls_dir


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


@pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='POSIX-specific HOME handling')
def test_context_paths_use_default_docker_config_dir_when_config_missing():
    with tempfile.TemporaryDirectory() as home:
        with mock.patch.dict(os.environ, {'HOME': home}, clear=False):
            assert get_context_dir() == os.path.join(home, '.docker', 'contexts')
            assert get_meta_dir('demo').startswith(
                os.path.join(home, '.docker', 'contexts', 'meta')
            )
            assert get_tls_dir('demo').startswith(
                os.path.join(home, '.docker', 'contexts', 'tls')
            )


@pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='POSIX-specific HOME handling')
def test_set_current_context_creates_config_in_default_docker_dir():
    with tempfile.TemporaryDirectory() as home, tempfile.TemporaryDirectory() as cwd:
        with mock.patch.dict(os.environ, {'HOME': home}, clear=False):
            old_cwd = os.getcwd()
            try:
                os.chdir(cwd)
                ctx = ContextAPI.create_context('demo')
                ContextAPI.set_current_context('demo')
            finally:
                os.chdir(old_cwd)

        config_path = os.path.join(home, '.docker', 'config.json')
        with open(config_path) as f:
            config = json.load(f)

        assert config["currentContext"] == 'demo'
        assert ctx.meta_path.startswith(os.path.join(home, '.docker', 'contexts'))
        assert not os.path.exists(os.path.join(cwd, 'contexts'))
