import os

import docker
import pytest

from .base import BaseAPIIntegrationTest, TEST_API_VERSION
from ..helpers import requires_api_version

SSHFS = 'vieux/sshfs:latest'


@requires_api_version('1.25')
class PluginTest(BaseAPIIntegrationTest):
    @classmethod
    def teardown_class(cls):
        c = docker.APIClient(
            version=TEST_API_VERSION, timeout=60,
            **docker.utils.kwargs_from_env()
        )
        try:
            c.remove_plugin(SSHFS, force=True)
        except docker.errors.APIError:
            pass

    def teardown_method(self, method):
        try:
            self.client.disable_plugin(SSHFS)
        except docker.errors.APIError:
            pass

        for p in self.tmp_plugins:
            try:
                self.client.remove_plugin(p, force=True)
            except docker.errors.APIError:
                pass

    def ensure_plugin_installed(self, plugin_name):
        try:
            return self.client.inspect_plugin(plugin_name)
        except docker.errors.NotFound:
            prv = self.client.plugin_privileges(plugin_name)
            for d in self.client.pull_plugin(plugin_name, prv):
                pass
        return self.client.inspect_plugin(plugin_name)

    def test_enable_plugin(self):
        pl_data = self.ensure_plugin_installed(SSHFS)
        assert pl_data['Enabled'] is False
        assert self.client.enable_plugin(SSHFS)
        pl_data = self.client.inspect_plugin(SSHFS)
        assert pl_data['Enabled'] is True
        with pytest.raises(docker.errors.APIError):
            self.client.enable_plugin(SSHFS)

    def test_disable_plugin(self):
        pl_data = self.ensure_plugin_installed(SSHFS)
        assert pl_data['Enabled'] is False
        assert self.client.enable_plugin(SSHFS)
        pl_data = self.client.inspect_plugin(SSHFS)
        assert pl_data['Enabled'] is True
        self.client.disable_plugin(SSHFS)
        pl_data = self.client.inspect_plugin(SSHFS)
        assert pl_data['Enabled'] is False
        with pytest.raises(docker.errors.APIError):
            self.client.disable_plugin(SSHFS)

    def test_inspect_plugin(self):
        self.ensure_plugin_installed(SSHFS)
        data = self.client.inspect_plugin(SSHFS)
        assert 'Config' in data
        assert 'Name' in data
        assert data['Name'] == SSHFS

    def test_plugin_privileges(self):
        prv = self.client.plugin_privileges(SSHFS)
        assert isinstance(prv, list)
        for item in prv:
            assert 'Name' in item
            assert 'Value' in item
            assert 'Description' in item

    def test_list_plugins(self):
        self.ensure_plugin_installed(SSHFS)
        data = self.client.plugins()
        assert len(data) > 0
        plugin = [p for p in data if p['Name'] == SSHFS][0]
        assert 'Config' in plugin

    def test_configure_plugin(self):
        pl_data = self.ensure_plugin_installed(SSHFS)
        assert pl_data['Enabled'] is False
        self.client.configure_plugin(SSHFS, {
            'DEBUG': '1'
        })
        pl_data = self.client.inspect_plugin(SSHFS)
        assert 'Env' in pl_data['Settings']
        assert 'DEBUG=1' in pl_data['Settings']['Env']

        self.client.configure_plugin(SSHFS, ['DEBUG=0'])
        pl_data = self.client.inspect_plugin(SSHFS)
        assert 'DEBUG=0' in pl_data['Settings']['Env']

    def test_remove_plugin(self):
        pl_data = self.ensure_plugin_installed(SSHFS)
        assert pl_data['Enabled'] is False
        assert self.client.remove_plugin(SSHFS) is True

    def test_force_remove_plugin(self):
        self.ensure_plugin_installed(SSHFS)
        self.client.enable_plugin(SSHFS)
        assert self.client.inspect_plugin(SSHFS)['Enabled'] is True
        assert self.client.remove_plugin(SSHFS, force=True) is True

    def test_install_plugin(self):
        try:
            self.client.remove_plugin(SSHFS, force=True)
        except docker.errors.APIError:
            pass

        prv = self.client.plugin_privileges(SSHFS)
        logs = [d for d in self.client.pull_plugin(SSHFS, prv)]
        assert filter(lambda x: x['status'] == 'Download complete', logs)
        assert self.client.inspect_plugin(SSHFS)
        assert self.client.enable_plugin(SSHFS)

    @requires_api_version('1.26')
    def test_upgrade_plugin(self):
        pl_data = self.ensure_plugin_installed(SSHFS)
        assert pl_data['Enabled'] is False
        prv = self.client.plugin_privileges(SSHFS)
        logs = [d for d in self.client.upgrade_plugin(SSHFS, SSHFS, prv)]
        assert filter(lambda x: x['status'] == 'Download complete', logs)
        assert self.client.inspect_plugin(SSHFS)
        assert self.client.enable_plugin(SSHFS)

    def test_create_plugin(self):
        plugin_data_dir = os.path.join(
            os.path.dirname(__file__), 'testdata/dummy-plugin'
        )
        assert self.client.create_plugin(
            'docker-sdk-py/dummy', plugin_data_dir
        )
        self.tmp_plugins.append('docker-sdk-py/dummy')
        data = self.client.inspect_plugin('docker-sdk-py/dummy')
        assert data['Config']['Entrypoint'] == ['/dummy']
