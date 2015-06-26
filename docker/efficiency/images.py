import six

from . import commons


def pull(client, repo, tag=None, insecure_registry=False, auth_config=None):
    """
    Pull an image and stream the response chunks as JSON objects.
    If an error is encountered during streaming, a DockerException will be
    raised.

    **Params:**
        client: a docker `Client` object
        repo: Name of the repository to pull
        tag:  Optional tag name to pull (default: latest)
        insecure_registry: Set to true if pulling from an insecure registry
        auth_config: Optional transient auth config object
    """
    gen = client.pull(
        repo, tag=tag, stream=True, insecure_registry=insecure_registry,
        auth_config=auth_config
    )

    return commons.generator_parser(gen)


def push(client, repo, tag=None, insecure_registry=False):
    """
    Push an image and stream the response chunks as JSON objects.
    If an error is encountered during streaming, a DockerException will be
    raised.

    **Params:**
        client: a docker `Client` object
        repo: Name of the repository to push
        tag:  Optional tag name to push (default: all)
        insecure_registry: Set to true if pulling from an insecure registry
        auth_config: Optional transient auth config object
    """
    gen = client.push(
        repo, tag=tag, stream=True, insecure_registry=insecure_registry
    )
    return commons.generator_parser(gen)


class Image(commons.Interactive):

    @classmethod
    def list(cls, name=None, all=False, filters=None):
        from . import efficiency
        lst = efficiency._client.images(name, True, all, False, filters)
        return [cls(efficiency._client, x) for x in lst]

    def __init__(self, *args, **kwargs):
        super(Image, self).__init__(*args, **kwargs)
        data = self._client.inspect_image(self.id)
        for k, v in six.iteritems(data):
            if k == 'Id':
                self._id = v
                continue
            setattr(self, commons.to_snakecase(k), v)

    def remove(self, force=False):
        self._client.remove_image(self.id, force)

    def tag(self, repository, tag=None, force=False):
        return self._client.tag(self.id, repository, tag, force)

    def history(self):
        hist = self._client.history(self.id)
        return [Image(self._client, img['Id']) for img in hist]

    def create_container(self, *args, **kwargs):
        from . import containers
        return containers.Container(
            self._client,
            self._client.create_container(self.id, *args, **kwargs).get('Id')
        )

    def __str__(self):
        return '<DockerImage(id={0})>'.format(self.id[:16])

    def __repr__(self):
        return str(self)
