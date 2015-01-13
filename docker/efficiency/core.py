from contextlib import contextmanager
from sys import stdout
from uuid import uuid4
import json

from characteristic import Attribute, attributes


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

        yield image_id

        self.client.remove_image(image_id)

    @contextmanager
    def temporary_container(self, **kwargs):
        container = self.client.create_container(**kwargs)
        container_id = container["Id"]
        yield container_id
        self.client.stop(container=container_id)
        self.client.remove_container(container_id)
