import json
import struct
from functools import partial

import requests
import requests.exceptions
import six
import websocket


from . import api
from . import constants
from . import errors
from .auth import auth
from .ssladapter import ssladapter
from .tls import TLSConfig
from .transport import UnixAdapter
from .utils import utils, check_resource, update_headers, kwargs_from_env
from .utils.socket import frames_iter
try:
    from .transport import NpipeAdapter
except ImportError:
    pass


def from_env(**kwargs):
    return Client.from_env(**kwargs)


class Client(
        requests.Session,
        api.BuildApiMixin,
        api.ContainerApiMixin,
        api.DaemonApiMixin,
        api.ExecApiMixin,
        api.ImageApiMixin,
        api.NetworkApiMixin,
        api.ServiceApiMixin,
        api.SwarmApiMixin,
        api.VolumeApiMixin):
    def __init__(self, base_url=None, version=None,
                 timeout=constants.DEFAULT_TIMEOUT_SECONDS, tls=False,
                 user_agent=constants.DEFAULT_USER_AGENT,
                 num_pools=constants.DEFAULT_NUM_POOLS):
        super(Client, self).__init__()

        if tls and not base_url:
            raise errors.TLSParameterError(
                'If using TLS, the base_url argument must be provided.'
            )

        self.base_url = base_url
        self.timeout = timeout
        self.headers['User-Agent'] = user_agent

        self._auth_configs = auth.load_config()

        base_url = utils.parse_host(
            base_url, constants.IS_WINDOWS_PLATFORM, tls=bool(tls)
        )
        if base_url.startswith('http+unix://'):
            self._custom_adapter = UnixAdapter(
                base_url, timeout, num_pools=num_pools
            )
            self.mount('http+docker://', self._custom_adapter)
            self._unmount('http://', 'https://')
            self.base_url = 'http+docker://localunixsocket'
        elif base_url.startswith('npipe://'):
            if not constants.IS_WINDOWS_PLATFORM:
                raise errors.DockerException(
                    'The npipe:// protocol is only supported on Windows'
                )
            try:
                self._custom_adapter = NpipeAdapter(
                    base_url, timeout, num_pools=num_pools
                )
            except NameError:
                raise errors.DockerException(
                    'Install pypiwin32 package to enable npipe:// support'
                )
            self.mount('http+docker://', self._custom_adapter)
            self.base_url = 'http+docker://localnpipe'
        else:
            # Use SSLAdapter for the ability to specify SSL version
            if isinstance(tls, TLSConfig):
                tls.configure_client(self)
            elif tls:
                self._custom_adapter = ssladapter.SSLAdapter(
                    num_pools=num_pools
                )
                self.mount('https://', self._custom_adapter)
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

    @classmethod
    def from_env(cls, **kwargs):
        return cls(**kwargs_from_env(**kwargs))

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

    @update_headers
    def _post(self, url, **kwargs):
        return self.post(url, **self._set_request_timeout(kwargs))

    @update_headers
    def _get(self, url, **kwargs):
        return self.get(url, **self._set_request_timeout(kwargs))

    @update_headers
    def _put(self, url, **kwargs):
        return self.put(url, **self._set_request_timeout(kwargs))

    @update_headers
    def _delete(self, url, **kwargs):
        return self.delete(url, **self._set_request_timeout(kwargs))

    def _url(self, pathfmt, *args, **kwargs):
        for arg in args:
            if not isinstance(arg, six.string_types):
                raise ValueError(
                    'Expected a string but found {0} ({1}) '
                    'instead'.format(arg, type(arg))
                )

        quote_f = partial(six.moves.urllib.parse.quote_plus, safe="/:")
        args = map(quote_f, args)

        if kwargs.get('versioned_api', True):
            return '{0}/v{1}{2}'.format(
                self.base_url, self._version, pathfmt.format(*args)
            )
        else:
            return '{0}{1}'.format(self.base_url, pathfmt.format(*args))

    def _raise_for_status(self, response, explanation=None):
        """Raises stored :class:`APIError`, if one occurred."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise errors.NotFound(e, response, explanation=explanation)
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
        url = self._url("/containers/{0}/attach/ws", container)
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
            if self.base_url.startswith("https://"):
                sock = sock._sock
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
                    # remove the trailing newline
                    data = data.strip()
                    # split the data at any newlines
                    data_list = data.split("\r\n")
                    # load and yield each line seperately
                    for data in data_list:
                        data = json.loads(data)
                        yield data
                else:
                    yield data
        else:
            # Response isn't chunked, meaning we probably
            # encountered an error immediately
            yield self._result(response, json=decode)

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
        self._disable_socket_timeout(socket)

        while True:
            header = response.raw.read(constants.STREAM_HEADER_SIZE_BYTES)
            if not header:
                break
            _, length = struct.unpack('>BxxxL', header)
            if not length:
                continue
            data = response.raw.read(length)
            if not data:
                break
            yield data

    def _stream_raw_result_old(self, response):
        ''' Stream raw output for API versions below 1.6 '''
        self._raise_for_status(response)
        for line in response.iter_lines(chunk_size=1,
                                        decode_unicode=True):
            # filter out keep-alive new lines
            if line:
                yield line

    def _stream_raw_result(self, response):
        ''' Stream result for TTY-enabled container above API 1.6 '''
        self._raise_for_status(response)
        for out in response.iter_content(chunk_size=1, decode_unicode=True):
            yield out

    def _read_from_socket(self, response, stream):
        socket = self._get_raw_response_socket(response)

        if stream:
            return frames_iter(socket)
        else:
            return six.binary_type().join(frames_iter(socket))

    def _disable_socket_timeout(self, socket):
        """ Depending on the combination of python version and whether we're
        connecting over http or https, we might need to access _sock, which
        may or may not exist; or we may need to just settimeout on socket
        itself, which also may or may not have settimeout on it. To avoid
        missing the correct one, we try both.

        We also do not want to set the timeout if it is already disabled, as
        you run the risk of changing a socket that was non-blocking to
        blocking, for example when using gevent.
        """
        sockets = [socket, getattr(socket, '_sock', None)]

        for s in sockets:
            if not hasattr(s, 'settimeout'):
                continue

            timeout = -1

            if hasattr(s, 'gettimeout'):
                timeout = s.gettimeout()

            # Don't change the timeout if it is already disabled.
            if timeout is None or timeout == 0.0:
                continue

            s.settimeout(None)

    def _get_result(self, container, stream, res):
        cont = self.inspect_container(container)
        return self._get_result_tty(stream, res, cont['Config']['Tty'])

    def _get_result_tty(self, stream, res, is_tty):
        # Stream multi-plexing was only introduced in API v1.6. Anything
        # before that needs old-style streaming.
        if utils.compare_version('1.6', self._version) < 0:
            return self._stream_raw_result_old(res)

        # We should also use raw streaming (without keep-alives)
        # if we're dealing with a tty-enabled container.
        if is_tty:
            return self._stream_raw_result(res) if stream else \
                self._result(res, binary=True)

        self._raise_for_status(res)
        sep = six.binary_type()
        if stream:
            return self._multiplexed_response_stream_helper(res)
        else:
            return sep.join(
                [x for x in self._multiplexed_buffer_helper(res)]
            )

    def _unmount(self, *args):
        for proto in args:
            self.adapters.pop(proto)

    def get_adapter(self, url):
        try:
            return super(Client, self).get_adapter(url)
        except requests.exceptions.InvalidSchema as e:
            if self._custom_adapter:
                return self._custom_adapter
            else:
                raise e

    @property
    def api_version(self):
        return self._version


class AutoVersionClient(Client):
    def __init__(self, *args, **kwargs):
        if 'version' in kwargs and kwargs['version']:
            raise errors.DockerException(
                'Can not specify version for AutoVersionClient'
            )
        kwargs['version'] = 'auto'
        super(AutoVersionClient, self).__init__(*args, **kwargs)
