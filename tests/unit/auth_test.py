import base64
import json
import os
import os.path
import random
import shutil
import tempfile
import unittest

from docker import auth, credentials, errors
from unittest import mock
import pytest


class RegressionTest(unittest.TestCase):
    def test_803_urlsafe_encode(self):
        auth_data = {
            'username': 'root',
            'password': 'GR?XGR?XGR?XGR?X'
        }
        encoded = auth.encode_header(auth_data)
        assert b'/' not in encoded
        assert b'_' in encoded


class ResolveRepositoryNameTest(unittest.TestCase):
    def test_resolve_repository_name_hub_library_image(self):
        assert auth.resolve_repository_name('image') == (
            'docker.io', 'image'
        )

    def test_resolve_repository_name_dotted_hub_library_image(self):
        assert auth.resolve_repository_name('image.valid') == (
            'docker.io', 'image.valid'
        )

    def test_resolve_repository_name_hub_image(self):
        assert auth.resolve_repository_name('username/image') == (
            'docker.io', 'username/image'
        )

    def test_explicit_hub_index_library_image(self):
        assert auth.resolve_repository_name('docker.io/image') == (
            'docker.io', 'image'
        )

    def test_explicit_legacy_hub_index_library_image(self):
        assert auth.resolve_repository_name('index.docker.io/image') == (
            'docker.io', 'image'
        )

    def test_resolve_repository_name_private_registry(self):
        assert auth.resolve_repository_name('my.registry.net/image') == (
            'my.registry.net', 'image'
        )

    def test_resolve_repository_name_private_registry_with_port(self):
        assert auth.resolve_repository_name('my.registry.net:5000/image') == (
            'my.registry.net:5000', 'image'
        )

    def test_resolve_repository_name_private_registry_with_username(self):
        assert auth.resolve_repository_name(
            'my.registry.net/username/image'
        ) == ('my.registry.net', 'username/image')

    def test_resolve_repository_name_no_dots_but_port(self):
        assert auth.resolve_repository_name('hostname:5000/image') == (
            'hostname:5000', 'image'
        )

    def test_resolve_repository_name_no_dots_but_port_and_username(self):
        assert auth.resolve_repository_name(
            'hostname:5000/username/image'
        ) == ('hostname:5000', 'username/image')

    def test_resolve_repository_name_localhost(self):
        assert auth.resolve_repository_name('localhost/image') == (
            'localhost', 'image'
        )

    def test_resolve_repository_name_localhost_with_username(self):
        assert auth.resolve_repository_name('localhost/username/image') == (
            'localhost', 'username/image'
        )

    def test_invalid_index_name(self):
        with pytest.raises(errors.InvalidRepository):
            auth.resolve_repository_name('-gecko.com/image')


def encode_auth(auth_info):
    return base64.b64encode(
        auth_info.get('username', '').encode('utf-8') + b':' +
        auth_info.get('password', '').encode('utf-8'))


