import os

from docker.credentials.utils import create_environment_dict
from unittest import mock


@mock.patch.dict(os.environ)
def test_create_environment_dict():
    base = {'FOO': 'bar', 'BAZ': 'foobar'}
    os.environ = base
    assert create_environment_dict({'FOO': 'baz'}) == {
        'FOO': 'baz', 'BAZ': 'foobar',
    }
    assert create_environment_dict({'HELLO': 'world'}) == {
        'FOO': 'bar', 'BAZ': 'foobar', 'HELLO': 'world',
    }

    assert os.environ == base
