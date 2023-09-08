from __future__ import annotations
import base64
import json
import logging
from typing import Any, AnyStr, Tuple, Dict, Optional, Union, cast

from . import credentials
from . import errors
from .api.client import APIClient
from .utils import config

INDEX_NAME = 'docker.io'
INDEX_URL = f'https://index.{INDEX_NAME}/v1/'
TOKEN_USERNAME = '<token>'

log = logging.getLogger(__name__)


def resolve_repository_name(repo_name: str) -> Tuple[str, str]:
    if '://' in repo_name:
        raise errors.InvalidRepository(
            f'Repository name cannot contain a scheme ({repo_name})'
        )

    index_name, remote_name = split_repo_name(repo_name)
    if index_name[0] == '-' or index_name[-1] == '-':
        raise errors.InvalidRepository(
            f'Invalid index name ({index_name}). '
            'Cannot begin or end with a hyphen.'
        )
    return resolve_index_name(index_name), remote_name


def resolve_index_name(index_name: str) -> str:
    index_name = convert_to_hostname(index_name)
    if index_name == f"index.{INDEX_NAME}":
        index_name = INDEX_NAME
    return index_name


def get_config_header(client: APIClient, registry: str) -> Optional[bytes]:
    log.debug('Looking for auth config')
    if not client._auth_configs or client._auth_configs.is_empty:
        log.debug(
            "No auth config in memory - loading from filesystem"
        )
        client._auth_configs = load_config(credstore_env=client.credstore_env)
    authcfg = resolve_authconfig(
        client._auth_configs, registry, credstore_env=client.credstore_env
    )
    # Do not fail here if no authentication exists for this
    # specific registry as we can have a readonly pull. Just
    # put the header if we can.
    if authcfg:
        log.debug('Found auth config')
        # auth_config needs to be a dict in the format used by
        # auth.py username , password, serveraddress, email
        return encode_header(authcfg)
    log.debug('No auth config found')
    return None


def split_repo_name(repo_name: str) -> Tuple[str, str]:
    parts = repo_name.split('/', 1)
    if len(parts) == 1 or (
        '.' not in parts[0] and ':' not in parts[0] and parts[0] != 'localhost'
    ):
        # This is a docker index repo (ex: username/foobar or ubuntu)
        return INDEX_NAME, repo_name
    return tuple(parts)  # type: ignore[return-value]


def get_credential_store(authconfig, registry):
    if not isinstance(authconfig, AuthConfig):
        authconfig = AuthConfig(authconfig)
    return authconfig.get_credential_store(registry)


