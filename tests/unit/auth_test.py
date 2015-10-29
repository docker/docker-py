# -*- coding: utf-8 -*-

import base64
import json
import os
import os.path
import random
import shutil
import tempfile

from docker import auth

from .. import base

try:
    from unittest import mock
except ImportError:
    import mock


class RegressionTest(base.BaseTestCase):
    def test_803_urlsafe_encode(self):
        auth_data = {
            'username': 'root',
            'password': 'GR?XGR?XGR?XGR?X'
        }
        encoded = auth.encode_header(auth_data)
        assert b'/' not in encoded
        assert b'_' in encoded


class ResolveAuthTest(base.BaseTestCase):
    auth_config = {
        'https://index.docker.io/v1/': {'auth': 'indexuser'},
        'my.registry.net': {'auth': 'privateuser'},
        'http://legacy.registry.url/v1/': {'auth': 'legacyauth'}
    }

    def test_resolve_repository_name_hub_library_image(self):
        self.assertEqual(
            auth.resolve_repository_name('image'),
            ('index.docker.io', 'image'),
        )

    def test_resolve_repository_name_hub_image(self):
        self.assertEqual(
            auth.resolve_repository_name('username/image'),
            ('index.docker.io', 'username/image'),
        )

    def test_resolve_repository_name_private_registry(self):
        self.assertEqual(
            auth.resolve_repository_name('my.registry.net/image'),
            ('my.registry.net', 'image'),
        )

    def test_resolve_repository_name_private_registry_with_port(self):
        self.assertEqual(
            auth.resolve_repository_name('my.registry.net:5000/image'),
            ('my.registry.net:5000', 'image'),
        )

    def test_resolve_repository_name_private_registry_with_username(self):
        self.assertEqual(
            auth.resolve_repository_name('my.registry.net/username/image'),
            ('my.registry.net', 'username/image'),
        )

    def test_resolve_repository_name_no_dots_but_port(self):
        self.assertEqual(
            auth.resolve_repository_name('hostname:5000/image'),
            ('hostname:5000', 'image'),
        )

    def test_resolve_repository_name_no_dots_but_port_and_username(self):
        self.assertEqual(
            auth.resolve_repository_name('hostname:5000/username/image'),
            ('hostname:5000', 'username/image'),
        )

    def test_resolve_repository_name_localhost(self):
        self.assertEqual(
            auth.resolve_repository_name('localhost/image'),
            ('localhost', 'image'),
        )

    def test_resolve_repository_name_localhost_with_username(self):
        self.assertEqual(
            auth.resolve_repository_name('localhost/username/image'),
            ('localhost', 'username/image'),
        )

    def test_resolve_authconfig_hostname_only(self):
        self.assertEqual(
            auth.resolve_authconfig(self.auth_config, 'my.registry.net'),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_no_protocol(self):
        self.assertEqual(
            auth.resolve_authconfig(self.auth_config, 'my.registry.net/v1/'),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_no_path(self):
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, 'http://my.registry.net'
            ),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_no_path_trailing_slash(self):
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, 'http://my.registry.net/'
            ),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_no_path_wrong_secure_proto(self):
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, 'https://my.registry.net'
            ),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_no_path_wrong_insecure_proto(self):
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, 'http://index.docker.io'
            ),
            {'auth': 'indexuser'}
        )

    def test_resolve_authconfig_path_wrong_proto(self):
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, 'https://my.registry.net/v1/'
            ),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_default_registry(self):
        self.assertEqual(
            auth.resolve_authconfig(self.auth_config), {'auth': 'indexuser'}
        )

    def test_resolve_authconfig_default_explicit_none(self):
        self.assertEqual(
            auth.resolve_authconfig(self.auth_config, None),
            {'auth': 'indexuser'}
        )

    def test_resolve_authconfig_fully_explicit(self):
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, 'http://my.registry.net/v1/'
            ),
            {'auth': 'privateuser'}
        )

    def test_resolve_authconfig_legacy_config(self):
        self.assertEqual(
            auth.resolve_authconfig(self.auth_config, 'legacy.registry.url'),
            {'auth': 'legacyauth'}
        )

    def test_resolve_authconfig_no_match(self):
        self.assertTrue(
            auth.resolve_authconfig(self.auth_config, 'does.not.exist') is None
        )

    def test_resolve_registry_and_auth_library_image(self):
        image = 'image'
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, auth.resolve_repository_name(image)[0]
            ),
            {'auth': 'indexuser'},
        )

    def test_resolve_registry_and_auth_hub_image(self):
        image = 'username/image'
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, auth.resolve_repository_name(image)[0]
            ),
            {'auth': 'indexuser'},
        )

    def test_resolve_registry_and_auth_private_registry(self):
        image = 'my.registry.net/image'
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, auth.resolve_repository_name(image)[0]
            ),
            {'auth': 'privateuser'},
        )

    def test_resolve_registry_and_auth_unauthenticated_registry(self):
        image = 'other.registry.net/image'
        self.assertEqual(
            auth.resolve_authconfig(
                self.auth_config, auth.resolve_repository_name(image)[0]
            ),
            None,
        )


