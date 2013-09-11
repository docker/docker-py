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

import requests
import requests.exceptions
import six

import auth
import unixconn
import utils


class APIError(requests.exceptions.HTTPError):
    def __init__(self, message, response, explanation=None):
        super(APIError, self).__init__(message, response=response)

        self.explanation = explanation

        if self.explanation is None and response.content and len(response.content) > 0:
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
    def __init__(self, base_url="unix://var/run/docker.sock", version="1.4"):
        super(Client, self).__init__()
        self.mount('unix://', unixconn.UnixAdapter(base_url))
        self.base_url = base_url
        self._version = version
        try:
            self._cfg = auth.load_config()
        except Exception:
            pass

    def _url(self, path):
        return '{0}/v{1}{2}'.format(self.base_url, self._version, path)

    def _raise_for_status(self, response, explanation=None):
        """Raises stored :class:`APIError`, if one occurred."""
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError, e:
            raise APIError(e, response=response, explanation=explanation)

    def _result(self, response, json=False):
        self._raise_for_status(response)

        if json:
            return response.json()
        return response.text

    def _container_config(self, image, command, hostname=None, user=None,
        detach=False, stdin_open=False, tty=False, mem_limit=0, ports=None,
        environment=None, dns=None, volumes=None, volumes_from=None,
        privileged=False):
        if isinstance(command, six.string_types):
            command = shlex.split(str(command))
        if isinstance(environment, dict):
            environment = ['{0}={1}'.format(k, v) for k, v in environment.items()]

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
            'PortSpecs':    ports,
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
            'Privileged': privileged,
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
        return self.post(url, json.dumps(data2), **kwargs)

    def attach_socket(self, container, params=None):
        if params is None:
            params = {
                'stdout': 1,
                'stderr': 1,
                'stream': 1
            }
        if isinstance(container, dict):
            container = container.get('Id')

        u = self._url("/containers/{0}/attach".format(container))
        res = self.post(u, None, params=params, stream=True)
        self._raise_for_status(res)
        # hijack the underlying socket from requests, icky
        # but for some reason requests.iter_contents and ilk
        # eventually block
        return res.raw._fp.fp._sock

    def attach(self, container):
        socket = self.attach_socket(container)

        while True:
            chunk = socket.recv(4096)
            if chunk:
                yield chunk
            else:
                break

    def build(self, path=None, tag=None, quiet=False, fileobj=None, nocache=False):
        remote = context = headers = None
        if path is None and fileobj is None:
            raise Exception("Either path or fileobj needs to be provided.")

        if fileobj is not None:
            context = utils.mkbuildcontext(fileobj)
        elif (path.startswith('http://') or path.startswith('https://') or
        path.startswith('git://') or path.startswith('github.com/')):
            remote = path
        else:
            context = utils.tar(path)

        u = self._url('/build')
        params = { 't': tag, 'remote': remote, 'q': quiet, 'nocache': nocache }
        if context is not None:
            headers = { 'Content-Type': 'application/tar' }
        res = self._result(self.post(u, context, params=params,
            headers=headers, stream=True))
        if context is not None:
            context.close()
        srch = r'Successfully built ([0-9a-f]+)'
        match = re.search(srch, res)
        if not match:
            return None, res
        return match.group(1), res

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
        return self._result(self._post_json(u, conf, params=params), json=True)

    def containers(self, quiet=False, all=False, trunc=True, latest=False,
        since=None, before=None, limit=-1):
        params = {
            'limit': 1 if latest else limit,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
            'trunc_cmd': 1 if trunc else 0,
            'since': since,
            'before': before
        }
        u = self._url("/containers/ps")
        return self._result(self.get(u, params=params), True)

    def copy(self, container, resource):
        res = self._post_json(self._url("/containers/{0}/copy".format(container)),
            {"Resource": resource},
            stream=True)
        self._raise_for_status(res)
        return res.raw

    def create_container(self, image, command, hostname=None, user=None,
        detach=False, stdin_open=False, tty=False, mem_limit=0, ports=None,
        environment=None, dns=None, volumes=None, volumes_from=None,
        privileged=False):
        config = self._container_config(image, command, hostname, user,
            detach, stdin_open, tty, mem_limit, ports, environment, dns,
            volumes, volumes_from, privileged)
        return self.create_container_from_config(config)

    def create_container_from_config(self, config):
        u = self._url("/containers/create")
        res = self._post_json(u, config)
        if res.status_code == 404:
            self._raise_for_status(res, explanation="{0} is an unrecognized image. Please pull the "
                "image first.".format(config['Image']))
        return self._result(res, True)

    def diff(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(self.get(self._url("/containers/{0}/changes".
            format(container))), True)

    def export(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self.get(self._url("/containers/{0}/export".format(container)),
            stream=True)
        self._raise_for_status(res)
        return res.raw

    def history(self, image):
        res = self.get(self._url("/images/{0}/history".format(image)))
        self._raise_for_status(res)
        return self._result(res)

    def images(self, name=None, quiet=False, all=False, viz=False):
        if viz:
            return self._result(self.get(self._url("images/viz")))
        params = {
            'filter': name,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
        }
        res = self._result(self.get(self._url("/images/json"), params=params),
            True)
        if quiet:
            return [x['Id'] for x in res]
        return res

    def import_image(self, src, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'repo': repository,
            'tag': tag
        }
        if isinstance(src, six.string_types):
            params['fromSrc'] = src
            return self._result(self.post(u, None, params=params))

        return self._result(self.post(u, src, params=params))

    def info(self):
        return self._result(self.get(self._url("/info")), True)

    def insert(self, image, url, path):
        api_url = self._url("/images/" + image + "/insert")
        params = {
            'url': url,
            'path': path
        }
        return self._result(self.post(api_url, None, params=params))

    def inspect_container(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        return self._result(self.get(self._url("/containers/{0}/json".
            format(container))), True)

    def inspect_image(self, image_id):
        return self._result(self.get(self._url("/images/{0}/json".
            format(image_id))), True)

    def kill(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/kill".format(container))
        res = self.post(url, None)
        self._raise_for_status(res)

    def login(self, username, password=None, email=None):
        url = self._url("/auth")
        res = self.get(url)
        json_ = res.json()
        if 'username' in json_ and json_['username'] == username:
            return json_
        req_data = {
            'username': username,
            'password': password if password is not None else json_['password'],
            'email': email if email is not None else json_['email']
        }
        res = self._result(self._post_json(url, req_data), True)
        try:
            self._cfg = auth.load_config()
        finally:
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
        return self._result(self.post(u, None, params=params))

    def port(self, container, private_port):
        if isinstance(container, dict):
            container = container.get('Id')
        res = self.get(self._url("/containers/{0}/json".format(container)))
        self._raise_for_status(res)
        json_ = res.json()
        s_port = str(private_port)
        f_port = None
        if s_port in json_['NetworkSettings']['PortMapping']['Udp']:
            f_port = json_['NetworkSettings']['PortMapping']['Udp'][s_port]
        elif s_port in json_['NetworkSettings']['PortMapping']['Tcp']:
            f_port = json_['NetworkSettings']['PortMapping']['Tcp'][s_port]

        return f_port

    def pull(self, repository, tag=None):
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
            headers = { 'X-Registry-Auth': auth.encode_header(authcfg) }

        u = self._url("/images/create")
        return self._result(self.post(u, params=params, headers=headers))

    def push(self, repository):
        registry, repository = auth.resolve_repository_name(repository)
        if getattr(self, '_cfg', None) is None:
            self._cfg = auth.load_config()
        authcfg = auth.resolve_authconfig(self._cfg, registry)
        u = self._url("/images/{0}/push".format(repository))
        if utils.compare_version('1.5', self._version) >= 0:
            headers = { 'X-Registry-Auth': auth.encode_header(authcfg) }
            return self._result(self._post_json(u, None, headers=headers))
        return self._result(self._post_json(u, authcfg))

    def remove_container(self, container, v=False):
        if isinstance(container, dict):
            container = container.get('Id')
        params = { 'v': v }
        res = self.delete(self._url("/containers/" + container), params=params)
        self._raise_for_status(res)

    def remove_image(self, image):
        res = self.delete(self._url("/images/" + image))
        self._raise_for_status(res)

    def restart(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = { 't': timeout }
        url = self._url("/containers/{0}/restart".format(container))
        res = self.post(url, None, params=params)
        self._raise_for_status(res)

    def search(self, term):
        return self._result(self.get(self._url("/images/search"),
            params={'term': term}), True)

    def start(self, container, binds=None, lxc_conf=None):
        if isinstance(container, dict):
            container = container.get('Id')
        start_config = {
            'LxcConf': lxc_conf
        }
        if binds:
            bind_pairs = ['{0}:{1}'.format(host, dest) for host, dest in binds.items()]
            start_config['Binds'] = bind_pairs

        url = self._url("/containers/{0}/start".format(container))
        res = self._post_json(url, start_config)
        self._raise_for_status(res)

    def stop(self, container, timeout=10):
        if isinstance(container, dict):
            container = container.get('Id')
        params = { 't': timeout }
        url = self._url("/containers/{0}/stop".format(container))
        res = self.post(url, None, params=params)
        self._raise_for_status(res)

    def tag(self, image, repository, tag=None, force=False):
        params = {
            'tag': tag,
            'repo': repository,
            'force': 1 if force else 0
        }
        url = self._url("/images/{0}/tag".format(image))
        res = self.post(url, None, params=params)
        self._raise_for_status(res)
        return res.status_code == 201

    def top(self, container):
        u = self._url("/containers/{0}/top".format(container))
        return self._result(self.get(u), True)

    def version(self):
        return self._result(self.get(self._url("/version")), True)

    def wait(self, container):
        if isinstance(container, dict):
            container = container.get('Id')
        url = self._url("/containers/{0}/wait".format(container))
        res = self.post(url, None, timeout=None)
        self._raise_for_status(res)
        json_ = res.json()
        if 'StatusCode' in json_:
            return json_['StatusCode']
        return -1
