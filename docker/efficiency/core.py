from __future__ import absolute_import
from contextlib import contextmanager
from distutils.util import strtobool
from sys import stdout
from uuid import uuid4
import json
import platform

from characteristic import Attribute, attributes
from docker.client import Client
from docker.utils import kwargs_from_env

if platform.system() == "Darwin":
    CLIENT_DEFAULTS = kwargs_from_env(assert_hostname=False)
else:
    CLIENT_DEFAULTS = {}


class ImageBuildFailure(Exception):
    pass


@attributes(
    [
        Attribute(name="client"),
        Attribute(name="stdout", default_value=stdout),
    ],
)
class Docker(object):
    @contextmanager
    def temporary_image(self, **kwargs):
        kwargs.setdefault("forcerm", True)

        image_id = uuid4().hex
        for event_json in self.client.build(tag=image_id, rm=True, **kwargs):
            event = json.loads(event_json)

            error = event.get("errorDetail")
            if error is not None:
                raise ImageBuildFailure(error["message"])

            self.stdout.write(event["stream"])

        image = Image(id=image_id, client=self.client)
        yield image
        image.remove()



@attributes([Attribute(name="id"), Attribute(name="client")])
class Image(object):
    @contextmanager
    def temporary_container(self, **kwargs):
        container = Container.create(
            client=self.client, image=self.id, **kwargs
        )
        yield container
        container.remove()

    def remove(self):
        self.client.remove_image(self.id)


@attributes(
    [
        Attribute(name="id"),
        Attribute(name="client"),
        Attribute(name="volumes", default_value=()),
    ],
)
class Container(object):
    @classmethod
    def create(cls, client, volumes=(), **kwargs):
        response = client.create_container(**kwargs)
        return cls(id=response["Id"], client=client, volumes=volumes)

    def remove(self):
        self.client.stop(container=self.id)
        self.client.remove_container(self.id)

    def start(self, **kwargs):
        if "binds" in kwargs:
            raise TypeError(
                "Volumes should be specified as instances of Volume",
            )
        self.client.start(
            container=self.id,
            binds=dict(volume.to_bind() for volume in self.volumes),
            **kwargs
        )

    def logs(self, stream=True, **kwargs):
        return self.client.logs(container=self.id, stream=stream, **kwargs)


@attributes(
    [
        Attribute(name="bind"),
        Attribute(name="mount_point"),
        Attribute(name="read_only", default_value=False),
    ],
)
class Volume(object):
    def to_bind(self):
        return (
            self.bind.path, {"bind" : self.mount_point, "ro" : self.read_only}
        )


def client_from_opts(client_opts):
    """
    Construct a docker-py Client from a string specifying options.

    """

    kwargs = CLIENT_DEFAULTS.copy()

    for name, value in client_opts:
        if name == "timeout":
            kwargs["timeout"] = int(value)
        elif name == "tls":
            kwargs["tls"] = strtobool(value.lower())
        else:
            kwargs[name] = value

    return Client(**kwargs)
