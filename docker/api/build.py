import logging
import os
import re
import json

from .. import constants
from .. import errors
from .. import auth
from .. import utils


log = logging.getLogger(__name__)


class BuildApiMixin(object):
    def build(self, path=None, tag=None, quiet=False, fileobj=None,
              nocache=False, rm=False, stream=False, timeout=None,
              custom_context=False, encoding=None, pull=False,
              forcerm=False, dockerfile=None, container_limits=None,
              decode=False, buildargs=None):
        remote = context = headers = None
        container_limits = container_limits or {}
        if path is None and fileobj is None:
            raise TypeError("Either path or fileobj needs to be provided.")

        for key in container_limits.keys():
            if key not in constants.CONTAINER_LIMITS_KEYS:
                raise errors.DockerException(
                    'Invalid container_limits key {0}'.format(key)
                )

        if custom_context:
            if not fileobj:
                raise TypeError("You must specify fileobj with custom_context")
            context = fileobj
        elif fileobj is not None:
            context = utils.mkbuildcontext(fileobj)
        elif path.startswith(('http://', 'https://',
                              'git://', 'github.com/', 'git@')):
            remote = path
        elif not os.path.isdir(path):
            raise TypeError("You must specify a directory to build in path")
        else:
            dockerignore = os.path.join(path, '.dockerignore')
            exclude = None
            if os.path.exists(dockerignore):
                with open(dockerignore, 'r') as f:
                    exclude = list(filter(bool, f.read().splitlines()))
            context = utils.tar(path, exclude=exclude, dockerfile=dockerfile)

        if utils.compare_version('1.8', self._version) >= 0:
            stream = True

        if dockerfile and utils.compare_version('1.17', self._version) < 0:
            raise errors.InvalidVersion(
                'dockerfile was only introduced in API version 1.17'
            )

        if utils.compare_version('1.19', self._version) < 0:
            pull = 1 if pull else 0

        u = self._url('/build')
        params = {
            't': tag,
            'remote': remote,
            'q': quiet,
            'nocache': nocache,
            'rm': rm,
            'forcerm': forcerm,
            'pull': pull,
            'dockerfile': dockerfile,
        }
        params.update(container_limits)

        if buildargs:
            if utils.version_gte(self._version, '1.21'):
                params.update({'buildargs': json.dumps(buildargs)})
            else:
                raise errors.InvalidVersion(
                    'buildargs was only introduced in API version 1.21'
                )

        if context is not None:
            headers = {'Content-Type': 'application/tar'}
            if encoding:
                headers['Content-Encoding'] = encoding

        if utils.compare_version('1.9', self._version) >= 0:
            self._set_auth_headers(headers)

        response = self._post(
            u,
            data=context,
            params=params,
            headers=headers,
            stream=stream,
            timeout=timeout,
        )

        if context is not None and not custom_context:
            context.close()

        if stream:
            return self._stream_helper(response, decode=decode)
        else:
            output = self._result(response)
            srch = r'Successfully built ([0-9a-f]+)'
            match = re.search(srch, output)
            if not match:
                return None, output
            return match.group(1), output

    def _set_auth_headers(self, headers):
        log.debug('Looking for auth config')

        # If we don't have any auth data so far, try reloading the config
        # file one more time in case anything showed up in there.
        if not self._auth_configs:
            log.debug("No auth config in memory - loading from filesystem")
            self._auth_configs = auth.load_config()

        # Send the full auth configuration (if any exists), since the build
        # could use any (or all) of the registries.
        if self._auth_configs:
            log.debug(
                'Sending auth config ({0})'.format(
                    ', '.join(repr(k) for k in self._auth_configs.keys())
                )
            )
            if headers is None:
                headers = {}
            if utils.compare_version('1.19', self._version) >= 0:
                headers['X-Registry-Config'] = auth.encode_header(
                    self._auth_configs
                )
            else:
                headers['X-Registry-Config'] = auth.encode_header({
                    'configs': self._auth_configs
                })
        else:
            log.debug('No auth config found')