class LoadConfigTest(base.Cleanup, base.BaseTestCase):
    def test_load_config_no_file(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg = auth.load_config(folder)
        self.assertTrue(cfg is not None)

    def test_load_config(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, '.dockercfg')
        with open(dockercfg_path, 'w') as f:
            auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
            f.write('auth = {0}\n'.format(auth_))
            f.write('email = sakuya@scarlet.net')
        cfg = auth.load_config(dockercfg_path)
        assert auth.INDEX_NAME in cfg
        self.assertNotEqual(cfg[auth.INDEX_NAME], None)
        cfg = cfg[auth.INDEX_NAME]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('auth'), None)

    def test_load_config_with_random_name(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder,
                                      '.{0}.dockercfg'.format(
                                          random.randrange(100000)))
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            registry: {
                'auth': '{0}'.format(auth_),
                'email': 'sakuya@scarlet.net'
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        cfg = auth.load_config(dockercfg_path)
        assert registry in cfg
        self.assertNotEqual(cfg[registry], None)
        cfg = cfg[registry]
        self.assertEqual(cfg['username'], 'sakuya')
        self.assertEqual(cfg['password'], 'izayoi')
        self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
        self.assertEqual(cfg.get('auth'), None)

    def test_load_config_custom_config_env(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder, 'config.json')
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            registry: {
                'auth': '{0}'.format(auth_),
                'email': 'sakuya@scarlet.net'
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = auth.load_config(None)
            assert registry in cfg
            self.assertNotEqual(cfg[registry], None)
            cfg = cfg[registry]
            self.assertEqual(cfg['username'], 'sakuya')
            self.assertEqual(cfg['password'], 'izayoi')
            self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
            self.assertEqual(cfg.get('auth'), None)

    def test_load_config_custom_config_env_with_auths(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder, 'config.json')
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            'auths': {
                registry: {
                    'auth': '{0}'.format(auth_),
                    'email': 'sakuya@scarlet.net'
                }
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = auth.load_config(None)
            assert registry in cfg
            self.assertNotEqual(cfg[registry], None)
            cfg = cfg[registry]
            self.assertEqual(cfg['username'], 'sakuya')
            self.assertEqual(cfg['password'], 'izayoi')
            self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
            self.assertEqual(cfg.get('auth'), None)

    def test_load_config_custom_config_env_utf8(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder, 'config.json')
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(
            b'sakuya\xc3\xa6:izayoi\xc3\xa6').decode('ascii')
        config = {
            'auths': {
                registry: {
                    'auth': '{0}'.format(auth_),
                    'email': 'sakuya@scarlet.net'
                }
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = auth.load_config(None)
            assert registry in cfg
            self.assertNotEqual(cfg[registry], None)
            cfg = cfg[registry]
            self.assertEqual(cfg['username'], b'sakuya\xc3\xa6'.decode('utf8'))
            self.assertEqual(cfg['password'], b'izayoi\xc3\xa6'.decode('utf8'))
            self.assertEqual(cfg['email'], 'sakuya@scarlet.net')
            self.assertEqual(cfg.get('auth'), None)
