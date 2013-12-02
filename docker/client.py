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
import re
import shlex
import struct

import requests
import requests.exceptions
import six

import docker.auth as auth
import docker.unixconn as unixconn
import docker.utils as utils

if not six.PY3:
    import websocket

DEFAULT_TIMEOUT_SECONDS = 60


class APIError(requests.exceptions.HTTPError):
    def __init__(self, message, response, explanation=None):
        super(APIError, self).__init__(message, response)

        self.response = response
        self.explanation = explanation

        if self.explanation is None and response.content:
            self.explanation = response.content.strip()

    def __str__(self):
        message = super(APIError, self).__str__()

        if self.is_client_error():
            message = '%s Client Error: %s' % (
                self.response.status_code, self.response.reason)

        elif self.is_server_error():
            message = '%s Server Error: %s' % (
                self.response.status_code, self.response.reason)

        if self.explanation:
            message = '%s ("%s")' % (message, self.explanation)

        return message

    def is_client_error(self):
        return 400 <= self.response.status_code < 500

    def is_server_error(self):
        return 500 <= self.response.status_code < 600


class Client(requests.Session):
    def __init__(self, base_url="unix://var/run/docker.sock", version="1.6",
                 timeout=DEFAULT_TIMEOUT_SECONDS):
        super(Client, self).__init__()
        if base_url.startswith('unix:///'):
            base_url = base_url.replace('unix:/', 'unix:')
        self.base_url = base_url
        self._version = version
        self._timeout = timeout

        self.mount('unix://', unixconn.UnixAdapter(base_url, timeout))
        try:
            self._cfg = auth.load_config()
        except Exception:
            pass

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
            raise APIError(e, response, explanation=explanation)

    def _stream_result(self, response):
        self._raise_for_status(response)
        for line in response.iter_lines(chunk_size=1):
            # filter out keep-alive new lines
            if line:
                yield line + '\n'

    def _stream_result_socket(self, response):
        self._raise_for_status(response)
        return response.raw._fp.fp._sock

    def _result(self, response, json=False):
        self._raise_for_status(response)

        if json:
            return response.json()
        return response.text

    def _container_config(self, image, command, hostname=None, user=None,
                          detach=False, stdin_open=False, tty=False,
                          mem_limit=0, ports=None, environment=None, dns=None,
                          volumes=None, volumes_from=None, privileged=False):
        if isinstance(command, six.string_types):
            command = shlex.split(str(command))
        if isinstance(environment, dict):
            environment = [
                '{0}={1}'.format(k, v) for k, v in environment.items()
            ]

        attach_stdin = False
        attach_stdout = False
        attach_stderr = False

        if not detach:
            attach_stdout = True
            attach_stderr = True

            if stdin_open:
                attach_stdin = True

        return {
            'Hostname':     hostname,
            'ExposedPorts': ports,
            'User':         user,
            'Tty':          tty,
            'OpenStdin':    stdin_open,
            'Memory':       mem_limit,
            'AttachStdin':  attach_stdin,
            'AttachStdout': attach_stdout,
            'AttachStderr': attach_stderr,
            'Env':          environment,
            'Cmd':          command,
            'Dns':          dns,
            'Image':        image,
            'Volumes':      volumes,
            'VolumesFrom':  volumes_from,
            'Privileged':   privileged,
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

    def _stream_helper(self, response):
        socket = self._stream_result_socket(response)
        while True:
            chunk = socket.recv(4096)
            if chunk:
                parts = chunk.strip().split('\r\n')
                for i in range(len(parts)):
                    if i % 2 != 0:
                        yield parts[i] + '\n'
                    else:
                        size = int(parts[i], 16)
                if size <= 0:
                    break
            else:
                break

    def attach(self, container):
        socket = self.attach_socket(container)

        while True:
            chunk = socket.recv(4096)
            if chunk:
                yield chunk
            else:
                break

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
        return self._stream_result_socket(self.post(
            u, None, params=self._attach_params(params), stream=True))

    def build(self, path=None, tag=None, quiet=False, fileobj=None,
              nocache=False, rm=False, stream=False):
        remote = context = headers = None
        if path is None and fileobj is None:
            raise Exception("Either path or fileobj needs to be provided.")

        if fileobj is not None:
            context = utils.mkbuildcontext(fileobj)
        elif path.startswith(('http://', 'https://', 'git://', 'github.com/')):
            remote = path
        else:
            context = utils.tar(path)

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

        response = self._post(
            u, data=context, params=params, headers=headers, stream=stream
        )

        if context is not None:
            context.close()
        if stream:
            return self._stream_result(response)
        else:
            output = self._result(response)
            srch = r'Successfully built ([0-9a-f]+)'
            match = re.search(srch, output)
            if not match:
                return None, output
            return match.group(1), output

    def commit(self, container, repository=None, tag=None, message=None,
               author=None, conf=None):
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
                   since=None, before=None, limit=-1):
        params = {
            'limit': 1 if latest else limit,
            'all': 1 if all else 0,
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
                         volumes=None, volumes_from=None, privileged=False,
                         name=None):

        config = self._container_config(
            image, command, hostname, user, detach, stdin_open, tty, mem_limit,
            ports, environment, dns, volumes, volumes_from, privileged
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
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(self._get(self._url("/containers/{0}/changes".
                            format(container))), True)

    def events(self):
        u = self._url("/events")

        socket = self._stream_result_socket(self.get(u, stream=True))

        while True:
            chunk = socket.recv(4096)
            if chunk:
                # Messages come in the format of length, data, newline.
                length, data = chunk.split("\n", 1)
                length = int(length, 16)
                if length > len(data):
                    data += socket.recv(length - len(data))
                yield json.loads(data)
            else:
                break

    def export(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/export".format(container)),
                        stream=True)
        self._raise_for_status(res)
        return res.raw

    def history(self, image):
        res = self._get(self._url("/images/{0}/history".format(image)))
        self._raise_for_status(res)
        return self._result(res)

    def images(self, name=None, quiet=False, all=False, viz=False):
        if viz:
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

    def import_image(self, src, data=None, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'repo': repository,
            'tag': tag
        }
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

    def info(self):
        return self._result(self._get(self._url("/info")),
                            True)

    def insert(self, image, url, path):
        api_url = self._url("/images/" + image + "/insert")
        params = {
            'url': url,
            'path': path
        }
        return self._result(self._post(api_url, params=params))

    def inspect_container(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(
            self._get(self._url("/containers/{0}/json".format(container))),
            True)

    def inspect_image(self, image_id):
        return self._result(
            self._get(self._url("/images/{0}/json".format(image_id))),
            True
        )

    def kill(self, container, signal=None):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/kill".format(container))
        params = {}
        if signal is not None:
            params['signal'] = signal
        res = self._post(url, params=params)

        self._raise_for_status(res)

    def login(self, username, password=None, email=None, registry=None):
        url = self._url("/auth")
        if registry is None:
            registry = auth.INDEX_URL
        if getattr(self, '_cfg', None) is None:
            self._cfg = auth.load_config()
        authcfg = auth.resolve_authconfig(self._cfg, registry)
        if 'username' in authcfg and authcfg['username'] == username:
            return authcfg
        req_data = {
            'username': username,
            'password': password,
            'email': email
        }
        res = self._result(self._post_json(url, data=req_data), True)
        if res['Status'] == 'Login Succeeded':
            self._cfg['Configs'][registry] = req_data
        return res

    def logs(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {
            'logs': 1,
            'stdout': 1,
            'stderr': 1
        }
        u = self._url("/containers/{0}/attach".format(container))
        if utils.compare_version('1.6', self._version) < 0:
            return self._result(self._post(u, params=params))
        res = ''
        response = self._result(self._post(u, params=params))
        walker = 0
        while walker < len(response):
            header = response[walker:walker+8]
            walker += 8
            # we don't care about the type of stream since we want both
            # stdout and stderr
            length = struct.unpack(">L", header[4:].encode())[0]
            res += response[walker:walker+length]
            walker += length
        return res

    def port(self, container, private_port):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self._get(self._url("/containers/{0}/json".format(container)))
        self._raise_for_status(res)
        json_ = res.json()
        s_port = str(private_port)
        f_port = None
        if s_port in json_['NetworkSettings']['PortMapping']['Udp']:
            f_port = json_['NetworkSettings']['PortMapping']['Udp'][s_port]
        elif s_port in json_['NetworkSettings']['PortMapping']['Tcp']:
            f_port = json_['NetworkSettings']['PortMapping']['Tcp'][s_port]

        return f_port

    def pull(self, repository, tag=None, stream=False):
        registry, repo_name = auth.resolve_repository_name(repository)
        if repo_name.count(":") == 1:
            repository, tag = repository.rsplit(":", 1)

        params = {
            'tag': tag,
            'fromImage': repository
        }
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            if getattr(self, '_cfg', None) is None:
                self._cfg = auth.load_config()
            authcfg = auth.resolve_authconfig(self._cfg, registry)
            # do not fail if no atuhentication exists
            # for this specific registry as we can have a readonly pull
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)
        u = self._url("/images/create")
        response = self._post(u, params=params, headers=headers, stream=stream)

        if stream:
            return self._stream_helper(response)
        else:
            return self._result(response)

    def push(self, repository, stream=False):
        registry, repo_name = auth.resolve_repository_name(repository)
        u = self._url("/images/{0}/push".format(repository))
        headers = {}
        if getattr(self, '_cfg', None) is None:
            self._cfg = auth.load_config()
        authcfg = auth.resolve_authconfig(self._cfg, registry)
        if utils.compare_version('1.5', self._version) >= 0:
            # do not fail if no atuhentication exists
            # for this specific registry as we can have an anon push
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)

            if stream:
                return self._stream_helper(
                    self._post_json(u, None, headers=headers, stream=True))
            else:
                return self._result(
                    self._post_json(u, None, headers=headers, stream=False))
        if stream:
            return self._stream_helper(
                self._post_json(u, authcfg, stream=True))
        else:
            return self._result(self._post_json(u, authcfg, stream=False))

    def remove_container(self, container, v=False, link=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'v': v, 'link': link}
        res = self._delete(self._url("/containers/" + container),
                           params=params)
        self._raise_for_status(res)

    def remove_image(self, image):
        res = self._delete(self._url("/images/" + image))
        self._raise_for_status(res)

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

    def start(self, container, binds=None, port_bindings=None, lxc_conf=None,
              publish_all_ports=False, links=None):
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
            bind_pairs = [
                '{0}:{1}'.format(host, dest) for host, dest in binds.items()
            ]
            start_config['Binds'] = bind_pairs

        if port_bindings:
            start_config['PortBindings'] = port_bindings

        start_config['PublishAllPorts'] = publish_all_ports

        if links:
            formatted_links = [
                '{0}:{1}'.format(k, v) for k, v in six.iteritems(links)
            ]

            start_config['Links'] = formatted_links

        url = self._url("/containers/{0}/start".format(container))
        res = self._post_json(url, data=start_config)
        self._raise_for_status(res)

    def stop(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = {'t': timeout}
        url = self._url("/containers/{0}/stop".format(container))
        res = self._post(url, params=params,
                         timeout=max(timeout, self._timeout))
        self._raise_for_status(res)

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

    def top(self, container):
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
