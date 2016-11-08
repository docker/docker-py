import unittest

from docker.errors import (APIError, DockerException,
                           create_unexpected_kwargs_error)


class APIErrorTest(unittest.TestCase):
    def test_api_error_is_caught_by_dockerexception(self):
        try:
            raise APIError("this should be caught by DockerException")
        except DockerException:
            pass


class CreateUnexpectedKwargsErrorTest(unittest.TestCase):
    def test_create_unexpected_kwargs_error_single(self):
        e = create_unexpected_kwargs_error('f', {'foo': 'bar'})
        assert str(e) == "f() got an unexpected keyword argument 'foo'"

    def test_create_unexpected_kwargs_error_multiple(self):
        e = create_unexpected_kwargs_error('f', {'foo': 'bar', 'baz': 'bosh'})
        assert str(e) == "f() got unexpected keyword arguments 'baz', 'foo'"
