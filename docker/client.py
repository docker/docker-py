# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import json
import os
import re
import shlex
import struct
import warnings
from datetime import datetime

import requests
import requests.exceptions
import six

from . import constants
from . import errors
from .auth import auth
from .unixconn import unixconn
from .ssladapter import ssladapter
from .utils import utils, check_resource
from .tls import TLSConfig


if not six.PY3:
    import websocket


class Client(requests.Session):
    def __init__(self, base_url=None, version=None,
                 timeout=constants.DEFAULT_TIMEOUT_SECONDS, tls=False):
        super(Client, self).__init__()

        if tls and not base_url.startswith('https://'):
            raise errors.TLSParameterError(
                'If using TLS, the base_url argument must begin with '
                '"https://".')

        self.base_url = base_url
        self.timeout = timeout

        self._auth_configs = auth.load_config()

        base_url = utils.parse_host(base_url)
        if base_url.startswith('http+unix://'):
            unix_socket_adapter = unixconn.UnixAdapter(base_url, timeout)
            self.mount('http+docker://', unix_socket_adapter)
            self.base_url = 'http+docker://localunixsocket'
        else:
            # Use SSLAdapter for the ability to specify SSL version
            if isinstance(tls, TLSConfig):
                tls.configure_client(self)
            elif tls:
                self.mount('https://', ssladapter.SSLAdapter())
            self.base_url = base_url

        # version detection needs to be after unix adapter mounting
        if version is None:
            self._version = constants.DEFAULT_DOCKER_API_VERSION
        elif isinstance(version, six.string_types):
            if version.lower() == 'auto':
                self._version = self._retrieve_server_version()
            else:
                self._version = version
        else:
            raise errors.DockerException(
                'Version parameter must be a string or None. Found {0}'.format(
                    type(version).__name__
                )
            )

    def _retrieve_server_version(self):
        try:
            return self.version(api_version=False)["ApiVersion"]
        except KeyError:
            raise errors.DockerException(
                'Invalid response from docker daemon: key "ApiVersion"'
                ' is missing.'
            )
        except Exception as e:
            raise errors.DockerException(
                'Error while fetching server API version: {0}'.format(e)
            )

    def _set_request_timeout(self, kwargs):
        """Prepare the kwargs for an HTTP request by inserting the timeout
        parameter, if not already present."""
        kwargs.setdefault('timeout', self.timeout)
        return kwargs

    def _post(self, url, **kwargs):
        return self.post(url, **self._set_request_timeout(kwargs))

    def _get(self, url, **kwargs):
        return self.get(url, **self._set_request_timeout(kwargs))

    def _delete(self, url, **kwargs):
        return self.delete(url, **self._set_request_timeout(kwargs))

    def _url(self, path, versioned_api=True):
        if versioned_api:
            return '{0}/v{1}{2}'.format(self.base_url, self._version, path)
        else:
            return '{0}{1}'.format(self.base_url, path)

    def _raise_for_status(self, response, explanation=None):
        """Raises stored :class:`APIError`, if one occurred."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            raise errors.APIError(e, response, explanation=explanation)

    def _result(self, response, json=False, binary=False):
        assert not (json and binary)
        self._raise_for_status(response)

        if json:
            return response.json()
        if binary:
            return response.content
        return response.text

    def _post_json(self, url, data, **kwargs):
        # Go <1.1 can't unserialize null to a string
        # so we do this disgusting thing here.
        data2 = {}
        if data is not None:
            for k, v in six.iteritems(data):
                if v is not None:
                    data2[k] = v

        if 'headers' not in kwargs:
            kwargs['headers'] = {}
        kwargs['headers']['Content-Type'] = 'application/json'
        return self._post(url, data=json.dumps(data2), **kwargs)

    def _attach_params(self, override=None):
        return override or {
            'stdout': 1,
            'stderr': 1,
            'stream': 1
        }

    @check_resource
    def _attach_websocket(self, container, params=None):
        if six.PY3:
            raise NotImplementedError("This method is not currently supported "
                                      "under python 3")
        url = self._url("/containers/{0}/attach/ws".format(container))
        req = requests.Request("POST", url, params=self._attach_params(params))
        full_url = req.prepare().url
        full_url = full_url.replace("http://", "ws://", 1)
        full_url = full_url.replace("https://", "wss://", 1)
        return self._create_websocket_connection(full_url)

    def _create_websocket_connection(self, url):
        return websocket.create_connection(url)

    def _get_raw_response_socket(self, response):
        self._raise_for_status(response)
        if six.PY3:
            sock = response.raw._fp.fp.raw
        else:
            sock = response.raw._fp.fp._sock
        try:
            # Keep a reference to the response to stop it being garbage
            # collected. If the response is garbage collected, it will
            # close TLS sockets.
            sock._response = response
        except AttributeError:
            # UNIX sockets can't have attributes set on them, but that's
            # fine because we won't be doing TLS over them
            pass

        return sock

    def _stream_helper(self, response, decode=False):
        """Generator for data coming from a chunked-encoded HTTP response."""
        if response.raw._fp.chunked:
            reader = response.raw
            while not reader.closed:
                # this read call will block until we get a chunk
                data = reader.read(1)
                if not data:
                    break
                if reader._fp.chunk_left:
                    data += reader.read(reader._fp.chunk_left)
                if decode:
                    if six.PY3:
                        data = data.decode('utf-8')
                    data = json.loads(data)
                yield data
        else:
            # Response isn't chunked, meaning we probably
            # encountered an error immediately
            yield self._result(response)

    def _multiplexed_buffer_helper(self, response):
        """A generator of multiplexed data blocks read from a buffered
        response."""
        buf = self._result(response, binary=True)
        walker = 0
        while True:
            if len(buf[walker:]) < 8:
                break
            _, length = struct.unpack_from('>BxxxL', buf[walker:])
            start = walker + constants.STREAM_HEADER_SIZE_BYTES
            end = start + length
            walker = end
            yield buf[start:end]

    def _multiplexed_response_stream_helper(self, response):
        """A generator of multiplexed data blocks coming from a response
        stream."""

        # Disable timeout on the underlying socket to prevent
        # Read timed out(s) for long running processes
        socket = self._get_raw_response_socket(response)
        if six.PY3:
            socket._sock.settimeout(None)
        else:
            socket.settimeout(None)

        while True:
            header = response.raw.read(constants.STREAM_HEADER_SIZE_BYTES)
            if not header:
                break
            _, length = struct.unpack('>BxxxL', header)
            if not length:
                break
            data = response.raw.read(length)
            if not data:
                break
            yield data

    @property
    def api_version(self):
        return self._version

    @check_resource
    def attach(self, container, stdout=True, stderr=True,
               stream=False, logs=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {
            'logs': logs and 1 or 0,
            'stdout': stdout and 1 or 0,
            'stderr': stderr and 1 or 0,
            'stream': stream and 1 or 0,
        }
        u = self._url("/containers/{0}/attach".format(container))
        response = self._post(u, params=params, stream=stream)

        # Stream multi-plexing was only introduced in API v1.6. Anything before
        # that needs old-style streaming.
        if utils.compare_version('1.6', self._version) < 0:
            def stream_result():
                self._raise_for_status(response)
                for line in response.iter_lines(chunk_size=1,
                                                decode_unicode=True):
                    # filter out keep-alive new lines
                    if line:
                        yield line

            return stream_result() if stream else \
                self._result(response, binary=True)

        sep = bytes() if six.PY3 else str()

        if stream:
            return self._multiplexed_response_stream_helper(response)
        else:
            return sep.join(
                [x for x in self._multiplexed_buffer_helper(response)]
            )

    @check_resource
    def attach_socket(self, container, params=None, ws=False):
        if params is None:
            params = {
                'stdout': 1,
                'stderr': 1,
                'stream': 1
            }

        if ws:
            return self._attach_websocket(container, params)

        if isinstance(container, dict):
            container = container.get('Id')

        u = self._url("/containers/{0}/attach".format(container))
        return self._get_raw_response_socket(self.post(
            u, None, params=self._attach_params(params), stream=True))

    def build(self, path=None, tag=None, quiet=False, fileobj=None,
              nocache=False, rm=False, stream=False, timeout=None,
              custom_context=False, encoding=None, pull=True,
              forcerm=False, dockerfile=None, container_limits=None):
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
                              'git://', 'github.com/')):
            remote = path
        elif not os.path.isdir(path):
            raise TypeError("You must specify a directory to build in path")
        else:
            dockerignore = os.path.join(path, '.dockerignore')
            exclude = None
            if os.path.exists(dockerignore):
                with open(dockerignore, 'r') as f:
                    exclude = list(filter(bool, f.read().splitlines()))
                    # These are handled by the docker daemon and should not be
                    # excluded on the client
                    if 'Dockerfile' in exclude:
                        exclude.remove('Dockerfile')
                    if '.dockerignore' in exclude:
                        exclude.remove(".dockerignore")
            context = utils.tar(path, exclude=exclude)

        if utils.compare_version('1.8', self._version) >= 0:
            stream = True

        if dockerfile and utils.compare_version('1.17', self._version) < 0:
            raise errors.InvalidVersion(
                'dockerfile was only introduced in API version 1.17'
            )

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

        if context is not None:
            headers = {'Content-Type': 'application/tar'}
            if encoding:
                headers['Content-Encoding'] = encoding

        if utils.compare_version('1.9', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if not self._auth_configs:
                self._auth_configs = auth.load_config()

            # Send the full auth configuration (if any exists), since the build
            # could use any (or all) of the registries.
            if self._auth_configs:
                if headers is None:
                    headers = {}
                headers['X-Registry-Config'] = auth.encode_full_header(
                    self._auth_configs
                )

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
            return self._stream_helper(response)
        else:
            output = self._result(response)
            srch = r'Successfully built ([0-9a-f]+)'
            match = re.search(srch, output)
            if not match:
                return None, output
            return match.group(1), output

    @check_resource
    def commit(self, container, repository=None, tag=None, message=None,
               author=None, conf=None):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {
            'container': container,
            'repo': repository,
            'tag': tag,
            'comment': message,
            'author': author
        }
        u = self._url("/commit")
        return self._result(self._post_json(u, data=conf, params=params),
                            json=True)

    def containers(self, quiet=False, all=False, trunc=False, latest=False,
                   since=None, before=None, limit=-1, size=False,
                   filters=None):
        params = {
            'limit': 1 if latest else limit,
            'all': 1 if all else 0,
            'size': 1 if size else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        if filters:
            params['filters'] = utils.convert_filters(filters)
        u = self._url("/containers/json")
        res = self._result(self._get(u, params=params), True)

        if quiet:
            return [{'Id': x['Id']} for x in res]
        if trunc:
            for x in res:
                x['Id'] = x['Id'][:12]
        return res

    @check_resource
    def copy(self, container, resource):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._post_json(
            self._url("/containers/{0}/copy".format(container)),
            data={"Resource": resource},
            stream=True
        )
        self._raise_for_status(res)
        return res.raw

    def create_container(self, image, command=None, hostname=None, user=None,
                         detach=False, stdin_open=False, tty=False,
                         mem_limit=0, ports=None, environment=None, dns=None,
                         volumes=None, volumes_from=None,
                         network_disabled=False, name=None, entrypoint=None,
                         cpu_shares=None, working_dir=None, domainname=None,
                         memswap_limit=0, cpuset=None, host_config=None,
                         mac_address=None, labels=None):

        if isinstance(volumes, six.string_types):
            volumes = [volumes, ]

        if host_config and utils.compare_version('1.15', self._version) < 0:
            raise errors.InvalidVersion(
                'host_config is not supported in API < 1.15'
            )

        config = utils.create_container_config(
            self._version, image, command, hostname, user, detach, stdin_open,
            tty, mem_limit, ports, environment, dns, volumes, volumes_from,
            network_disabled, entrypoint, cpu_shares, working_dir, domainname,
            memswap_limit, cpuset, host_config, mac_address, labels
        )
        return self.create_container_from_config(config, name)

    def create_container_from_config(self, config, name=None):
        u = self._url("/containers/create")
        params = {
            'name': name
        }
        res = self._post_json(u, data=config, params=params)
        return self._result(res, True)

    @check_resource
    def diff(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(self._get(self._url("/containers/{0}/changes".
                            format(container))), True)

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

        return self._stream_helper(self.get(self._url('/events'),
                                            params=params, stream=True),
                                   decode=decode)

    @check_resource
    def execute(self, container, cmd, detach=False, stdout=True, stderr=True,
                stream=False, tty=False):
        warnings.warn(
            'Client.execute is being deprecated. Please use exec_create & '
            'exec_start instead', DeprecationWarning
        )
        create_res = self.exec_create(
            container, cmd, detach, stdout, stderr, tty
        )

        return self.exec_start(create_res, detach, tty, stream)

    def exec_create(self, container, cmd, stdout=True, stderr=True, tty=False):
        if utils.compare_version('1.15', self._version) < 0:
            raise errors.InvalidVersion('Exec is not supported in API < 1.15')
        if isinstance(container, dict):
            container = container.get('Id')
        if isinstance(cmd, six.string_types):
            cmd = shlex.split(str(cmd))

        data = {
            'Container': container,
            'User': '',
            'Privileged': False,
            'Tty': tty,
            'AttachStdin': False,
            'AttachStdout': stdout,
            'AttachStderr': stderr,
            'Cmd': cmd
        }

        url = self._url('/containers/{0}/exec'.format(container))
        res = self._post_json(url, data=data)
        return self._result(res, True)

    def exec_inspect(self, exec_id):
        if utils.compare_version('1.15', self._version) < 0:
            raise errors.InvalidVersion('Exec is not supported in API < 1.15')
        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')
        res = self._get(self._url("/exec/{0}/json".format(exec_id)))
        return self._result(res, True)

    def exec_resize(self, exec_id, height=None, width=None):
        if utils.compare_version('1.15', self._version) < 0:
            raise errors.InvalidVersion('Exec is not supported in API < 1.15')
        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')

        params = {'h': height, 'w': width}
        url = self._url("/exec/{0}/resize".format(exec_id))
        res = self._post(url, params=params)
        self._raise_for_status(res)

    def exec_start(self, exec_id, detach=False, tty=False, stream=False):
        if utils.compare_version('1.15', self._version) < 0:
            raise errors.InvalidVersion('Exec is not supported in API < 1.15')
        if isinstance(exec_id, dict):
            exec_id = exec_id.get('Id')

        data = {
            'Tty': tty,
            'Detach': detach
        }

        res = self._post_json(self._url('/exec/{0}/start'.format(exec_id)),
                              data=data, stream=stream)
        self._raise_for_status(res)
        if stream:
            return self._multiplexed_response_stream_helper(res)
        elif six.PY3:
            return bytes().join(
                [x for x in self._multiplexed_buffer_helper(res)]
            )
        else:
            return str().join(
                [x for x in self._multiplexed_buffer_helper(res)]
            )

    @check_resource
    def export(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/export".format(container)),
                        stream=True)
        self._raise_for_status(res)
        return res.raw

    @check_resource
    def get_image(self, image):
        res = self._get(self._url("/images/{0}/get".format(image)),
                        stream=True)
        self._raise_for_status(res)
        return res.raw

    @check_resource
    def history(self, image):
        res = self._get(self._url("/images/{0}/history".format(image)))
        return self._result(res, True)

    def images(self, name=None, quiet=False, all=False, viz=False,
               filters=None):
        if viz:
            if utils.compare_version('1.7', self._version) >= 0:
                raise Exception('Viz output is not supported in API >= 1.7!')
            return self._result(self._get(self._url("images/viz")))
        params = {
            'filter': name,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
        }
        if filters:
            params['filters'] = utils.convert_filters(filters)
        res = self._result(self._get(self._url("/images/json"), params=params),
                           True)
        if quiet:
            return [x['Id'] for x in res]
        return res

    def import_image(self, src=None, repository=None, tag=None, image=None):
        if src:
            if isinstance(src, six.string_types):
                try:
                    result = self.import_image_from_file(
                        src, repository=repository, tag=tag)
                except IOError:
                    result = self.import_image_from_url(
                        src, repository=repository, tag=tag)
            else:
                result = self.import_image_from_data(
                    src, repository=repository, tag=tag)
        elif image:
            result = self.import_image_from_image(
                image, repository=repository, tag=tag)
        else:
            raise Exception("Must specify a src or image")

        return result

    def import_image_from_data(self, data, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': '-',
            'repo': repository,
            'tag': tag
        }
        headers = {
            'Content-Type': 'application/tar',
        }
        return self._result(
            self._post(u, data=data, params=params, headers=headers))

    def import_image_from_file(self, filename, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': '-',
            'repo': repository,
            'tag': tag
        }
        headers = {
            'Content-Type': 'application/tar',
        }
        with open(filename, 'rb') as f:
            return self._result(
                self._post(u, data=f, params=params, headers=headers,
                           timeout=None))

    def import_image_from_stream(self, stream, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': '-',
            'repo': repository,
            'tag': tag
        }
        headers = {
            'Content-Type': 'application/tar',
            'Transfer-Encoding': 'chunked',
        }
        return self._result(
            self._post(u, data=stream, params=params, headers=headers))

    def import_image_from_url(self, url, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': url,
            'repo': repository,
            'tag': tag
        }
        return self._result(
            self._post(u, data=None, params=params))

    def import_image_from_image(self, image, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromImage': image,
            'repo': repository,
            'tag': tag
        }
        return self._result(
            self._post(u, data=None, params=params))

    def info(self):
        return self._result(self._get(self._url("/info")),
                            True)

    @check_resource
    def insert(self, image, url, path):
        if utils.compare_version('1.12', self._version) >= 0:
            raise errors.DeprecatedMethod(
                'insert is not available for API version >=1.12'
            )
        api_url = self._url("/images/{0}/insert".fornat(image))
        params = {
            'url': url,
            'path': path
        }
        return self._result(self._post(api_url, params=params))

    @check_resource
    def inspect_container(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(
            self._get(self._url("/containers/{0}/json".format(container))),
            True)

    @check_resource
    def inspect_image(self, image):
        return self._result(
            self._get(self._url("/images/{0}/json".format(image))),
            True
        )

    @check_resource
    def kill(self, container, signal=None):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/kill".format(container))
        params = {}
        if signal is not None:
            params['signal'] = signal
        res = self._post(url, params=params)

        self._raise_for_status(res)

    def load_image(self, data):
        res = self._post(self._url("/images/load"), data=data)
        self._raise_for_status(res)

    def login(self, username, password=None, email=None, registry=None,
              reauth=False, insecure_registry=False, dockercfg_path=None):
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

    @check_resource
    def logs(self, container, stdout=True, stderr=True, stream=False,
             timestamps=False, tail='all'):
        if isinstance(container, dict):
            container = container.get('Id')
        if utils.compare_version('1.11', self._version) >= 0:
            params = {'stderr': stderr and 1 or 0,
                      'stdout': stdout and 1 or 0,
                      'timestamps': timestamps and 1 or 0,
                      'follow': stream and 1 or 0,
                      }
            if utils.compare_version('1.13', self._version) >= 0:
                if tail != 'all' and (not isinstance(tail, int) or tail <= 0):
                    tail = 'all'
                params['tail'] = tail
            url = self._url("/containers/{0}/logs".format(container))
            res = self._get(url, params=params, stream=stream)
            if stream:
                return self._multiplexed_response_stream_helper(res)
            elif six.PY3:
                return bytes().join(
                    [x for x in self._multiplexed_buffer_helper(res)]
                )
            else:
                return str().join(
                    [x for x in self._multiplexed_buffer_helper(res)]
                )
        return self.attach(
            container,
            stdout=stdout,
            stderr=stderr,
            stream=stream,
            logs=True
        )

    @check_resource
    def pause(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url('/containers/{0}/pause'.format(container))
        res = self._post(url)
        self._raise_for_status(res)

    def ping(self):
        return self._result(self._get(self._url('/_ping')))

    @check_resource
    def port(self, container, private_port):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/json".format(container)))
        self._raise_for_status(res)
        json_ = res.json()
        s_port = str(private_port)
        h_ports = None

        # Port settings is None when the container is running with
        # network_mode=host.
        port_settings = json_.get('NetworkSettings', {}).get('Ports')
        if port_settings is None:
            return None

        h_ports = port_settings.get(s_port + '/udp')
        if h_ports is None:
            h_ports = port_settings.get(s_port + '/tcp')

        return h_ports

    def pull(self, repository, tag=None, stream=False,
             insecure_registry=False, auth_config=None):
        if not tag:
            repository, tag = utils.parse_repository_tag(repository)
        registry, repo_name = auth.resolve_repository_name(
            repository, insecure=insecure_registry
        )
        if repo_name.count(":") == 1:
            repository, tag = repository.rsplit(":", 1)

        params = {
            'tag': tag,
            'fromImage': repository
        }
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if auth_config is None:
                if not self._auth_configs:
                    self._auth_configs = auth.load_config()
                authcfg = auth.resolve_authconfig(self._auth_configs, registry)
                # Do not fail here if no authentication exists for this
                # specific registry as we can have a readonly pull. Just
                # put the header if we can.
                if authcfg:
                    # auth_config needs to be a dict in the format used by
                    # auth.py username , password, serveraddress, email
                    headers['X-Registry-Auth'] = auth.encode_header(
                        authcfg
                    )
            else:
                headers['X-Registry-Auth'] = auth.encode_header(auth_config)

        response = self._post(self._url('/images/create'), params=params,
                              headers=headers, stream=stream, timeout=None)

        if stream:
            return self._stream_helper(response)
        else:
            return self._result(response)

    def push(self, repository, tag=None, stream=False,
             insecure_registry=False):
        if not tag:
            repository, tag = utils.parse_repository_tag(repository)
        registry, repo_name = auth.resolve_repository_name(
            repository, insecure=insecure_registry
        )
        u = self._url("/images/{0}/push".format(repository))
        params = {
            'tag': tag
        }
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if not self._auth_configs:
                self._auth_configs = auth.load_config()
            authcfg = auth.resolve_authconfig(self._auth_configs, registry)

            # Do not fail here if no authentication exists for this specific
            # registry as we can have a readonly pull. Just put the header if
            # we can.
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)

            response = self._post_json(u, None, headers=headers,
                                       stream=stream, params=params)
        else:
            response = self._post_json(u, None, stream=stream, params=params)

        return stream and self._stream_helper(response) \
            or self._result(response)

    @check_resource
    def remove_container(self, container, v=False, link=False, force=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'v': v, 'link': link, 'force': force}
        res = self._delete(self._url("/containers/" + container),
                           params=params)
        self._raise_for_status(res)

    @check_resource
    def remove_image(self, image, force=False, noprune=False):
        if isinstance(image, dict):
            image = image.get('Id')
        params = {'force': force, 'noprune': noprune}
        res = self._delete(self._url("/images/" + image), params=params)
        self._raise_for_status(res)

    @check_resource
    def rename(self, container, name):
        if utils.compare_version('1.17', self._version) < 0:
            raise errors.InvalidVersion(
                'rename was only introduced in API version 1.17'
            )
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/rename".format(container))
        params = {'name': name}
        res = self._post(url, params=params)
        self._raise_for_status(res)

    @check_resource
    def resize(self, container, height, width):
        if isinstance(container, dict):
            container = container.get('Id')

        params = {'h': height, 'w': width}
        url = self._url("/containers/{0}/resize".format(container))
        res = self._post(url, params=params)
        self._raise_for_status(res)

    @check_resource
    def restart(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/restart".format(container))
        res = self._post(url, params=params)
        self._raise_for_status(res)

    def search(self, term):
        return self._result(self._get(self._url("/images/search"),
                                      params={'term': term}),
                            True)

    @check_resource
    def start(self, container, binds=None, port_bindings=None, lxc_conf=None,
              publish_all_ports=False, links=None, privileged=False,
              dns=None, dns_search=None, volumes_from=None, network_mode=None,
              restart_policy=None, cap_add=None, cap_drop=None, devices=None,
              extra_hosts=None, read_only=None, pid_mode=None, ipc_mode=None,
              security_opt=None, ulimits=None):

        if utils.compare_version('1.10', self._version) < 0:
            if dns is not None:
                raise errors.InvalidVersion(
                    'dns is only supported for API version >= 1.10'
                )
            if volumes_from is not None:
                raise errors.InvalidVersion(
                    'volumes_from is only supported for API version >= 1.10'
                )

        if utils.compare_version('1.15', self._version) < 0:
            if security_opt is not None:
                raise errors.InvalidVersion(
                    'security_opt is only supported for API version >= 1.15'
                )
            if ipc_mode:
                raise errors.InvalidVersion(
                    'ipc_mode is only supported for API version >= 1.15'
                )

        if utils.compare_version('1.17', self._version) < 0:
            if read_only is not None:
                raise errors.InvalidVersion(
                    'read_only is only supported for API version >= 1.17'
                )
            if pid_mode is not None:
                raise errors.InvalidVersion(
                    'pid_mode is only supported for API version >= 1.17'
                )

        if utils.compare_version('1.18', self._version) < 0:
            if ulimits is not None:
                raise errors.InvalidVersion(
                    'ulimits is only supported for API version >= 1.18'
                )

        start_config = utils.create_host_config(
            binds=binds, port_bindings=port_bindings, lxc_conf=lxc_conf,
            publish_all_ports=publish_all_ports, links=links, dns=dns,
            privileged=privileged, dns_search=dns_search, cap_add=cap_add,
            cap_drop=cap_drop, volumes_from=volumes_from, devices=devices,
            network_mode=network_mode, restart_policy=restart_policy,
            extra_hosts=extra_hosts, read_only=read_only, pid_mode=pid_mode,
            ipc_mode=ipc_mode, security_opt=security_opt, ulimits=ulimits
        )

        if isinstance(container, dict):
            container = container.get('Id')

        url = self._url("/containers/{0}/start".format(container))
        if not start_config:
            start_config = None
        res = self._post_json(url, data=start_config)
        self._raise_for_status(res)

    @check_resource
    def stats(self, container, decode=None):
        if utils.compare_version('1.17', self._version) < 0:
            raise errors.InvalidVersion(
                'Stats retrieval is not supported in API < 1.17!')

        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/stats".format(container))
        return self._stream_helper(self._get(url, stream=True), decode=decode)

    @check_resource
    def stop(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/stop".format(container))

        res = self._post(url, params=params,
                         timeout=(timeout + self.timeout))
        self._raise_for_status(res)

    @check_resource
    def tag(self, image, repository, tag=None, force=False):
        params = {
            'tag': tag,
            'repo': repository,
            'force': 1 if force else 0
        }
        url = self._url("/images/{0}/tag".format(image))
        res = self._post(url, params=params)
        self._raise_for_status(res)
        return res.status_code == 201

    @check_resource
    def top(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        u = self._url("/containers/{0}/top".format(container))
        return self._result(self._get(u), True)

    def version(self, api_version=True):
        url = self._url("/version", versioned_api=api_version)
        return self._result(self._get(url), json=True)

    @check_resource
    def unpause(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url('/containers/{0}/unpause'.format(container))
        res = self._post(url)
        self._raise_for_status(res)

    @check_resource
    def wait(self, container, timeout=None):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/wait".format(container))
        res = self._post(url, timeout=timeout)
        self._raise_for_status(res)
        json_ = res.json()
        if 'StatusCode' in json_:
            return json_['StatusCode']
        return -1


class AutoVersionClient(Client):
    def __init__(self, *args, **kwargs):
        if 'version' in kwargs and kwargs['version']:
            raise errors.DockerException(
                'Can not specify version for AutoVersionClient'
            )
        kwargs['version'] = 'auto'
        super(AutoVersionClient, self).__init__(*args, **kwargs)
