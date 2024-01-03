import os
from unittest import mock

from docker.credentials.utils import create_environment_dict


@mock.patch.dict(os.environ)
def test_create_environment_dict():
    base = {'FOO': 'bar', 'BAZ': 'foobar'}
    os.environ = base  # noqa: B003
    assert create_environment_dict({'FOO': 'baz'}) == {
        'FOO': 'baz', 'BAZ': 'foobar',
    }
    assert create_environment_dict({'HELLO': 'world'}) == {
        'FOO': 'bar', 'BAZ': 'foobar', 'HELLO': 'world',
    }

    assert os.environ == base
