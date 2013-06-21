import json
import logging
from StringIO import StringIO

import requests
from requests.exceptions import HTTPError


class Client(requests.Session):
    def __init__(self, base_url="http://localhost:4243"):
        super(Client, self).__init__()
        self.base_url = base_url

    def _url(self, path):
        return self.base_url + path

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

    def _container_config(self, image, command, hostname=None, user=None, detach=False,
        stdin_open=False, tty=False, mem_limit=0, ports=None, environment=None, dns=None,
        volumes=None, volumes_from=None):
        if isinstance(command, basestring):
            command = [command]
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

    def post_json(self, url, data, **kwargs):
        # Go <1.1 can't unserialize null to a string
        # so we do this disgusting thing here.
        data2 = {}
        if data is not None:
            for k, v in data.iteritems():
                if v is not None:
                    data2[k] = v

        return self.post(url, json.dumps(data2), **kwargs)

    def build(self, dockerfile):
        bc = BuilderClient(self)
        img_id = None
        try:
            img_id = bc.build(dockerfile)
        except Exception as e:
            bc.done()
            raise e
        return img_id, bc.done()

    def commit(self, container, repository=None, tag=None, message=None, author=None, conf=None):
        params = {
            'container': container,
            'repo': repository,
            'tag': tag,
            'comment': message,
            'author': author
        }
        u = self._url("/commit")
        return self._result(self.post_json(u, conf, params=params), json=True)

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
        config = self._container_config(image, command, hostname, user,
            detach, stdin_open, tty, mem_limit, ports, environment, dns,
            volumes, volumes_from)
        return self.create_container_from_config(config)

    def create_container_from_config(self, config):
        u = self._url("/containers/create")
        res = self.post_json(u, config)
        if res.status_code == 404:
            raise ValueError("{0} is an unrecognized image. Please pull the image first.".
                format(config['Image']))
        return self._result(res, True)

    def diff(self, container):
        return self._result(self.get(self._url("/containers/{0}/changes".format(container))), True)

    def export(self, container):
        res = self.get(self._url("/containers/{0}/export".format(container)), stream=True)
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
        json_ = res.json()
        if 'username' in json_ and json_['username'] == username:
            return json_
        req_data = {
            'username': username,
            'password': password if password is not None else json_['password'],
            'email': email if email is not None else json_['email']
        }
        return self._result(self.post_json(url, req_data), True)

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
        json_ = res.json()
        return json_['NetworkSettings']['PortMapping'][private_port]

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

    def push(self, repository, registry=None):
        if repository.count("/") < 1:
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