class ResolveAuthTest(unittest.TestCase):
    index_config = {'auth': encode_auth({'username': 'indexuser'})}
    private_config = {'auth': encode_auth({'username': 'privateuser'})}
    legacy_config = {'auth': encode_auth({'username': 'legacyauth'})}

    auth_config = auth.AuthConfig({
        'auths': auth.parse_auth({
            'https://index.docker.io/v1/': index_config,
            'my.registry.net': private_config,
            'http://legacy.registry.url/v1/': legacy_config,
        })
    })

    def test_resolve_authconfig_hostname_only(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'my.registry.net'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_no_protocol(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'my.registry.net/v1/'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_no_path(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'http://my.registry.net'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_no_path_trailing_slash(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'http://my.registry.net/'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_no_path_wrong_secure_proto(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'https://my.registry.net'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_no_path_wrong_insecure_proto(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'http://index.docker.io'
        )['username'] == 'indexuser'

    def test_resolve_authconfig_path_wrong_proto(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'https://my.registry.net/v1/'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_default_registry(self):
        assert auth.resolve_authconfig(
            self.auth_config
        )['username'] == 'indexuser'

    def test_resolve_authconfig_default_explicit_none(self):
        assert auth.resolve_authconfig(
            self.auth_config, None
        )['username'] == 'indexuser'

    def test_resolve_authconfig_fully_explicit(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'http://my.registry.net/v1/'
        )['username'] == 'privateuser'

    def test_resolve_authconfig_legacy_config(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'legacy.registry.url'
        )['username'] == 'legacyauth'

    def test_resolve_authconfig_no_match(self):
        assert auth.resolve_authconfig(
            self.auth_config, 'does.not.exist'
        ) is None

    def test_resolve_registry_and_auth_library_image(self):
        image = 'image'
        assert auth.resolve_authconfig(
            self.auth_config, auth.resolve_repository_name(image)[0]
        )['username'] == 'indexuser'

    def test_resolve_registry_and_auth_hub_image(self):
        image = 'username/image'
        assert auth.resolve_authconfig(
            self.auth_config, auth.resolve_repository_name(image)[0]
        )['username'] == 'indexuser'

    def test_resolve_registry_and_auth_explicit_hub(self):
        image = 'docker.io/username/image'
        assert auth.resolve_authconfig(
            self.auth_config, auth.resolve_repository_name(image)[0]
        )['username'] == 'indexuser'

    def test_resolve_registry_and_auth_explicit_legacy_hub(self):
        image = 'index.docker.io/username/image'
        assert auth.resolve_authconfig(
            self.auth_config, auth.resolve_repository_name(image)[0]
        )['username'] == 'indexuser'

    def test_resolve_registry_and_auth_private_registry(self):
        image = 'my.registry.net/image'
        assert auth.resolve_authconfig(
            self.auth_config, auth.resolve_repository_name(image)[0]
        )['username'] == 'privateuser'

    def test_resolve_registry_and_auth_unauthenticated_registry(self):
        image = 'other.registry.net/image'
        assert auth.resolve_authconfig(
            self.auth_config, auth.resolve_repository_name(image)[0]
        ) is None

    def test_resolve_auth_with_empty_credstore_and_auth_dict(self):
        auth_config = auth.AuthConfig({
            'auths': auth.parse_auth({
                'https://index.docker.io/v1/': self.index_config,
            }),
            'credsStore': 'blackbox'
        })
        with mock.patch(
            'docker.auth.AuthConfig._resolve_authconfig_credstore'
        ) as m:
            m.return_value = None
            assert 'indexuser' == auth.resolve_authconfig(
                auth_config, None
            )['username']


class LoadConfigTest(unittest.TestCase):
    def test_load_config_no_file(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg = auth.load_config(folder)
        assert cfg is not None

    def test_load_legacy_config(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg_path = os.path.join(folder, '.dockercfg')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        with open(cfg_path, 'w') as f:
            f.write(f'auth = {auth_}\n')
            f.write('email = sakuya@scarlet.net')

        cfg = auth.load_config(cfg_path)
        assert auth.resolve_authconfig(cfg) is not None
        assert cfg.auths[auth.INDEX_NAME] is not None
        cfg = cfg.auths[auth.INDEX_NAME]
        assert cfg['username'] == 'sakuya'
        assert cfg['password'] == 'izayoi'
        assert cfg['email'] == 'sakuya@scarlet.net'
        assert cfg.get('Auth') is None

    def test_load_json_config(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg_path = os.path.join(folder, '.dockercfg')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        email = 'sakuya@scarlet.net'
        with open(cfg_path, 'w') as f:
            json.dump(
                {auth.INDEX_URL: {'auth': auth_, 'email': email}}, f
            )
        cfg = auth.load_config(cfg_path)
        assert auth.resolve_authconfig(cfg) is not None
        assert cfg.auths[auth.INDEX_URL] is not None
        cfg = cfg.auths[auth.INDEX_URL]
        assert cfg['username'] == 'sakuya'
        assert cfg['password'] == 'izayoi'
        assert cfg['email'] == email
        assert cfg.get('Auth') is None

    def test_load_modern_json_config(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        cfg_path = os.path.join(folder, 'config.json')
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        email = 'sakuya@scarlet.net'
        with open(cfg_path, 'w') as f:
            json.dump({
                'auths': {
                    auth.INDEX_URL: {
                        'auth': auth_, 'email': email
                    }
                }
            }, f)
        cfg = auth.load_config(cfg_path)
        assert auth.resolve_authconfig(cfg) is not None
        assert cfg.auths[auth.INDEX_URL] is not None
        cfg = cfg.auths[auth.INDEX_URL]
        assert cfg['username'] == 'sakuya'
        assert cfg['password'] == 'izayoi'
        assert cfg['email'] == email

    def test_load_config_with_random_name(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder,
                                      '.{}.dockercfg'.format(
                                          random.randrange(100000)))
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            registry: {
                'auth': f'{auth_}',
                'email': 'sakuya@scarlet.net'
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        cfg = auth.load_config(dockercfg_path).auths
        assert registry in cfg
        assert cfg[registry] is not None
        cfg = cfg[registry]
        assert cfg['username'] == 'sakuya'
        assert cfg['password'] == 'izayoi'
        assert cfg['email'] == 'sakuya@scarlet.net'
        assert cfg.get('auth') is None

    def test_load_config_custom_config_env(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder, 'config.json')
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            registry: {
                'auth': f'{auth_}',
                'email': 'sakuya@scarlet.net'
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = auth.load_config(None).auths
            assert registry in cfg
            assert cfg[registry] is not None
            cfg = cfg[registry]
            assert cfg['username'] == 'sakuya'
            assert cfg['password'] == 'izayoi'
            assert cfg['email'] == 'sakuya@scarlet.net'
            assert cfg.get('auth') is None

    def test_load_config_custom_config_env_with_auths(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)

        dockercfg_path = os.path.join(folder, 'config.json')
        registry = 'https://your.private.registry.io'
        auth_ = base64.b64encode(b'sakuya:izayoi').decode('ascii')
        config = {
            'auths': {
                registry: {
                    'auth': f'{auth_}',
                    'email': 'sakuya@scarlet.net'
                }
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = auth.load_config(None)
            assert registry in cfg.auths
            cfg = cfg.auths[registry]
            assert cfg['username'] == 'sakuya'
            assert cfg['password'] == 'izayoi'
            assert cfg['email'] == 'sakuya@scarlet.net'
            assert cfg.get('auth') is None

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
                    'auth': f'{auth_}',
                    'email': 'sakuya@scarlet.net'
                }
            }
        }

        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        with mock.patch.dict(os.environ, {'DOCKER_CONFIG': folder}):
            cfg = auth.load_config(None)
            assert registry in cfg.auths
            cfg = cfg.auths[registry]
            assert cfg['username'] == b'sakuya\xc3\xa6'.decode('utf8')
            assert cfg['password'] == b'izayoi\xc3\xa6'.decode('utf8')
            assert cfg['email'] == 'sakuya@scarlet.net'
            assert cfg.get('auth') is None

    def test_load_config_unknown_keys(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, 'config.json')
        config = {
            'detachKeys': 'ctrl-q, ctrl-u, ctrl-i'
        }
        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        cfg = auth.load_config(dockercfg_path)
        assert dict(cfg) == {'auths': {}}

    def test_load_config_invalid_auth_dict(self):
        folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, 'config.json')
        config = {
            'auths': {
                'scarlet.net': {'sakuya': 'izayoi'}
            }
        }
        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        cfg = auth.load_config(dockercfg_path)
        assert dict(cfg) == {'auths': {'scarlet.net': {}}}

    def test_load_config_identity_token(self):
        folder = tempfile.mkdtemp()
        registry = 'scarlet.net'
        token = '1ce1cebb-503e-7043-11aa-7feb8bd4a1ce'
        self.addCleanup(shutil.rmtree, folder)
        dockercfg_path = os.path.join(folder, 'config.json')
        auth_entry = encode_auth({'username': 'sakuya'}).decode('ascii')
        config = {
            'auths': {
                registry: {
                    'auth': auth_entry,
                    'identitytoken': token
                }
            }
        }
        with open(dockercfg_path, 'w') as f:
            json.dump(config, f)

        cfg = auth.load_config(dockercfg_path)
        assert registry in cfg.auths
        cfg = cfg.auths[registry]
        assert 'IdentityToken' in cfg
        assert cfg['IdentityToken'] == token


class CredstoreTest(unittest.TestCase):
    def setUp(self):
        self.authconfig = auth.AuthConfig({'credsStore': 'default'})
        self.default_store = InMemoryStore('default')
        self.authconfig._stores['default'] = self.default_store
        self.default_store.store(
            'https://gensokyo.jp/v2', 'sakuya', 'izayoi',
        )
        self.default_store.store(
            'https://default.com/v2', 'user', 'hunter2',
        )

    def test_get_credential_store(self):
        auth_config = auth.AuthConfig({
            'credHelpers': {
                'registry1.io': 'truesecret',
                'registry2.io': 'powerlock'
            },
            'credsStore': 'blackbox',
        })

        assert auth_config.get_credential_store('registry1.io') == 'truesecret'
        assert auth_config.get_credential_store('registry2.io') == 'powerlock'
        assert auth_config.get_credential_store('registry3.io') == 'blackbox'

    def test_get_credential_store_no_default(self):
        auth_config = auth.AuthConfig({
            'credHelpers': {
                'registry1.io': 'truesecret',
                'registry2.io': 'powerlock'
            },
        })
        assert auth_config.get_credential_store('registry2.io') == 'powerlock'
        assert auth_config.get_credential_store('registry3.io') is None

    def test_get_credential_store_default_index(self):
        auth_config = auth.AuthConfig({
            'credHelpers': {
                'https://index.docker.io/v1/': 'powerlock'
            },
            'credsStore': 'truesecret'
        })

        assert auth_config.get_credential_store(None) == 'powerlock'
        assert auth_config.get_credential_store('docker.io') == 'powerlock'
        assert auth_config.get_credential_store('images.io') == 'truesecret'

    def test_get_credential_store_with_plain_dict(self):
        auth_config = {
            'credHelpers': {
                'registry1.io': 'truesecret',
                'registry2.io': 'powerlock'
            },
            'credsStore': 'blackbox',
        }

        assert auth.get_credential_store(
            auth_config, 'registry1.io'
        ) == 'truesecret'
        assert auth.get_credential_store(
            auth_config, 'registry2.io'
        ) == 'powerlock'
        assert auth.get_credential_store(
            auth_config, 'registry3.io'
        ) == 'blackbox'

    def test_get_all_credentials_credstore_only(self):
        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
        }

    def test_get_all_credentials_with_empty_credhelper(self):
        self.authconfig['credHelpers'] = {
            'registry1.io': 'truesecret',
        }
        self.authconfig._stores['truesecret'] = InMemoryStore()
        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'registry1.io': None,
        }

    def test_get_all_credentials_with_credhelpers_only(self):
        del self.authconfig['credsStore']
        assert self.authconfig.get_all_credentials() == {}

        self.authconfig['credHelpers'] = {
            'https://gensokyo.jp/v2': 'default',
            'https://default.com/v2': 'default',
        }

        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
        }

    def test_get_all_credentials_with_auths_entries(self):
        self.authconfig.add_auth('registry1.io', {
            'ServerAddress': 'registry1.io',
            'Username': 'reimu',
            'Password': 'hakurei',
        })

        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'registry1.io': {
                'ServerAddress': 'registry1.io',
                'Username': 'reimu',
                'Password': 'hakurei',
            },
        }

    def test_get_all_credentials_with_empty_auths_entry(self):
        self.authconfig.add_auth('default.com', {})

        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
        }

    def test_get_all_credentials_credstore_overrides_auth_entry(self):
        self.authconfig.add_auth('default.com', {
            'Username': 'shouldnotsee',
            'Password': 'thisentry',
            'ServerAddress': 'https://default.com/v2',
        })

        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
        }

    def test_get_all_credentials_helpers_override_default(self):
        self.authconfig['credHelpers'] = {
            'https://default.com/v2': 'truesecret',
        }
        truesecret = InMemoryStore('truesecret')
        truesecret.store('https://default.com/v2', 'reimu', 'hakurei')
        self.authconfig._stores['truesecret'] = truesecret
        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'reimu',
                'Password': 'hakurei',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'reimu',
                'Password': 'hakurei',
                'ServerAddress': 'https://default.com/v2',
            },
        }

    def test_get_all_credentials_3_sources(self):
        self.authconfig['credHelpers'] = {
            'registry1.io': 'truesecret',
        }
        truesecret = InMemoryStore('truesecret')
        truesecret.store('registry1.io', 'reimu', 'hakurei')
        self.authconfig._stores['truesecret'] = truesecret
        self.authconfig.add_auth('registry2.io', {
            'ServerAddress': 'registry2.io',
            'Username': 'reimu',
            'Password': 'hakurei',
        })

        assert self.authconfig.get_all_credentials() == {
            'https://gensokyo.jp/v2': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'gensokyo.jp': {
                'Username': 'sakuya',
                'Password': 'izayoi',
                'ServerAddress': 'https://gensokyo.jp/v2',
            },
            'https://default.com/v2': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'default.com': {
                'Username': 'user',
                'Password': 'hunter2',
                'ServerAddress': 'https://default.com/v2',
            },
            'registry1.io': {
                'ServerAddress': 'registry1.io',
                'Username': 'reimu',
                'Password': 'hakurei',
            },
            'registry2.io': {
                'ServerAddress': 'registry2.io',
                'Username': 'reimu',
                'Password': 'hakurei',
            }
        }


class InMemoryStore(credentials.Store):
    def __init__(self, *args, **kwargs):
        self.__store = {}

    def get(self, server):
        try:
            return self.__store[server]
        except KeyError:
            raise credentials.errors.CredentialsNotFound()

    def store(self, server, username, secret):
        self.__store[server] = {
            'ServerURL': server,
            'Username': username,
            'Secret': secret,
        }

    def list(self):
        return {
            k: v['Username'] for k, v in self.__store.items()
        }

    def erase(self, server):
        del self.__store[server]
