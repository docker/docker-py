import string

import requests

class Client(requests.Session):
    def __init__(self, base_url="http://localhost:4243"):
        super(Client, self).__init__()
        self.base_url = base_url

    def _url(self, path):
        return self.base_url + path

    def _result(self, response, json=False):
        # FIXME
        if response.status_code != 200:
            response.raise_for_status()
        if json:
            return response.json()
        return response

    def build(self, dockerfile):
        url = self._url("/build")
        return self._result(self.post(url, dockerfile))

    def commit(self, container, repository=None, tag=None, message=None, author=None, conf=None):
        params = {
            'container': container,
            'repo': repository,
            'tag': tag,
            'comment': message,
            'author': author
        }
        u = self._url("/commit")
        return self._result(self.post(u, conf, params=params))

    def containers(self, quiet=False, all=False, trunc=True, latest=False, since=None, before=None, limit=-1):
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

    def create_container(self, image, command, hostname=None, user=None, detach=False,
        stdin_open=False, tty=False, mem_limit=0, ports=None, environment=None, dns=None,
        volumes=None, volumes_from=None):
        config = {
            'Hostname':     hostname,
            'PortSpecs':    ports,
            'User':         user,
            'Tty':          tty,
            'OpenStdin':    stdin_open,
            'Memory':       mem_limit,
            'AttachStdin':  0,
            'AttachStdout': 0,
            'AttachStderr': 0,
            'Env':          environment,
            'Cmd':          command,
            'Dns':          dns,
            'Image':        image,
            'Volumes':      volumes,
            'VolumesFrom':  volumes_from,
        }
        u = self._url("/containers/create")
        res = self.post(u, config)
        if res.status_code == 404:
            raise ValueError("{0} is an unrecognized image. Please pull the image first.".
                format(image))
        return self._result(res)

    def diff(self, container):
        return self._result(self.get(self._url("/containers/{0}/changes".format(container))), True)

    def export(self, container):
        res = self.get(self._url("/containers/{0}/export".format(container)), stream=True)
        return res.raw

    def history(self, image):
        res = self.get(self._url("/images/{0}/history".format(image)))
        if res.status_code == 500 and string.count(res.text, "Image does not exist") == 1:
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
        return self._result(self.get(self._url("/images/json"), params=params), True)

    def import_image(self, src, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'repo': repository,
            'tag': tag
        }
        if type(src) == str or type(src) == unicode:
            params['fromSrc'] = src
            return self._result(self.post(u, None, params=params))

        return self._result(self.post(u, src, params=params))

    def info(self):
        return self._result(self.get(self._url("/info")), True)

    def insert(self, image, url, path):
        url = self._url("/images/" + image)
        params = {
            'url': url,
            'path': path
        }
        return self._result(self.post(url, None, params=params))

    def inspect_container(self, container_id):
        return self._result(self.get(self._url("/containers/{0}/json".format(container_id))), True)

    def inspect_image(self, image_id):
        return self._result(self.get(self._url("/images/{0}/json".format(image_id))), True)

    def kill(self, *args):
        for name in args:
            url = self._url("/containers/{0}/kill".format(name))
            self.post(url, None)

    def login(self, username, password=None, email=None):
        url = self._url("/auth")
        res = self.get(url)
        json = res.json()
        if 'username' in json and json['username'] == username:
            return json
        req_data = {
            'username': username,
            'password': password if password is not None else json['password'],
            'email': email if email is not None else json['email']
        }
        return self._result(self.post(url, req_data), True)

    def logs(self, container):
        params = {
            'logs': 1,
            'stdout': 1,
            'stderr': 1
        }
        u = self._url("/containers/{0}/attach".format(container))
        res = self.post(u, None, params=params)
        return res.raw

    def port(self, container, private_port):
        res = self.get(self._url("/containers/{0}/json".format(container)))
        json = res.json()
        return json['NetworkSettings']['PortMapping'][private_port]

    def pull(self, repository, tag=None, registry=None):
        if string.count(repository, ":") == 1:
            tag, repository = string.split(repository, ":")

        params = {
            'tag': tag,
            'fromImage': repository,
            'registry': registry
        }
        u = self._url("/images/create")
        return self._result(self.post(u, None, params=params))

    def push(self, repository, registry=None):
        if string.count(repository, "/") != 1:
            raise ValueError("Impossible to push a \"root\" repository. Please rename your repository in <user>/<repo>")
        u = self._url("/images/{0}/push".format(repository))
        return self._result(self.post(u, None, params={'registry': registry}))

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
        return self._result(self.get(self._url("/images/search"), params={'term': term}),
            True)

    def start(self, *args):
        for name in args:
            url = self._url("/containers/{0}/start".format(name))
            self.post(url, None)

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
        return self._result(self.post(url, None, params=params))

    def version(self):
        return self._result(self.get(self._url("/version")), True)

    def wait(self, *args):
        result = []
        for name in args:
            url = self._url("/containers/{0}/wait".format(name))
            res = self.post(url, None, timeout=None)
            json = res.json()
            if 'StatusCode' in json:
                result.append(json['StatusCode'])
        return result
