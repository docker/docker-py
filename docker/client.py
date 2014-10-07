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
from socket import socket as socket_obj
import warnings

import requests
import requests.exceptions
import six

from .auth import auth
from .unixconn import unixconn
from .ssladapter import ssladapter
from .utils import utils
from . import errors
from .tls import TLSConfig

if not six.PY3:
    import websocket

DEFAULT_DOCKER_API_VERSION = '1.12'
DEFAULT_TIMEOUT_SECONDS = 60
STREAM_HEADER_SIZE_BYTES = 8


class Client(requests.Session):
    """
    **Port bindings**


    Port bindings is done in two parts. Firstly, by providing a list of ports
    to open inside the container in the ``Client.create_container()`` method.

    .. code-block:: python

        c.create_container('busybox', 'ls', ports=[1111, 2222])

    Bindings are then declared in the ``Client.start`` method.

    .. code-block:: python

        c.start(container_id, port_bindings={1111: 4567, 2222: None})

    You can limit the host address on which the port will be exposed like such:

    .. code-block:: python

        c.start(container_id, port_bindings={1111: ('127.0.0.1', 4567)})

    Or without host port assignment:

    .. code-block:: python

        c.start(container_id, port_bindings={1111: ('127.0.0.1',)})

    If you wish to use UDP instead of TCP (default), you need to declare it
    like such in both the ``create_container()`` and ``start()`` calls:

    .. code-block:: python

        container_id = c.create_container(
            'busybox', 'ls', ports=[(1111, 'udp'), 2222]
        )
        c.start(container_id, port_bindings={'1111/udp': 4567, 2222: None})

    **Using volumes**

    Similarly, volume declaration is done in two parts. First, you have to
    provide a list of mountpoints to the ``Client.create_container()`` method.

    .. code-block:: python

        c.create_container('busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'])

    Volume mappings are then declared inside the ``Client.start()`` method like
    this:

    .. code-block:: python

        c.start(container_id, binds={
            '/home/user1/':
                {
                    'bind': '/mnt/vol2',
                    'ro': False
                },
            '/var/www':
                {
                    'bind': '/mnt/vol1',
                    'ro': True
                }
        })

    """
    def __init__(self, base_url=None, version=DEFAULT_DOCKER_API_VERSION,
                 timeout=DEFAULT_TIMEOUT_SECONDS, tls=False):
        """
        To instantiate a ``Client`` class that will allow you to communicate
        with a Docker daemon, simply do:

        .. code-block:: python

            c = docker.Client(base_url='unix://var/run/docker.sock')

        :param base_url: Refers to the protocol+hostname+port where the docker
            server is hosted.
        :type base_url: str

        :param version: The version of the API the client will use
        :type version: str

        :param timeout: The HTTP request timeout, in seconds.
        :type timeout: int

        :param tls: Equivalent CLI options: ``docker --tls ...``
        :type tls: bool or :class:`TLSConfig<docker.tls.TLSConfig>`
        """
        super(Client, self).__init__()
        base_url = utils.parse_host(base_url)
        if 'http+unix:///' in base_url:
            base_url = base_url.replace('unix:/', 'unix:')
        if tls and not base_url.startswith('https://'):
            raise errors.TLSParameterError(
                'If using TLS, the base_url argument must begin with '
                '"https://".')
        self.base_url = base_url
        self._version = version
        self._timeout = timeout
        self._auth_configs = auth.load_config()

        # Use SSLAdapter for the ability to specify SSL version
        if isinstance(tls, TLSConfig):
            tls.configure_client(self)
        elif tls:
            self.mount('https://', ssladapter.SSLAdapter())
        else:
            self.mount('http+unix://', unixconn.UnixAdapter(base_url, timeout))

    def _set_request_timeout(self, kwargs):
        """Prepare the kwargs for an HTTP request by inserting the timeout
        parameter, if not already present."""
        kwargs.setdefault('timeout', self._timeout)
        return kwargs

    def _post(self, url, **kwargs):
        return self.post(url, **self._set_request_timeout(kwargs))

    def _get(self, url, **kwargs):
        return self.get(url, **self._set_request_timeout(kwargs))

    def _delete(self, url, **kwargs):
        return self.delete(url, **self._set_request_timeout(kwargs))

    def _url(self, path):
        return '{0}/v{1}{2}'.format(self.base_url, self._version, path)

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

    def _container_config(self, image, command, hostname=None, user=None,
                          detach=False, stdin_open=False, tty=False,
                          mem_limit=0, ports=None, environment=None, dns=None,
                          volumes=None, volumes_from=None,
                          network_disabled=False, entrypoint=None,
                          cpu_shares=None, working_dir=None, domainname=None,
                          memswap_limit=0):
        if isinstance(command, six.string_types):
            command = shlex.split(str(command))
        if isinstance(environment, dict):
            environment = [
                '{0}={1}'.format(k, v) for k, v in environment.items()
            ]

        if isinstance(mem_limit, six.string_types):
            if len(mem_limit) == 0:
                mem_limit = 0
            else:
                units = {'b': 1,
                         'k': 1024,
                         'm': 1024 * 1024,
                         'g': 1024 * 1024 * 1024}
                suffix = mem_limit[-1].lower()

                # Check if the variable is a string representation of an int
                # without a units part. Assuming that the units are bytes.
                if suffix.isdigit():
                    digits_part = mem_limit
                    suffix = 'b'
                else:
                    digits_part = mem_limit[:-1]

                if suffix in units.keys() or suffix.isdigit():
                    try:
                        digits = int(digits_part)
                    except ValueError:
                        message = ('Failed converting the string value for'
                                   ' mem_limit ({0}) to a number.')
                        formatted_message = message.format(digits_part)
                        raise errors.DockerException(formatted_message)

                    mem_limit = digits * units[suffix]
                else:
                    message = ('The specified value for mem_limit parameter'
                               ' ({0}) should specify the units. The postfix'
                               ' should be one of the `b` `k` `m` `g`'
                               ' characters')
                    raise errors.DockerException(message.format(mem_limit))

        if isinstance(ports, list):
            exposed_ports = {}
            for port_definition in ports:
                port = port_definition
                proto = 'tcp'
                if isinstance(port_definition, tuple):
                    if len(port_definition) == 2:
                        proto = port_definition[1]
                    port = port_definition[0]
                exposed_ports['{0}/{1}'.format(port, proto)] = {}
            ports = exposed_ports

        if isinstance(volumes, six.string_types):
            volumes = [volumes, ]

        if isinstance(volumes, list):
            volumes_dict = {}
            for vol in volumes:
                volumes_dict[vol] = {}
            volumes = volumes_dict

        if volumes_from:
            if not isinstance(volumes_from, six.string_types):
                volumes_from = ','.join(volumes_from)
        else:
            # Force None, an empty list or dict causes client.start to fail
            volumes_from = None

        attach_stdin = False
        attach_stdout = False
        attach_stderr = False
        stdin_once = False

        if not detach:
            attach_stdout = True
            attach_stderr = True

            if stdin_open:
                attach_stdin = True
                stdin_once = True

        if utils.compare_version('1.10', self._version) >= 0:
            message = ('{0!r} parameter has no effect on create_container().'
                       ' It has been moved to start()')
            if dns is not None:
                raise errors.DockerException(message.format('dns'))
            if volumes_from is not None:
                raise errors.DockerException(message.format('volumes_from'))

        return {
            'Hostname': hostname,
            'Domainname': domainname,
            'ExposedPorts': ports,
            'User': user,
            'Tty': tty,
            'OpenStdin': stdin_open,
            'StdinOnce': stdin_once,
            'Memory': mem_limit,
            'AttachStdin': attach_stdin,
            'AttachStdout': attach_stdout,
            'AttachStderr': attach_stderr,
            'Env': environment,
            'Cmd': command,
            'Dns': dns,
            'Image': image,
            'Volumes': volumes,
            'VolumesFrom': volumes_from,
            'NetworkDisabled': network_disabled,
            'Entrypoint': entrypoint,
            'CpuShares': cpu_shares,
            'WorkingDir': working_dir,
            'MemorySwap': memswap_limit
        }

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
            return response.raw._fp.fp.raw._sock
        else:
            return response.raw._fp.fp._sock

    def _stream_helper(self, response):
        """Generator for data coming from a chunked-encoded HTTP response."""
        socket_fp = socket_obj(_sock=self._get_raw_response_socket(response))
        socket_fp.setblocking(1)
        socket = socket_fp.makefile()
        while True:
            # Because Docker introduced newlines at the end of chunks in v0.9,
            # and only on some API endpoints, we have to cater for both cases.
            size_line = socket.readline()
            if size_line == '\r\n' or size_line == '\n':
                size_line = socket.readline()

            size = int(size_line, 16)
            if size <= 0:
                break
            data = socket.readline()
            if not data:
                break
            yield data

    def _multiplexed_buffer_helper(self, response):
        """A generator of multiplexed data blocks read from a buffered
        response."""
        buf = self._result(response, binary=True)
        walker = 0
        while True:
            if len(buf[walker:]) < 8:
                break
            _, length = struct.unpack_from('>BxxxL', buf[walker:])
            start = walker + STREAM_HEADER_SIZE_BYTES
            end = start + length
            walker = end
            yield buf[start:end]

    def _multiplexed_socket_stream_helper(self, response):
        """A generator of multiplexed data blocks coming from a response
        socket."""
        socket = self._get_raw_response_socket(response)

        def recvall(socket, size):
            blocks = []
            while size > 0:
                block = socket.recv(size)
                if not block:
                    return None

                blocks.append(block)
                size -= len(block)

            sep = bytes() if six.PY3 else str()
            data = sep.join(blocks)
            return data

        while True:
            socket.settimeout(None)
            header = recvall(socket, STREAM_HEADER_SIZE_BYTES)
            if not header:
                break
            _, length = struct.unpack('>BxxxL', header)
            if not length:
                break
            data = recvall(socket, length)
            if not data:
                break
            yield data

    def attach(self, container, stdout=True, stderr=True,
               stream=False, logs=False):
        """
        The ``.logs()`` function is a wrapper around this one, which you can
        use instead if you want to fetch/stream container output without first
        retrieving the entire backlog.

        :param container: The container to attach to
        :type container: str

        :param stdout: Get STDOUT
        :type stdout: bool

        :param stderr: Get STDERR
        :type stderr: bool

        :param stream: Return an interator
        :type stream: bool

        :param logs: Get all previous output
        :type logs: bool

        :return: The logs or output for the image
        :rtype: generator or str
        """
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

        return stream and self._multiplexed_socket_stream_helper(response) or \
            sep.join([x for x in self._multiplexed_buffer_helper(response)])

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
              custom_context=False, encoding=None):
        """
        Similar to the ``docker build`` command. Either ``path`` or ``fileobj``
        needs to be set. ``path`` can be a local path (to a directory
        containing a Dockerfile) or a remote URL. ``fileobj`` must be a
        readable file-like object to a Dockerfile.

        If you have a tar file for the docker build context (including a
        Dockerfile) already, pass a readable file-like object to ``fileobj``
        and also pass ``custom_context=True``. If the stream is compressed
        also, set ``encoding`` to the correct value (e.g ``gzip``).


        :param path: Path to the directory containing the Dockerfile
        :type path: str

        :param tag: A tag to add to the final image
        :type tag: str

        :param quiet: Whether to return the status
        :type quiet: bool

        :param fileobj: A file object to use as the Dockerfile.
        :type fileobj: file or :class:`StringIO<python:StringIO.StringIO>`
            (:class:`BytesIO<python3:io.BytesIO>` for py3)

        :param nocache: Don't use the cache when set to ``True``
        :type nocache: bool

        :param rm: Remove intermediate containers
        :type rm: bool

        :param stream: Return a blocking generator you can iterate over to
            retrieve build output as it happens
        :type stream: bool

        :param timeout: HTTP timeout
        :type timeout: int

        :param custom_context: Optional if using ``fileobj``
        :type custom_context: bool

        :param encoding: The encoding for a stream. Set to ``gzip`` for
            compressing
        :type encoding: str

        :rtype: generator
        :returns: Generator of the build output

        Example usage and response output

        .. code-block:: python

            >>> from io import BytesIO
            >>> from docker import Client
            >>> dockerfile = '''
            ... # Shared Volume
            ... FROM busybox:buildroot-2014.02
            ... MAINTAINER first last, first.last@yourdomain.com
            ... VOLUME /data
            ... CMD ["/bin/sh"]
            ... '''
            >>> f = BytesIO(dockerfile.encode('utf-8'))
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> response = [line for line in cli.build(
            ...     fileobj=f, rm=True, tag='yourname/volume'
            ... )]
            >>> response
            ['{"stream":" ---\\u003e a9eb17255234\\n"}',
             '{"stream":"Step 1 : MAINTAINER first last, first.last@yourdomain.com\\n"}',
             '{"stream":" ---\\u003e Running in 08787d0ee8b1\\n"}',
             '{"stream":" ---\\u003e 23e5e66a4494\\n"}',
             '{"stream":"Removing intermediate container 08787d0ee8b1\\n"}',
             '{"stream":"Step 2 : VOLUME /data\\n"}',
             '{"stream":" ---\\u003e Running in abdc1e6896c6\\n"}',
             '{"stream":" ---\\u003e 713bca62012e\\n"}',
             '{"stream":"Removing intermediate container abdc1e6896c6\\n"}',
             '{"stream":"Step 3 : CMD [\\"/bin/sh\\"]\\n"}',
             '{"stream":" ---\\u003e Running in dba30f2a1a7e\\n"}',
             '{"stream":" ---\\u003e 032b8b2855fc\\n"}',
             '{"stream":"Removing intermediate container dba30f2a1a7e\\n"}',
             '{"stream":"Successfully built 032b8b2855fc\\n"}']

        :raises: :class:`TypeError<exceptions.TypeError>` if ``path`` nor
            ``fileobj`` are specified
        """
        remote = context = headers = None
        if path is None and fileobj is None:
            raise TypeError("Either path or fileobj needs to be provided.")

        if custom_context:
            if not fileobj:
                raise TypeError("You must specify fileobj with custom_context")
            context = fileobj
        elif fileobj is not None:
            context = utils.mkbuildcontext(fileobj)
        elif path.startswith(('http://', 'https://',
                              'git://', 'github.com/')):
            remote = path
        else:
            dockerignore = os.path.join(path, '.dockerignore')
            exclude = None
            if os.path.exists(dockerignore):
                with open(dockerignore, 'r') as f:
                    exclude = list(filter(bool, f.read().split('\n')))
            context = utils.tar(path, exclude=exclude)

        if utils.compare_version('1.8', self._version) >= 0:
            stream = True

        u = self._url('/build')
        params = {
            't': tag,
            'remote': remote,
            'q': quiet,
            'nocache': nocache,
            'rm': rm
        }

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

        if context is not None:
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

    def commit(self, container, repository=None, tag=None, message=None,
               author=None, conf=None):
        """
        Identical to the ``docker commit`` command.

        :param container: The image hash of the container
        :type container: str

        :param repository: The repository to push the image to
        :type repository: str

        :param tag: The tag to push
        :type tag: str

        :param message: A commit message
        :type message: str

        :param author: The name of the author
        :type author: str

        :param conf:
        :type conf: dict
        """
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

    def containers(self, quiet=False, all=False, trunc=True, latest=False,
                   since=None, before=None, limit=-1, size=False):
        """
        List containers. Identical to the ``docker ps`` command.

        :param quiet: Only display numeric IDs
        :type quiet: bool

        :param all: Show all containers. Only running containers are shown by
            default
        :type all: bool

        :param trunc: Truncate output
        :type trunc: bool

        :param latest: Show only the latest created container, include
            non-running ones.
        :type latest: bool

        :param since: Show only containers created since Id or Name, include
            non-running ones
        :type since: str

        :param before: Show only container created before Id or Name, include
            non-running ones
        :type before: str

        :param limit: Show ``limit`` last created containers, include
            non-running ones
        :type limit: int

        :param size: Display sizes
        :type size: bool

        :rtype: dict
        :returns: The system's containers

        Example:

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> cli.containers()
            [{'Command': '/bin/sleep 30',
              'Created': 1412574844,
              'Id': '6e276c9e6e5759e12a6a9214efec6439f80b4f37618e1a6547f28a3da34db07a',
              'Image': 'busybox:buildroot-2014.02',
              'Names': ['/grave_mayer'],
              'Ports': [],
              'Status': 'Up 1 seconds'}]



        """
        params = {
            'limit': 1 if latest else limit,
            'all': 1 if all else 0,
            'size': 1 if size else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        u = self._url("/containers/json")
        res = self._result(self._get(u, params=params), True)

        if quiet:
            return [{'Id': x['Id']} for x in res]
        return res

    def copy(self, container, resource):
        """
        Identical to the ``docker cp`` command. Get files/folders from the
        container.

        :param container: The container to copy from
        :type container: str

        :param resource: The path within the container
        :type resource: str

        :return: The contents of the file as a string
        :rtype: str
        """
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
                         memswap_limit=0):
        """
        Creates a container that can then be ``.start()`` ed. Parameters are
        similar to those for the ``docker run`` command except it doesn't
        support the attach options (``-a``).

        See "Port bindings" and "Using volumes" below for
        more information on how to create port bindings and volume mappings.

        The ``mem_limit`` variable accepts float values (which represent the
        memory limit of the created container in bytes) or a string with a
        units identification char ('100000b', 1000k', 128m', '1g'). If a string
        is specified without a units character, bytes are assumed as an
        intended unit.

        ``volumes_from`` and ``dns`` arguments raise
        :class:`TypeError<exceptions.TypeError>` exception if they are used
        against v1.10 of docker remote API. Those arguments should be passed to
        ``start()`` instead.

        :param image: The image to run
        :type image: str

        :param command: The command to be run in the container
        :type command: str or list

        :param hostname: Optional hostname for the container
        :type hostname: str

        :param user: Username or UID
        :type user: str or int

        :param detach: Detached mode: run container in the background and print
            new container ID
        :type detach: bool

        :param stdin_open: Keep STDIN open even if not attached
        :type stdin_open: bool

        :param tty: Allocate a pseudo-TTY
        :type tty: bool

        :param mem_limit: Memory limit (format: <number><optional unit>, where
            unit = b, k, m or g)
        :type mem_limit: float or str

        :param ports: A list of port numbers
        :type ports: list of ints

        :param environment: A dictionary or a list of strings in the following
            format ``["PASSWORD=xxx"]`` or ``{"PASSWORD": "xxx"}``.
        :type environment: list or dict

        :param dns: DNS name servers
        :type dns: list

        :param volumes:
        :type volumes:

        :param volumes_from:
        :type volumes_from:

        :param network_disabled: Disable networking
        :type network_disabled: bool

        :param name: A name for the container
        :type name: str

        :param entrypoint: An entrypoint
        :type entrypoint: str or list

        :param cpu_shares: CPU shares (relative weight)
        :type cpu_shares: int or float
        :param working_dir: Path to the working directory
        :type working_dir: str

        :param domainname: Set custom DNS search domains
        :type domainname: str or list

        :param memswap_limit:
        :type memswap_limit:

        :rtype: dict
        :returns: A dictionary with an image 'ID' key and a 'Warnings' key.

        Example Usage:

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> container = cli.create_container(image='busybox:latest', command='/bin/sleep 30')
            >>> print(container)
            {'Id': '8a61192da2b3bb2d922875585e29b74ec0dc4e0117fcbf84c962204e97564cd7',
             'Warnings': None}
        """

        if isinstance(volumes, six.string_types):
            volumes = [volumes, ]

        config = self._container_config(
            image, command, hostname, user, detach, stdin_open, tty, mem_limit,
            ports, environment, dns, volumes, volumes_from, network_disabled,
            entrypoint, cpu_shares, working_dir, domainname, memswap_limit
        )
        return self.create_container_from_config(config, name)

    def create_container_from_config(self, config, name=None):
        u = self._url("/containers/create")
        params = {
            'name': name
        }
        res = self._post_json(u, data=config, params=params)
        return self._result(res, True)

    def diff(self, container):
        """
        Inspect changes on a container's filesystem

        :param container: The container to diff
        :type container: str

        :rtype: str
        """
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(self._get(self._url("/containers/{0}/changes".
                            format(container))), True)

    def events(self):
        return self._stream_helper(self.get(self._url('/events'), stream=True))

    def export(self, container):
        """
        Export the contents of a filesystem as a tar archive to STDOUT

        :param container: The container to export
        :type container: str

        :rtype: str
        """
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/export".format(container)),
                        stream=True)
        self._raise_for_status(res)
        return res.raw

    def get_image(self, image):
        res = self._get(self._url("/images/{0}/get".format(image)),
                        stream=True)
        self._raise_for_status(res)
        return res.raw

    def history(self, image):
        """
        Show the history of an image

        :param image: The image to show history for
        :type image: str
        """
        res = self._get(self._url("/images/{0}/history".format(image)))
        self._raise_for_status(res)
        return self._result(res)

    def images(self, name=None, quiet=False, all=False, viz=False):
        """
        List images. Identical to the `docker images` command.

        :param name: Optional filter for a name
        :type name: str

        :param quiet: Only show numeric IDs. Returns a list
        :type quiet: bool

        :param all: Show all images (by default filter out the intermediate image
            layers)
        :type all: bool

        :param viz: Depreciated

        :rtype: dict or list
        :returns: A list if ``quiet=True``, otherwise a dict.

        ::

            [{'Created': 1401926735,
              'Id': 'a9eb172552348a9a49180694790b33a1097f546456d041b6e82e4d7716ddb721',
              'ParentId': '120e218dd395ec314e7b6249f39d2853911b3d6def6ea164ae05722649f34b16',
              'RepoTags': ['busybox:buildroot-2014.02', 'busybox:latest'],
              'Size': 0,
              'VirtualSize': 2433303},
              ...
            ]

        """

        if viz:
            if utils.compare_version('1.7', self._version) >= 0:
                raise Exception('Viz output is not supported in API >= 1.7!')
            return self._result(self._get(self._url("images/viz")))
        params = {
            'filter': name,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
        }
        res = self._result(self._get(self._url("/images/json"), params=params),
                           True)
        if quiet:
            return [x['Id'] for x in res]
        return res

    def import_image(self, src=None, repository=None, tag=None, image=None):
        """
        Identical to the ``docker import`` command. If ``src`` is a string or
        unicode string, it will be treated as a URL to fetch the image from. To
        import an image from the local machine, ``src`` needs to be a file-like
        object or bytes collection.  To import from a tarball use your absolute
        path to your tarball.  To load arbitrary data as tarball use whatever
        you want as src and your tarball content in data.

        :param src: Path to tarfile or URL
        :type src: str or file

        :param repository: The repository to create
        :type repository: str

        :param tag: The tag to apply
        :type tag: str

        :param image: Use another image like the ``FROM`` Dockerfile parameter
        :type image: str
        """
        u = self._url("/images/create")
        params = {
            'repo': repository,
            'tag': tag
        }

        if src:
            try:
                # XXX: this is ways not optimal but the only way
                # for now to import tarballs through the API
                fic = open(src)
                data = fic.read()
                fic.close()
                src = "-"
            except IOError:
                # file does not exists or not a file (URL)
                data = None
            if isinstance(src, six.string_types):
                params['fromSrc'] = src
                return self._result(self._post(u, data=data, params=params))
            return self._result(self._post(u, data=src, params=params))

        if image:
            params['fromImage'] = image
            return self._result(self._post(u, data=None, params=params))

        raise Exception("Must specify a src or image")

    def info(self):
        """
        Display system-wide information. Identical to the ``docker info`` command.

        :return: The info as a dict
        :rtype: dict

        Example:

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> cli.info()
            {'Containers': 3,
             'Debug': 1,
             'Driver': 'aufs',
             'DriverStatus': [['Root Dir', '/mnt/sda1/var/lib/docker/aufs'],
              ['Dirs', '225']],
             'ExecutionDriver': 'native-0.2',
             'IPv4Forwarding': 1,
             'Images': 219,
             'IndexServerAddress': 'https://index.docker.io/v1/',
             'InitPath': '/usr/local/bin/docker',
             'InitSha1': '',
             'KernelVersion': '3.16.1-tinycore64',
             'MemoryLimit': 1,
             'NEventsListener': 0,
             'NFd': 11,
             'NGoroutines': 12,
             'OperatingSystem': 'Boot2Docker 1.2.0 (TCL 5.3);',
             'SwapLimit': 1}

        """
        return self._result(self._get(self._url("/info")),
                            True)

    def insert(self, image, url, path):
        """
        DEPRECATED
        """
        if utils.compare_version('1.12', self._version) >= 0:
            raise errors.DeprecatedMethod(
                'insert is not available for API version >=1.12'
            )
        api_url = self._url("/images/" + image + "/insert")
        params = {
            'url': url,
            'path': path
        }
        return self._result(self._post(api_url, params=params))

    def inspect_container(self, container):
        """
        Identical to the ``docker inspect`` command, but only for containers.

        :param container: The container to inspect
        :type container: str

        :rtype: str
        :return: Nearly the same output as ``docker inspect``, just as a single
            dict
        """
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(
            self._get(self._url("/containers/{0}/json".format(container))),
            True)

    def inspect_image(self, image_id):
        """
        Identical to the `docker inspect` command, but only for images

        :param image_id: The image to inspect
        :type image_id: str

        :rtype: str
        :return: Nearly the same output as ``docker inspect``, just as a single
            dict
        """
        return self._result(
            self._get(self._url("/images/{0}/json".format(image_id))),
            True
        )

    def kill(self, container, signal=None):
        """
        Kill a container or send a signal to a container

        :param container: The container to kill
        :type container: str

        :param signal: The singal to send. Defaults to ``SIGKILL``
        :type signal: str or int
        """
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
              reauth=False):
        """
        Identical to the ``docker login`` command (but non-interactive,
        obviously).

        :param username: The registry username
        :type username: str
        :param password: The plaintext password
        :type password: str
        :param email: The email for the registry account
        :type email: str
        :param registry: URL to the registry. Ex:
            ``https://index.docker.io/v1/``
        :type registry: str
        :param reauth: Whether refresh existing authentication on the docker
            server.
        :type reauth: bool

        :return: The response from the login request
        :rtype: dict
        """
        # If we don't have any auth data so far, try reloading the config file
        # one more time in case anything showed up in there.
        if not self._auth_configs:
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

    def logs(self, container, stdout=True, stderr=True, stream=False,
             timestamps=False):
        """
        Identical to the `docker logs` command. The `stream` parameter makes
        the `logs` function return a blocking generator you can iterate over to
        retrieve log output as it happens.

        :param container: The container to get logs from
        :type container: str

        :param stdout: Get STDOUT
        :type stdout: bool

        :param stderr: Get STDERR
        :type stderr: bool

        :param stream: Stream the response
        :type stream: bool

        :param timestamps: Show timestamps
        :type timestamps: bool

        :rtype: generator or str
        """
        if isinstance(container, dict):
            container = container.get('Id')
        if utils.compare_version('1.11', self._version) >= 0:
            params = {'stderr': stderr and 1 or 0,
                      'stdout': stdout and 1 or 0,
                      'timestamps': timestamps and 1 or 0,
                      'follow': stream and 1 or 0}
            url = self._url("/containers/{0}/logs".format(container))
            res = self._get(url, params=params, stream=stream)
            if stream:
                return self._multiplexed_socket_stream_helper(res)
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

    def ping(self):
        """
        Hits the /_ping endpoint of the remote API and returns the result.
        An exception will be raised if the endpoint isn't responding.

        :rtype: bool
        """
        return self._result(self._get(self._url('/_ping')))

    def port(self, container, private_port):
        """
        Lookup the public-facing port that is NAT-ed to ``private_port``.
        Identical to the ``docker port`` command.

        :param container: The container to look up
        :type container: str
        :param private_port: The private port to inspect
        :type private_port: int

        :rtype: list of dict
        :return: The mapping for the host port

        Example:

        .. code-block:: bash

            $ docker run -d -p 80:80 ubuntu:14.04 /bin/sleep 30
            7174d6347063a83f412fad6124c99cffd25ffe1a0807eb4b7f9cec76ac8cb43b

        .. code-block:: python

            >>> cli.port('7174d6347063', 80)
            [{'HostIp': '0.0.0.0', 'HostPort': '80'}]

        """
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/json".format(container)))
        self._raise_for_status(res)
        json_ = res.json()
        s_port = str(private_port)
        h_ports = None

        h_ports = json_['NetworkSettings']['Ports'].get(s_port + '/udp')
        if h_ports is None:
            h_ports = json_['NetworkSettings']['Ports'].get(s_port + '/tcp')

        return h_ports

    def pull(self, repository, tag=None, stream=False,
             insecure_registry=False):
        """
        Identical to the `docker pull` command.

        :param repository: The repository to pull
        :type repository: str

        :param tag: The tag to pull
        :type tag: str

        :param stream: Stream the output as a generator
        :type stream: bool

        :param insecure_registry: Use an insecure registry
        :type insecure_registry: bool

        :rtype: generator or str
        :return: The output

        Example:

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> for line in cli.pull('busybox', stream=True):
            ...     print(json.dumps(json.loads(line), indent=4))
            {
                "status": "Pulling image (latest) from busybox",
                "progressDetail": {},
                "id": "e72ac664f4f0"
            }
            {
                "status": "Pulling image (latest) from busybox, endpoint: ...",
                "progressDetail": {},
                "id": "e72ac664f4f0"
            }

        """
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
            if not self._auth_configs:
                self._auth_configs = auth.load_config()
            authcfg = auth.resolve_authconfig(self._auth_configs, registry)

            # Do not fail here if no authentication exists for this specific
            # registry as we can have a readonly pull. Just put the header if
            # we can.
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)

        response = self._post(self._url('/images/create'), params=params,
                              headers=headers, stream=stream, timeout=None)

        if stream:
            return self._stream_helper(response)
        else:
            return self._result(response)

    def push(self, repository, tag=None, stream=False,
             insecure_registry=False):
        """
        Push an image or a repository to the registry. Identical to the docker
        push command

        :param repository: The repository to push to
        :type repository: str

        :param tag: An optional tag to push
        :type tag: str

        :param stream: Stream the output as a blocking generator
        :type stream: bool

        :param insecure_registry: Use ``http://`` to connect to the registry
        :type insecure_registry: bool

        :rtype: str or generator
        :return: The output of the upload

        Example:

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> response = [line for line in cli.push('yourname/app', stream=True)]
            >>> response
            ['{"status":"Pushing repository yourname/app (1 tags)"}\\n',
             '{"status":"Pushing","progressDetail":{},"id":"511136ea3c5a"}\\n',
             '{"status":"Image already pushed, skipping","progressDetail":{},
                "id":"511136ea3c5a"}\\n',
             ...
             '{"status":"Pushing tag for rev [918af568e6e5] on {
                https://cdn-registry-1.docker.io/v1/repositories/
                yourname/app/tags/latest}"}\\n']

        """
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

    def remove_container(self, container, v=False, link=False, force=False):
        """
        Remove a container. Similar to the `docker rm` command.

        :param container: The container to remove
        :type container: str

        :param v: Remove the volumes associated with the container
        :type v: bool

        :param link: Remove the specified link and not the underlying container
        :type link: bool

        :param force: Force the removal of a running container (uses SIGKILL)
        :type force: bool

        :rtype: None
        """
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'v': v, 'link': link, 'force': force}
        res = self._delete(self._url("/containers/" + container),
                           params=params)
        self._raise_for_status(res)

    def remove_image(self, image, force=False, noprune=False):
        """
        Remove an image. Similar to the `docker rmi` command.

        :param image: The image to remove
        :type image: str

        :param force: Force removal of the image
        :type force: bool

        :param noprune: Do not delete untagged parents
        :type noprune: bool

        :rtype: None
        """
        params = {'force': force, 'noprune': noprune}
        res = self._delete(self._url("/images/" + image), params=params)
        self._raise_for_status(res)

    def restart(self, container, timeout=10):
        """
        Restart a container. Similar to the `docker restart` command.

        :param container: The container to restart
        :type container:

        :param timeout: Number of seconds to try to stop for before killing
            the container. Once killed it will then be restarted. Default is
            10 seconds.
        :type timeout: int

        :rtype: None
        """
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/restart".format(container))
        res = self._post(url, params=params)
        self._raise_for_status(res)

    def search(self, term):
        """
        Identical to the `docker search` command.

        :param term: A term to search for
        :type term: str

        :rtype: list of dicts
        :return: The response of the search

        Example:
        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> response = cli.search('nginx')
            >>> response[:2]
            [{'description': 'Official build of Nginx.',
              'is_official': True,
              'is_trusted': False,
              'name': 'nginx',
              'star_count': 266},
             {'description': 'Trusted automated Nginx (http://nginx.org/) ...',
              'is_official': False,
              'is_trusted': True,
              'name': 'dockerfile/nginx',
              'star_count': 60},

        """
        return self._result(self._get(self._url("/images/search"),
                                      params={'term': term}),
                            True)

    def start(self, container, binds=None, port_bindings=None, lxc_conf=None,
              publish_all_ports=False, links=None, privileged=False,
              dns=None, dns_search=None, volumes_from=None, network_mode=None,
              restart_policy=None, cap_add=None, cap_drop=None):
        """
        Similar to the ``docker start`` command, but doesn't support attach
        options.  Use ``docker logs`` to recover ``stdout``/``stderr``.

        ``binds`` allows to bind a directory in the host to the container. See
        "Using volumes" above for more information. ``port_bindings`` exposes
        container ports to the host. See "Port bindings" above for more
        information. ``lxc_conf`` allows to pass LXC configuration options
        using a dictionary. ``privileged`` starts the container in privileged
        mode.

        `Links`_ can be specified with the ``links`` argument. They can either
        be specified as a dictionary mapping name to alias or as a list of
        ``(name, alias)`` tuples.

        .. _Links: http://docs.docker.io/en/latest/use/working_with_links_names/

        ``dns`` and ``volumes_from`` are only available if they are used with
        version v1.10 of docker remote API. Otherwise they are ignored.

        ``network_mode`` is available since v1.11 and sets the Network mode
        for the container ('bridge': creates a new network stack for the
        container on the docker bridge, 'none': no networking for this
        container, 'container:[name|id]': reuses another container network
        stack), 'host': use the host network stack inside the container.

        ``restart_policy`` is available since v1.2.0 and sets the RestartPolicy
        for how a container should or should not be restarted on exit. By
        default the policy is set to no meaning do not restart the container
        when it exits. The user may specify the restart policy as a dictionary
        for example:

        .. code-block:: python

            {
                "MaximumRetryCount": 0,
                "Name": "always"
            }

        For always restarting the container on exit or can specify to restart
        the container to restart on failure and can limit number of restarts.
        For example:

        .. code-block:: python

            {
                "MaximumRetryCount": 5,
                "Name": "on-failure"
            }

        ``cap_add`` and ``cap_drop`` are available since v1.2.0 and can be
        used to add or drop certain capabilities. The user may specify the
        capabilities as an array for example:

        .. code-block:: python

            [
                "SYS_ADMIN",
                "MKNOD"
            ]


        :param container: The container to start
        :type container: str

        :param binds: Volumes to bind

        :param port_bindings: Port bindings. See note above
        :type port_bindings: dict

        :param lxc_conf: LXC config
        :type lxc_conf: dict

        :param publish_all_ports: Whether to publish all ports to the host
        :type publish_all_ports: bool

        :param links: See note above
        :type links: dict or list of tuples

        :param privileged: Give extended privileges to this container
        :type privileged: bool

        :param dns: Set custom DNS servers
        :type dns: list

        :param dns_search: DNS search  domains
        :type dns_search: list

        :param volumes_from:
        :type volumes_from:

        :param network_mode: One of ``['bridge', None, 'container:<name|id>',
            'host']``
        :type network_mode: str

        :param restart_policy: See note above. "Name" param must be one of
            `['on-failure', 'always']`
        :type restart_policy: dict

        :param cap_add: See note above
        :type cap_add: list of str

        :param cap_drop: See note above
        :type cap_drop: list of str

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> container = cli.create_container(
            ...     image='busybox:latest',
            ...     command='/bin/sleep 30')
            >>> response = cli.start(container=container.get('Id'))
            >>> print(response)
            None

        """
        if isinstance(container, dict):
            container = container.get('Id')

        if isinstance(lxc_conf, dict):
            formatted = []
            for k, v in six.iteritems(lxc_conf):
                formatted.append({'Key': k, 'Value': str(v)})
            lxc_conf = formatted

        start_config = {
            'LxcConf': lxc_conf
        }
        if binds:
            start_config['Binds'] = utils.convert_volume_binds(binds)

        if port_bindings:
            start_config['PortBindings'] = utils.convert_port_bindings(
                port_bindings
            )

        start_config['PublishAllPorts'] = publish_all_ports

        if links:
            if isinstance(links, dict):
                links = six.iteritems(links)

            formatted_links = [
                '{0}:{1}'.format(k, v) for k, v in sorted(links)
            ]

            start_config['Links'] = formatted_links

        start_config['Privileged'] = privileged

        if utils.compare_version('1.10', self._version) >= 0:
            if dns is not None:
                start_config['Dns'] = dns
            if volumes_from is not None:
                if isinstance(volumes_from, six.string_types):
                    volumes_from = volumes_from.split(',')
                start_config['VolumesFrom'] = volumes_from
        else:
            warning_message = ('{0!r} parameter is discarded. It is only'
                               ' available for API version greater or equal'
                               ' than 1.10')

            if dns is not None:
                warnings.warn(warning_message.format('dns'),
                              DeprecationWarning)
            if volumes_from is not None:
                warnings.warn(warning_message.format('volumes_from'),
                              DeprecationWarning)
        if dns_search:
            start_config['DnsSearch'] = dns_search

        if network_mode:
            start_config['NetworkMode'] = network_mode

        if restart_policy:
            start_config['RestartPolicy'] = restart_policy

        if cap_add:
            start_config['CapAdd'] = cap_add

        if cap_drop:
            start_config['CapDrop'] = cap_drop

        url = self._url("/containers/{0}/start".format(container))
        res = self._post_json(url, data=start_config)
        self._raise_for_status(res)

    def resize(self, container, height, width):
        if isinstance(container, dict):
            container = container.get('Id')

        params = {'h': height, 'w': width}
        url = self._url("/containers/{0}/resize".format(container))
        res = self._post(url, params=params)
        self._raise_for_status(res)

    def stop(self, container, timeout=10):
        """
        Stops a container. Similar to the ``docker stop`` command.

        :param container: The container to stop
        :type container: str

        :param timeout: Timeout in seconds to wait for the container to stop
            before sending a ``SIGKILL``
        :type timeout: int
        """
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/stop".format(container))
        res = self._post(url, params=params,
                         timeout=(timeout + self._timeout))
        self._raise_for_status(res)

    def tag(self, image, repository, tag=None, force=False):
        """
        Tag an image into a repository. Identical to the ``docker tag``
        command.

        :param image: The image to tag
        :type image: str

        :param repository: The repository to set for the tag
        :type repository: str

        :param tag: The tag name
        :type tag: str

        :param force: Force
        :type force: bool

        :returns: True if successful
        :rtype: bool
        """
        params = {
            'tag': tag,
            'repo': repository,
            'force': 1 if force else 0
        }
        url = self._url("/images/{0}/tag".format(image))
        res = self._post(url, params=params)
        self._raise_for_status(res)
        return res.status_code == 201

    def top(self, container):
        """
        Display the running processes of a container

        :param container: The container to inspect
        :type container: str

        :rtype: str
        :returns: The output of the top

        .. code-block:: python

            >>> from docker import Client
            >>> cli = Client(base_url='tcp://127.0.0.1:2375')
            >>> cli.create_container('busybox:latest', '/bin/sleep 30', name='sleeper')
            >>> cli.start('sleeper')
            >>> cli.top('sleeper')
            {'Processes': [['952', 'root', '/bin/sleep 30']],
             'Titles': ['PID', 'USER', 'COMMAND']}

        """
        u = self._url("/containers/{0}/top".format(container))
        return self._result(self._get(u), True)

    def version(self):
        return self._result(self._get(self._url("/version")), True)

    def wait(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/wait".format(container))
        res = self._post(url, timeout=None)
        self._raise_for_status(res)
        json_ = res.json()
        if 'StatusCode' in json_:
            return json_['StatusCode']
        return -1
