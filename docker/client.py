import base64
import json
import logging
import os
import re
import six
import shlex
import tarfile
import tempfile
import six
import httplib
import socket

import requests
from requests.exceptions import HTTPError
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.connectionpool import HTTPConnectionPool

if six.PY3:
    from io import StringIO
else:
    from StringIO import StringIO

class UnixHTTPConnection(httplib.HTTPConnection, object):
    def __init__(self, base_url, unix_socket):
        httplib.HTTPConnection.__init__(self, 'localhost')
        self.base_url = base_url
        self.unix_socket = unix_socket

    def connect(self):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(self.base_url.replace("unix:/",""))
        self.sock = sock

    def _extract_path(self, url):
        #remove the base_url entirely..
        return url.replace(self.base_url, "")

    def request(self, method, url, **kwargs):
        url = self._extract_path(self.unix_socket)
        super(UnixHTTPConnection, self).request(method, url, **kwargs)


class UnixHTTPConnectionPool(HTTPConnectionPool):
    def __init__(self, base_url, socket_path):
        self.socket_path = socket_path
        self.base_url = base_url
        super(UnixHTTPConnectionPool, self).__init__(self, 'localhost')

    def _new_conn(self):
        return UnixHTTPConnection(self.base_url, self.socket_path)


class UnixAdapter(HTTPAdapter):
    def __init__(self, base_url):
        self.base_url = base_url
        super(UnixAdapter, self).__init__()

    def get_connection(self, socket_path, proxies=None):
        return UnixHTTPConnectionPool(self.base_url, socket_path)


