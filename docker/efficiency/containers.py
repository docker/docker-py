import io
import tarfile

import six

from . import commons
from . import images


def copy_to_fs(client, container, path, target="."):
    """
    Copy file from container to filesystem

    **Params:**
        client: a docker `Client` object
        container_id: ID of the container to copy from
        path: path to the file in the container
        target: folder where file will be copied (default ".")
    """
    response = client.copy(container, path)
    buffer = io.BytesIO()
    buffer.write(response.data)
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer, mode='r|')
    tar.extractall(path=target)


def start_auto_remove(client, container, *args, **kwargs):
    """
    Start a container and try to remove it when it's finished running,
    similar to using --autorm in the docker CLI.
    **Params:**
        client: a docker `Client` object
        container: ID of the container to be started
        args, kwargs: `Client.start()` arguments
    """
    client.start(container, *args, **kwargs)
    if client.wait(container) == 0:
        return client.remove_container(container)


class Exec(commons.Interactive):
    def __init__(self, client, id):
        super(Exec, self).__init__(client, id)
        data = self._client.exec_inspect(self.id)
        for k, v in six.iteritems(data):
            if k == 'Id':
                continue
            setattr(self, commons.to_snakecase(k), v)

    def start(self, detach=False, tty=False, stream=False):
        return self._client.exec_start(self.id, detach, tty, stream)

    def resize(self, height=None, width=None):
        self._client.exec_resize(self.id, height, width)

    def __str__(self):
        return '<DockerExec(id={0})>'.format(self.id[:16])

    def __repr__(self):
        return str(self)


class Container(commons.Interactive):

    @classmethod
    def list(cls, all=False, latest=False,
             since=None, before=None, limit=-1, size=False, filters=None):
        from . import efficiency
        lst = efficiency._client.containers(
            quiet=True, all=all, trunc=False, latest=latest, since=since,
            before=before, limit=limit, size=size, filters=filters
        )
        return [cls(efficiency._client, x.get('Id')) for x in lst]

    def __init__(self, *args, **kwargs):
        super(Container, self).__init__(*args, **kwargs)
        self._update()

    def _update(self):
        data = self._client.inspect_container(self.id)
        for k, v in six.iteritems(data):
            if k == 'Id':
                self._id = v
                continue
            setattr(self, commons.to_snakecase(k), v)

    def commit(self, repository=None, tag=None, message=None, author=None,
               conf=None):
        return images.Image(
            self._client, self._client.commit(
                self.id, repository, tag, message, author, conf
            ).get('Id')
        )

    def diff(self):
        return self._client.diff(self.id)

    def exec_create(self, cmd, stdout=True, stderr=True, tty=False,
                    privileged=False):
        return Exec(self._client, self._client.exec_create(
            self.id, cmd, stdout, stderr, tty, privileged
        ).get('Id'))

    def pause(self):
        return self._client.pause(self.id)

    def unpause(self):
        return self._client.unpause(self.id)

    def kill(self, signal=None):
        self._client.kill(self.id, signal)
        self._update()

    def start(self):
        self._client.start(self.id)
        self._update()

    def stop(self, timeout=10):
        self._client.stop(self.id, timeout)
        self._update()

    def restart(self, timeout=10):
        self.stop(timeout)
        self.start()
        self._update()

    def wait(self, timeout=None):
        res = self._client.wait(self.id, timeout)
        self._update()
        return res

    def top(self):
        return self._client.top(self.id)

    def stats(self):
        return self._client.stats(self.id, decode=True)

    def resize(self, height=None, width=None):
        self._client.resize(self.id, height, width)
        self._update()

    def rename(self, name):
        self._client.rename(self.id, name)
        self._update()

    def remove(self, volumes=False, link=False, force=False):
        self._client.remove_container(self.id, volumes, link, force)

    def port(self, private_port):
        return self._client.port(self.id, private_port)

    def logs(self, stdout=True, stderr=True, stream=True, timestamps=False,
             tail='all'):
        return self._client.logs(
            self.id, stdout, stderr, stream, timestamps, tail
        )

    @property
    def status(self):
        if self.state['Restarting']:
            return 'restarting'
        if self.state['Paused']:
            return 'paused'
        if self.state['Running']:
            return 'running'
        if self.state['OOMKilled']:
            return 'oom-killed'
        if self.state['Dead']:
            return 'dead'
        return 'stopped'

    def __str__(self):
        return '<DockerContainer(id={0})>'.format(self.id[:16])

    def __repr__(self):
        return str(self)