class BuilderClient(object):
    def __init__(self, client):
        self.client = client
        self.tmp_containers = {}
        self.tmp_images = {}
        self.image = None
        self.maintainer = None
        self.need_commit = False
        self.config = {}

        self.logger = logging.getLogger(__name__)
        logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',
                    level='INFO')
        self.logs = StringIO()
        self.logger.addHandler(logging.StreamHandler(self.logs))

    def done(self):
        if self.image is None:
            # The build is unsuccessful, remove temporary containers and images
            self.client.remove_container(*self.tmp_containers)
            self.client.remove_image(*self.tmp_images)
        self.logs.flush()
        res = self.logs.getvalue()
        #self.logs.close()
        return res

    def build(self, dockerfile):
        for line in dockerfile:
            line = line.strip().replace("\t", " ", 1)
            if len(line) == 0 or line[0] == '#':
                continue
            instr, sep, args = line.partition(' ')
            if sep == '':
                self.logger.error('Invalid Dockerfile format: "{0}"'.format(line))
                return
            args = args.strip()
            self.logger.info('{0} {1} ({2})'.format(instr.upper(), args, self.image))
            try:
                method = getattr(self, 'cmd_{0}'.format(instr.lower()))
                try:
                    method(args)
                except Exception as e:
                    self.logger.exception(str(e))
                    return
            except Exception as e:
                self.logger.warning("Skipping unknown instruction {0}".format(instr.upper()))
            self.logger.info('===> {0}'.format(self.image))
        if self.need_commit:
            try:
                self.commit()
            except Exception as e:
                self.logger.exception(str(e))
                return
        if self.image is not None:
            self.logger.info("Build finished, image id: {0}".format(self.image))
            return self.image
        self.logger.error("An error has occured during the build.")
        return

    def commit(self, id=None):
        if self.image is None:
            raise Exception("Please provide a source image with `from` prior to run")
        self.config['Image'] = self.image
        if id is None:
            cmd = self.config['Cmd']
            self.config['Cmd'] = ['true']
            id = self.run()
            self.config['Cmd'] = cmd

        res = self.client.commit(id, author=self.maintainer)
        if 'Id' not in res:
            raise Exception('No ID returned by commit operation: {0}'.format(res))

        self.tmp_images[res['Id']] = {}
        self.image = res['Id']
        self.need_commit = False

    def run(self):
        if self.image is None:
            raise Exception("Please provide a source image with `from` prior to run")
        self.config['Image'] = self.image
        container = self.client.create_container_from_config(self.config)
        if container.get('Warnings', None):
            for warning in container['Warnings']:
                self.logger.warning(warning)
        self.client.start(container['Id'])
        self.tmp_containers[container['Id']] = {}
        status = self.client.wait(container['Id'])
        if status != 0:
            raise Exception("The command `{0}` returned a non-zero status: {1}".format(
                self.config['Cmd'], status))
        return container['Id']

    def merge_config(self, a, b):
        if not a.get('Hostname'):
            a['Hostname'] = b.get('Hostname')
        if not a.get('User'):
            a['User'] = b.get('User')
        if not a.get('Memory'):
            a['Memory'] = b.get('Memory')
        if not a.get('MemorySwap'):
            a['MemorySwap'] = b.get('MemorySwap')
        if not a.get('CpuShares'):
            a['CpuShares'] = b.get('CpuShares')
        if not a.get('PortSpecs') or len(a.get('PortSpecs')) == 0:
            a['PortSpecs'] = b.get('PortSpecs')

        a['Tty'] = a.get('Tty') or b.get('Tty')
        a['OpenStdin'] = a.get('OpenStdin') or b.get('OpenStdin')
        a['StdinOnce'] = a.get('StdinOnce') or b.get('StdinOnce')

        if not a.get('Env') or len(a.get('Env')) == 0:
            a['Env'] = b.get('Env')
        if not a.get('Cmd') or len(a.get('Cmd')) == 0:
            a['Cmd'] = b.get('Cmd')
        if not a.get('Dns') or len(a.get('Dns')) == 0:
            a['Dns'] = b.get('Dns')

    def cmd_from(self, name):
        img = None
        try:
            img = self.client.inspect_image(name)
        except:
            self.client.pull(name)
            img = self.client.inspect_image(name)

        self.image = img['id']
        self.logger.debug("Using image {0}".format(self.image))

    def cmd_run(self, args):
        if self.image is None:
            raise Exception("Please provide a source image with `from` prior to run")
        config = self.client._container_config(self.image, ['/bin/sh', '-c', args])
        cmd = self.config.get('Cmd', None)
        env = self.config.get('Env', None)

        self.config['Cmd'] = None
        self.merge_config(self.config, config)
        container = self.run()

        self.config['Cmd'] = cmd
        self.config['Env'] = env
        self.commit(container)

    def cmd_maintainer(self, name):
        self.need_commit = True
        self.maintainer = name

    def cmd_env(self, args):
        self.need_commit = True
        try:
            k, v = args.split(None, 1)
            if 'Env' not in self.config:
                self.config['Env'] = { k: v }
                return
            env = self.config['Env']
            for line in env:
                if line.startswith(k):
                    env[env.index(line)] = '{0}={1}'.format(k, v)
                    return
            env.extend('{0}={1}'.format(k, v))
        except ValueError:
            raise Exception("Invalid ENV format")

    def cmd_cmd(self, args):
        self.need_commit = True
        try:
            self.config['Cmd'] = json.loads(args)
        except:
            self.logger.debug("Error decoding json, using /bin/sh -c")
            self.config['Cmd'] = ['/bin/sh', '-c', args]


    def cmd_expose(self, args):
        ports = args.split()
        if 'PortSpecs' not in self.config or self.config['PortSpecs'] is None:
            self.config['PortSpecs'] = ports
            return
        self.config['PortSpecs'].append(ports)

    def cmd_insert(self, args):
        raise NotImplementedError("INSERT not implemented")