class Client(requests.Session):
    def __init__(self, base_url="unix://var/run/docker.sock", version="1.4"):
        super(Client, self).__init__()
        self.mount('unix://', UnixAdapter(base_url))
        self.base_url = base_url
        self._version = version
        try:
            self._cfg = self._load_config()
        except:
            pass

    def _url(self, path):
        return '{0}/v{1}{2}'.format(self.base_url, self._version, path)

    def _raise_for_status(self, response):
        """Raises stored :class:`HTTPError`, if one occurred."""
        http_error_msg = ''

        if 400 <= response.status_code < 500:
            http_error_msg = '%s Client Error: %s' % (
                response.status_code, response.reason)

        elif 500 <= response.status_code < 600:
            http_error_msg = '%s Server Error: %s' % (
                response.status_code, response.reason)
            if response.content and len(response.content) > 0:
                http_error_msg += ' "%s"' % response.content

        if http_error_msg:
            raise HTTPError(http_error_msg, response=response)

    def _result(self, response, json=False):
        if response.status_code != 200 and response.status_code != 201:
            self._raise_for_status(response)
        if json:
            return response.json()
        return response.text

    def _container_config(self, image, command, hostname=None, user=None,
        detach=False, stdin_open=False, tty=False, mem_limit=0, ports=None,
        environment=None, dns=None, volumes=None, volumes_from=None):
        if isinstance(command, six.string_types):
            command = shlex.split(str(command))
        return {
            'Hostname':     hostname,
            'PortSpecs':    ports,
            'User':         user,
            'Tty':          tty,
            'OpenStdin':    stdin_open,
            'Memory':       mem_limit,
            'AttachStdin':  False,
            'AttachStdout': False,
            'AttachStderr': False,
            'Env':          environment,
            'Cmd':          command,
            'Dns':          dns,
            'Image':        image,
            'Volumes':      volumes,
            'VolumesFrom':  volumes_from,
        }

    def _mkbuildcontext(self, dockerfile):
        f = tempfile.TemporaryFile()
        t = tarfile.open(mode='w', fileobj=f)
        if isinstance(dockerfile, StringIO):
            dfinfo = tarfile.TarInfo('Dockerfile')
            dfinfo.size = dockerfile.len
        else:
            dfinfo = t.gettarinfo(fileobj=dockerfile, arcname='Dockerfile')
        t.addfile(dfinfo, dockerfile)
        t.close()
        f.seek(0)
        return f

    def _tar(self, path):
        f = tempfile.TemporaryFile()
        t = tarfile.open(mode='w', fileobj=f)
        t.add(path, arcname='.')
        t.close()
        f.seek(0)
        return f

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

    def _decode_auth(self, auth):
        s = base64.b64decode(auth)
        login, pwd = s.split(':')
        return login, pwd

    def _load_config(self, root=None):
        if root is None:
            root = os.environ['HOME']
        config_file = {
            'Configs': {},
            'rootPath': root
        }
        f = open(os.path.join(root, '.dockercfg'))
        try:
            config_file['Configs'] = json.load(f)
            for k, conf in six.iteritems(config_file['Configs']):
                conf['Username'], conf['Password'] = self._decode_auth(conf['Auth'])
                del conf['Auth']
                config_file['Configs'][k] = conf
        except:
            f.seek(0)
            buf = []
            for line in f:
                k, v = line.split(' = ')
                buf.append(v)
            if len(buf) < 2:
                raise Exception("The Auth config file is empty")
            user, pwd = self._decode_auth(buf[0])
            config_file['Configs']['index.docker.io'] = {
                'Username': user,
                'Password': pwd,
                'Email': buf[1]
            }
        finally:
            f.close()
        return config_file

    def attach(self, container):
        params = {
            'stdout': 1,
            'stderr': 1,
            'stream': 1
        }
        u = self._url("/containers/{0}/attach".format(container))
        res = self.post(u, None, params=params, stream=True)
        # hijack the underlying socket from requests, icky
        # but for some reason requests.iter_contents and ilk
        # eventually block
        socket = res.raw._fp.fp._sock

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
            context = self._mkbuildcontext(fileobj)
        elif (path.startswith('http://') or path.startswith('https://') or
        path.startswith('git://') or path.startswith('github.com/')):
            remote = path
        else:
            context = self._tar(path)

        u = self._url('/build')
        params = { 'tag': tag, 'remote': remote, 'q': quiet, 'nocache': nocache }
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

    def create_container(self, image, command, hostname=None, user=None,
        detach=False, stdin_open=False, tty=False, mem_limit=0, ports=None,
        environment=None, dns=None, volumes=None, volumes_from=None):
        config = self._container_config(image, command, hostname, user,
            detach, stdin_open, tty, mem_limit, ports, environment, dns,
            volumes, volumes_from)
        return self.create_container_from_config(config)

    def create_container_from_config(self, config):
        u = self._url("/containers/create")
        res = self._post_json(u, config)
        if res.status_code == 404:
            raise ValueError("{0} is an unrecognized image. Please pull the "
                "image first.".format(config['Image']))
        return self._result(res, True)

    def diff(self, container):
        return self._result(self.get(self._url("/containers/{0}/changes".
            format(container))), True)

    def export(self, container):
        res = self.get(self._url("/containers/{0}/export".format(container)),
            stream=True)
        return res.raw

    def history(self, image):
        res = self.get(self._url("/images/{0}/history".format(image)))
        if res.status_code == 500 and res.text.find("Image does not exist") != -1:
            raise KeyError(res.text)
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

    def inspect_container(self, container_id):
        return self._result(self.get(self._url("/containers/{0}/json".
            format(container_id))), True)

    def inspect_image(self, image_id):
        return self._result(self.get(self._url("/images/{0}/json".
            format(image_id))), True)

    def kill(self, *args):
        for name in args:
            url = self._url("/containers/{0}/kill".format(name))
            self.post(url, None)

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
            self._cfg = self._load_config()
        finally:
            return res

    def logs(self, container):
        params = {
            'logs': 1,
            'stdout': 1,
            'stderr': 1
        }
        u = self._url("/containers/{0}/attach".format(container))
        return self._result(self.post(u, None, params=params))

    def port(self, container, private_port):
        res = self.get(self._url("/containers/{0}/json".format(container)))
        json_ = res.json()
        s_port = str(private_port)
        f_port = None
        if s_port in json_['NetworkSettings']['PortMapping']['Udp']:
            f_port = json_['NetworkSettings']['PortMapping']['Udp'][s_port]
        elif s_port in json_['NetworkSettings']['PortMapping']['Tcp']:
            f_port = json_['NetworkSettings']['PortMapping']['Tcp'][s_port]

        return f_port

    def pull(self, repository, tag=None, registry=None):
        if repository.count(":") == 1:
            repository, tag = repository.split(":")

        params = {
            'tag': tag,
            'fromImage': repository,
            'registry': registry
        }
        u = self._url("/images/create")
        return self._result(self.post(u, None, params=params))

    def push(self, repository):
        if repository.count("/") < 1:
            raise ValueError("""Impossible to push a \"root\" repository.
                Please rename your repository in <user>/<repo>""")
        if self._cfg is None:
            self._cfg = self._load_config()
        u = self._url("/images/{0}/push".format(repository))
        return self._result(
            self._post_json(u, self._cfg['Configs']['index.docker.io']))

    def remove_container(self, *args, **kwargs):
        params = {
            'v': 1 if kwargs.get('v', False) else 0
        }
        for container in args:
            self.delete(self._url("/containers/" + container), params=params)

    def remove_image(self, *args):
        for image in args:
            self.delete(self._url("/images/" + image))

    def restart(self, *args, **kwargs):
        params = {
            't': kwargs.get('timeout', 10)
        }
        for name in args:
            url = self._url("/containers/{0}/restart".format(name))
            self.post(url, None, params=params)

    def search(self, term):
        return self._result(self.get(self._url("/images/search"),
            params={'term': term}), True)

    def start(self, *args, **kwargs):
        start_config = {}
        binds = kwargs.pop('binds', '')
        if binds:
            bind_pairs = ['{0}:{1}'.format(host, dest) for host, dest in binds.items()]
            start_config = {
                'Binds': bind_pairs,
            }

        for name in args:
            url = self._url("/containers/{0}/start".format(name))
            self._post_json(url, start_config)

    def stop(self, *args, **kwargs):
        params = {
            't': kwargs.get('timeout', 10)
        }
        for name in args:
            url = self._url("/containers/{0}/stop".format(name))
            self.post(url, None, params=params)

    def tag(self, image, repository, tag=None, force=False):
        params = {
            'tag': tag,
            'repo': repository,
            'force': 1 if force else 0
        }
        url = self._url("/images/{0}/tag".format(image))
        res = self.post(url, None, params=params)
        res.raise_for_status()
        return res.status_code == 201

    def version(self):
        return self._result(self.get(self._url("/version")), True)

    def wait(self, *args):
        result = []
        for name in args:
            url = self._url("/containers/{0}/wait".format(name))
            res = self.post(url, None, timeout=None)
            json_ = res.json()
            if 'StatusCode' in json_:
                result.append(json_['StatusCode'])
        if len(result) == 1:
            return result[0]
        return result
