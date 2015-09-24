import json
import re

from .. import errors


first_cap_re = re.compile('(.)([A-Z][a-z]+)')
all_cap_re = re.compile('([a-z0-9])([A-Z])')


def to_snakecase(name):
    s1 = first_cap_re.sub(r'\1_\2', name)
    return all_cap_re.sub(r'\1_\2', s1).lower()


def generator_parser(gen):
    for line in gen:
        status = json.loads(line)
        if status.get('error'):
            raise errors.DockerException(status.get('error'))
        yield status


class Identifiable(object):
    def __init__(self, id):
        self._id = id

    @property
    def id(self):
        return self._id


class Interactive(Identifiable):
    def __init__(self, client, id):
        super(Interactive, self).__init__(id)
        self._client = client
