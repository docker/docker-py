import os
import warnings
from datetime import datetime

from ..auth import auth
from ..constants import INSECURE_REGISTRY_DEPRECATION_WARNING
from ..utils import utils


class DaemonApiMixin(object):
    def events(self, since=None, until=None, filters=None, decode=None):
        if isinstance(since, datetime):
            since = utils.datetime_to_timestamp(since)

        if isinstance(until, datetime):
            until = utils.datetime_to_timestamp(until)

        if filters:
            filters = utils.convert_filters(filters)

        params = {
            'since': since,
            'until': until,
            'filters': filters
        }

        return self._stream_helper(
            self.get(self._url('/events'), params=params, stream=True),
            decode=decode
        )

    def info(self):
        return self._result(self._get(self._url("/info")), True)

    def login(self, username, password=None, email=None, registry=None,
              reauth=False, insecure_registry=False, dockercfg_path=None):
        if insecure_registry:
            warnings.warn(
                INSECURE_REGISTRY_DEPRECATION_WARNING.format('login()'),
                DeprecationWarning
            )

        # If we don't have any auth data so far, try reloading the config file
        # one more time in case anything showed up in there.
        # If dockercfg_path is passed check to see if the config file exists,
        # if so load that config.
        if dockercfg_path and os.path.exists(dockercfg_path):
            self._auth_configs = auth.load_config(dockercfg_path)
        elif not self._auth_configs:
            self._auth_configs = auth.load_config()

        registry = registry or auth.INDEX_URL

        authcfg = auth.resolve_authconfig(self._auth_configs, registry)
        # If we found an existing auth config for this registry and username
        # combination, we can return it immediately unless reauth is requested.
        if authcfg and authcfg.get('username', None) == username \
                and not reauth:
            return authcfg

        req_data = {
            'username': username,
            'password': password,
            'email': email,
            'serveraddress': registry,
        }

        response = self._post_json(self._url('/auth'), data=req_data)
        if response.status_code == 200:
            self._auth_configs[registry] = req_data
        return self._result(response, json=True)

    def ping(self):
        return self._result(self._get(self._url('/_ping')))

    def version(self, api_version=True):
        url = self._url("/version", versioned_api=api_version)
        return self._result(self._get(url), json=True)
