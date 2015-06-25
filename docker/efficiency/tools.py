import json

from .. import errors


def generator_parser(gen):
    for line in gen:
        status = json.loads(line)
        if status.get('error'):
            raise errors.DockerException(status.get('error'))
        yield status
