import os
import unittest
import shutil
import tempfile
import json

from py.test import ensuretemp
from pytest import mark
from docker.utils import config

try:
    from unittest import mock
except ImportError:
    import mock


class FindConfigFileTest(unittest.TestCase):
    def tmpdir(self, name):
        tmpdir = ensuretemp(name)
        self.addCleanup(tmpdir.remove)
        return tmpdir

    def test_find_config_fallback(self):
        tmpdir = self.tmpdir('test_find_config_fallback')

        with mock.patch.dict(os.environ, {'HOME': str(tmpdir)}):
            assert config.find_config_file() is None

    def test_find_config_from_explicit_path(self):
        tmpdir = self.tmpdir('test_find_config_from_explicit_path')
        config_path = tmpdir.ensure('my-config-file.json')

        assert config.find_config_file(str(config_path)) == str(config_path)

    def test_find_config_from_environment(self):
        tmpdir = self.tmpdir('test_find_config_from_environment')
        config_path = tmpdir.ensure('config.json')

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': str(tmpdir)}):
            assert config.find_config_file() == str(config_path)

    @mark.skipif("sys.platform == 'win32'")
    def test_find_config_from_home_posix(self):
        tmpdir = self.tmpdir('test_find_config_from_home_posix')
        config_path = tmpdir.ensure('.docker', 'config.json')

        with mock.patch.dict(os.environ, {'HOME': str(tmpdir)}):
            assert config.find_config_file() == str(config_path)

    @mark.skipif("sys.platform == 'win32'")
    def test_find_config_from_home_legacy_name(self):
        tmpdir = self.tmpdir('test_find_config_from_home_legacy_name')
        config_path = tmpdir.ensure('.dockercfg')

        with mock.patch.dict(os.environ, {'HOME': str(tmpdir)}):
            assert config.find_config_file() == str(config_path)

    @mark.skipif("sys.platform != 'win32'")
    def test_find_config_from_home_windows(self):
        tmpdir = self.tmpdir('test_find_config_from_home_windows')
        config_path = tmpdir.ensure('.docker', 'config.json')

        with mock.patch.dict(os.environ, {'USERPROFILE': str(tmpdir)}):
            assert config.find_config_file() == str(config_path)


class LoadConfigTest(unittest.TestCase):
    def test_load_config_no_file(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg = config.load_general_config(folder)
        assert cfg is not None
        assert isinstance(cfg, dict)
        assert not cfg

    def test_load_config_custom_headers(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder, 'config.json')
        config_data = {
            'HttpHeaders': {
                'Name': 'Spike',
                'Surname': 'Spiegel'
            },
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config_data, f)

        cfg = config.load_general_config(dockercfg_path)
        assert 'HttpHeaders' in cfg
        assert cfg['HttpHeaders'] == {
            'Name': 'Spike',
            'Surname': 'Spiegel'
        }

    def test_load_config_detach_keys(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, 'config.json')
        config_data = {
            'detachKeys': 'ctrl-q, ctrl-u, ctrl-i'
        }
        with open(dockercfg_path, 'w') as f:
            json.dump(config_data, f)

        cfg = config.load_general_config(dockercfg_path)
        assert cfg == config_data

    def test_load_config_from_env(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, 'config.json')
        config_data = {
            'detachKeys': 'ctrl-q, ctrl-u, ctrl-i'
        }
        with open(dockercfg_path, 'w') as f:
            json.dump(config_data, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = config.load_general_config(None)
        assert cfg == config_data
