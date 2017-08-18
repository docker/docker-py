import json
import logging
import os
import re

from .. import auth
from .. import constants
from .. import errors
from .. import utils


log = logging.getLogger(__name__)


class BuildApiMixin(object):
    def build(self, path=None, tag=None, quiet=False, fileobj=None,
              nocache=False, rm=False, stream=False, timeout=None,
              custom_context=False, encoding=None, pull=False,
              forcerm=False, dockerfile=None, container_limits=None,
              decode=False, buildargs=None, gzip=False, shmsize=None,
              labels=None, cache_from=None, target=None, network_mode=None,
              squash=None):
        """
        Similar to the ``docker build`` command. Either ``path`` or ``fileobj``
        needs to be set. ``path`` can be a local path (to a directory
        containing a Dockerfile) or a remote URL. ``fileobj`` must be a
        readable file-like object to a Dockerfile.

        If you have a tar file for the Docker build context (including a
        Dockerfile) already, pass a readable file-like object to ``fileobj``
        and also pass ``custom_context=True``. If the stream is compressed
        also, set ``encoding`` to the correct value (e.g ``gzip``).

        Example:
            >>> from io import BytesIO
            >>> from docker import APIClient
            >>> dockerfile = '''
            ... # Shared Volume
            ... FROM busybox:buildroot-2014.02
            ... VOLUME /data
            ... CMD ["/bin/sh"]
            ... '''
            >>> f = BytesIO(dockerfile.encode('utf-8'))
            >>> cli = APIClient(base_url='tcp://127.0.0.1:2375')
            >>> response = [line for line in cli.build(
            ...     fileobj=f, rm=True, tag='yourname/volume'
            ... )]
            >>> response
            ['{"stream":" ---\\u003e a9eb17255234\\n"}',
             '{"stream":"Step 1 : VOLUME /data\\n"}',
             '{"stream":" ---\\u003e Running in abdc1e6896c6\\n"}',
             '{"stream":" ---\\u003e 713bca62012e\\n"}',
             '{"stream":"Removing intermediate container abdc1e6896c6\\n"}',
             '{"stream":"Step 2 : CMD [\\"/bin/sh\\"]\\n"}',
             '{"stream":" ---\\u003e Running in dba30f2a1a7e\\n"}',
             '{"stream":" ---\\u003e 032b8b2855fc\\n"}',
             '{"stream":"Removing intermediate container dba30f2a1a7e\\n"}',
             '{"stream":"Successfully built 032b8b2855fc\\n"}']

        Args:
            path (str): Path to the directory containing the Dockerfile
            fileobj: A file object to use as the Dockerfile. (Or a file-like
                object)
            tag (str): A tag to add to the final image
            quiet (bool): Whether to return the status
            nocache (bool): Don't use the cache when set to ``True``
            rm (bool): Remove intermediate containers. The ``docker build``
                command now defaults to ``--rm=true``, but we have kept the old
                default of `False` to preserve backward compatibility
            stream (bool): *Deprecated for API version > 1.8 (always True)*.
                Return a blocking generator you can iterate over to retrieve
                build output as it happens
            timeout (int): HTTP timeout
            custom_context (bool): Optional if using ``fileobj``
            encoding (str): The encoding for a stream. Set to ``gzip`` for
                compressing
            pull (bool): Downloads any updates to the FROM image in Dockerfiles
            forcerm (bool): Always remove intermediate containers, even after
                unsuccessful builds
            dockerfile (str): path within the build context to the Dockerfile
            buildargs (dict): A dictionary of build arguments
            container_limits (dict): A dictionary of limits applied to each
                container created by the build process. Valid keys:

                - memory (int): set memory limit for build
                - memswap (int): Total memory (memory + swap), -1 to disable
                    swap
                - cpushares (int): CPU shares (relative weight)
                - cpusetcpus (str): CPUs in which to allow execution, e.g.,
                    ``"0-3"``, ``"0,1"``
            decode (bool): If set to ``True``, the returned stream will be
                decoded into dicts on the fly. Default ``False``
            shmsize (int): Size of `/dev/shm` in bytes. The size must be
                greater than 0. If omitted the system uses 64MB
            labels (dict): A dictionary of labels to set on the image
            cache_from (list): A list of images used for build cache
                resolution
            target (str): Name of the build-stage to build in a multi-stage
                Dockerfile
            network_mode (str): networking mode for the run commands during
                build
            squash (bool): Squash the resulting images layers into a
                single layer.

        Returns:
            A generator for the build output.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
            ``TypeError``
                If neither ``path`` nor ``fileobj`` is specified.
        """
        remote = context = None
        headers = {}
        container_limits = container_limits or {}
        if path is None and fileobj is None:
            raise TypeError("Either path or fileobj needs to be provided.")
        if gzip and encoding is not None:
            raise errors.DockerException(
                'Can not use custom encoding if gzip is enabled'
            )

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
            context = utils.tar(
                path, exclude=exclude, dockerfile=dockerfile, gzip=gzip
            )
            encoding = 'gzip' if gzip else encoding

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

        if shmsize:
            if utils.version_gte(self._version, '1.22'):
                params.update({'shmsize': shmsize})
            else:
                raise errors.InvalidVersion(
                    'shmsize was only introduced in API version 1.22'
                )

        if labels:
            if utils.version_gte(self._version, '1.23'):
                params.update({'labels': json.dumps(labels)})
            else:
                raise errors.InvalidVersion(
                    'labels was only introduced in API version 1.23'
                )

        if cache_from:
            if utils.version_gte(self._version, '1.25'):
                params.update({'cachefrom': json.dumps(cache_from)})
            else:
                raise errors.InvalidVersion(
                    'cache_from was only introduced in API version 1.25'
                )

        if target:
            if utils.version_gte(self._version, '1.29'):
                params.update({'target': target})
            else:
                raise errors.InvalidVersion(
                    'target was only introduced in API version 1.29'
                )

        if network_mode:
            if utils.version_gte(self._version, '1.25'):
                params.update({'networkmode': network_mode})
            else:
                raise errors.InvalidVersion(
                    'network_mode was only introduced in API version 1.25'
                )

        if squash:
            if utils.version_gte(self._version, '1.25'):
                params.update({'squash': squash})
            else:
                raise errors.InvalidVersion(
                    'squash was only introduced in API version 1.25'
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
            auth_data = {}
            if self._auth_configs.get('credsStore'):
                # Using a credentials store, we need to retrieve the
                # credentials for each registry listed in the config.json file
                # Matches CLI behavior: https://github.com/docker/docker/blob/
                # 67b85f9d26f1b0b2b240f2d794748fac0f45243c/cliconfig/
                # credentials/native_store.go#L68-L83
                for registry in self._auth_configs.keys():
                    if registry == 'credsStore' or registry == 'HttpHeaders':
                        continue
                    auth_data[registry] = auth.resolve_authconfig(
                        self._auth_configs, registry
                    )
            else:
                auth_data = self._auth_configs.copy()
                # See https://github.com/docker/docker-py/issues/1683
                if auth.INDEX_NAME in auth_data:
                    auth_data[auth.INDEX_URL] = auth_data[auth.INDEX_NAME]

            log.debug(
                'Sending auth config ({0})'.format(
                    ', '.join(repr(k) for k in auth_data.keys())
                )
            )

            if utils.compare_version('1.19', self._version) >= 0:
                headers['X-Registry-Config'] = auth.encode_header(
                    auth_data
                )
            else:
                headers['X-Registry-Config'] = auth.encode_header({
                    'configs': auth_data
                })
        else:
            log.debug('No auth config found')