class AuthConfig(dict):
    def __init__(self, dct: Dict[str, Any], credstore_env: Optional[Dict[str, Any]] = None) -> None:
        if 'auths' not in dct:
            dct['auths'] = {}
        self.update(dct)
        self._credstore_env = credstore_env
        self._stores: Dict[str, credentials.Store] = {}

    @classmethod
    def parse_auth(cls, entries: Dict[str, Any], raise_on_error: bool = False) -> Dict[str, Any]:
        """
        Parses authentication entries

        Args:
          entries:        Dict of authentication entries.
          raise_on_error: If set to true, an invalid format will raise
                          InvalidConfigFile

        Returns:
          Authentication registry.
        """

        conf = {}
        for registry, entry in entries.items():
            if not isinstance(entry, dict):
                log.debug(
                    f'Config entry for key {registry} is not auth config'
                )
                # We sometimes fall back to parsing the whole config as if it
                # was the auth config by itself, for legacy purposes. In that
                # case, we fail silently and return an empty conf if any of the
                # keys is not formatted properly.
                if raise_on_error:
                    raise errors.InvalidConfigFile(
                        f'Invalid configuration for registry {registry}'
                    )
                return {}
            if 'identitytoken' in entry:
                log.debug(f'Found an IdentityToken entry for registry {registry}')
                conf[registry] = {
                    'IdentityToken': entry['identitytoken']
                }
                continue  # Other values are irrelevant if we have a token

            if 'auth' not in entry:
                # Starting with engine v1.11 (API 1.23), an empty dictionary is
                # a valid value in the auths config.
                # https://github.com/docker/compose/issues/3265
                log.debug(
                    f'Auth data for {registry} is absent. '
                    f'Client might be using a credentials store instead.'
                )
                conf[registry] = {}
                continue

            username, password = decode_auth(entry['auth'])
            log.debug(
                f'Found entry (registry={registry!r}, username={username!r})'
            )

            conf[registry] = {
                'username': username,
                'password': password,
                'email': entry.get('email'),
                'serveraddress': registry,
            }
        return conf

    @classmethod
    def load_config(cls, config_path: Optional[str], config_dict: Optional[Dict[str, Any]], credstore_env: Optional[Dict[str, Any]] = None) -> AuthConfig:
        """
        Loads authentication data from a Docker configuration file in the given
        root directory or if config_path is passed use given path.
        Lookup priority:
            explicit config_path parameter > DOCKER_CONFIG environment
            variable > ~/.docker/config.json > ~/.dockercfg
        """

        if not config_dict:
            config_file = config.find_config_file(config_path)

            if not config_file:
                return cls({}, credstore_env)
            try:
                with open(config_file) as f:
                    config_dict = cast(Dict[str, Any], json.load(f))
            except (OSError, KeyError, ValueError) as e:
                # Likely missing new Docker config file or it's in an
                # unknown format, continue to attempt to read old location
                # and format.
                log.debug(e)
                return cls(_load_legacy_config(config_file), credstore_env)

        res = {}
        if config_dict.get('auths'):
            log.debug("Found 'auths' section")
            res.update({
                'auths': cls.parse_auth(
                    config_dict.pop('auths'), raise_on_error=True
                )
            })
        if config_dict.get('credsStore'):
            log.debug("Found 'credsStore' section")
            res.update({'credsStore': config_dict.pop('credsStore')})
        if config_dict.get('credHelpers'):
            log.debug("Found 'credHelpers' section")
            res.update({'credHelpers': config_dict.pop('credHelpers')})
        if res:
            return cls(res, credstore_env)

        log.debug(
            "Couldn't find auth-related section ; attempting to interpret "
            "as auth-only file"
        )
        return cls({'auths': cls.parse_auth(config_dict)}, credstore_env)

    @property
    def auths(self) -> Dict[str, Any]:
        return self.get('auths', {})

    @property
    def creds_store(self) -> Optional[str]:
        return self.get('credsStore', None)

    @property
    def cred_helpers(self) -> Dict[str, Any]:
        return self.get('credHelpers', {})

    @property
    def is_empty(self) -> bool:
        return (
            not self.auths and not self.creds_store and not self.cred_helpers
        )

    def resolve_authconfig(self, registry: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Returns the authentication data from the given auth configuration for a
        specific registry. As with the Docker client, legacy entries in the
        config with full URLs are stripped down to hostnames before checking
        for a match. Returns None if no match was found.
        """

        if self.creds_store or self.cred_helpers:
            store_name = self.get_credential_store(registry)
            if store_name is not None:
                log.debug(
                    f'Using credentials store "{store_name}"'
                )
                cfg = self._resolve_authconfig_credstore(registry, store_name)
                if cfg is not None:
                    return cfg
                log.debug('No entry in credstore - fetching from auth dict')

        # Default to the public index server
        registry = resolve_index_name(registry) if registry else INDEX_NAME
        log.debug(f"Looking for auth entry for {repr(registry)}")

        if registry in self.auths:
            log.debug(f"Found {repr(registry)}")
            return self.auths[registry]

        for key, conf in self.auths.items():
            if resolve_index_name(key) == registry:
                log.debug(f"Found {repr(key)}")
                return conf

        log.debug("No entry found")
        return None

    def _resolve_authconfig_credstore(self, registry: Optional[str], credstore_name: str) -> Optional[Dict[str, Any]]:
        if not registry or registry == INDEX_NAME:
            # The ecosystem is a little schizophrenic with index.docker.io VS
            # docker.io - in that case, it seems the full URL is necessary.
            registry = INDEX_URL
        log.debug(f"Looking for auth entry for {repr(registry)}")
        store = self._get_store_instance(credstore_name)
        try:
            data = store.get(registry)
            res = {
                'ServerAddress': registry,
            }
            if data['Username'] == TOKEN_USERNAME:
                res['IdentityToken'] = data['Secret']
            else:
                res.update({
                    'Username': data['Username'],
                    'Password': data['Secret'],
                })
            return res
        except credentials.CredentialsNotFound:
            log.debug('No entry found')
            return None
        except credentials.StoreError as e:
            raise errors.DockerException(
                f'Credentials store error: {repr(e)}'
            ) from e

    def _get_store_instance(self, name: str) -> credentials.Store:
        if name not in self._stores:
            self._stores[name] = credentials.Store(
                name, environment=self._credstore_env
            )
        return self._stores[name]

    def get_credential_store(self, registry: Optional[str]) -> Optional[str]:
        if not registry or registry == INDEX_NAME:
            registry = INDEX_URL

        return self.cred_helpers.get(registry) or self.creds_store

    def get_all_credentials(self) -> Dict[str, Any]:
        auth_data = self.auths.copy()
        if self.creds_store:
            # Retrieve all credentials from the default store
            store = self._get_store_instance(self.creds_store)
            for k in store.list().keys():
                auth_data[k] = self._resolve_authconfig_credstore(
                    k, self.creds_store
                )
                auth_data[convert_to_hostname(k)] = auth_data[k]

        # credHelpers entries take priority over all others
        for reg, store_name in self.cred_helpers.items():
            auth_data[reg] = self._resolve_authconfig_credstore(
                reg, store_name
            )
            auth_data[convert_to_hostname(reg)] = auth_data[reg]

        return auth_data

    def add_auth(self, reg: str, data: Any) -> None:
        self['auths'][reg] = data


def resolve_authconfig(authconfig: Union[AuthConfig, Dict[str, Any]], registry: Optional[str] = None, credstore_env: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    if not isinstance(authconfig, AuthConfig):
        authconfig = AuthConfig(authconfig, credstore_env)
    return authconfig.resolve_authconfig(registry)


def convert_to_hostname(url: str) -> str:
    return url.replace('http://', '').replace('https://', '').split('/', 1)[0]


def decode_auth(auth: AnyStr) -> Tuple[str, str]:
    if isinstance(auth, str):
        auth_bytes = auth.encode('ascii')
    else:
        auth_bytes = auth
    s = base64.b64decode(auth_bytes)
    login, pwd = s.split(b':', 1)
    return login.decode('utf8'), pwd.decode('utf8')


def encode_header(auth: Dict[str, Any]) -> bytes:
    auth_json = json.dumps(auth).encode('ascii')
    return base64.urlsafe_b64encode(auth_json)


def parse_auth(entries: Dict[str, Any], raise_on_error: bool = False) -> Dict[str, Any]:
    """
    Parses authentication entries

    Args:
      entries:        Dict of authentication entries.
      raise_on_error: If set to true, an invalid format will raise
                      InvalidConfigFile

    Returns:
      Authentication registry.
    """

    return AuthConfig.parse_auth(entries, raise_on_error)


def load_config(config_path: Optional[str] = None, config_dict: Optional[Dict[str, Any]] = None, credstore_env: Optional[Dict[str, Any]] = None) -> AuthConfig:
    return AuthConfig.load_config(config_path, config_dict, credstore_env)


def _load_legacy_config(config_file: str) -> Dict[str, Any]:
    log.debug("Attempting to parse legacy auth file format")
    try:
        data = []
        with open(config_file) as f:
            for line in f.readlines():
                data.append(line.strip().split(' = ')[1])
            if len(data) < 2:
                # Not enough data
                raise errors.InvalidConfigFile(
                    'Invalid or empty configuration file!'
                )

        username, password = decode_auth(data[0])
        return {'auths': {
            INDEX_NAME: {
                'username': username,
                'password': password,
                'email': data[1],
                'serveraddress': INDEX_URL,
            }
        }}
    except Exception as e:
        log.debug(e)

    log.debug("All parsing attempts failed - returning empty config")
    return {}
