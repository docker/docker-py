import unittest

import requests

from docker.errors import (APIError, DockerException,
                           create_unexpected_kwargs_error)


class APIErrorTest(unittest.TestCase):
    def test_api_error_is_caught_by_dockerexception(self):
        try:
            raise APIError("this should be caught by DockerException")
        except DockerException:
            pass

    def test_status_code_200(self):
        """The status_code property is present with 200 response."""
        resp = requests.Response()
        resp.status_code = 200
        err = APIError('', response=resp)
        assert err.status_code == 200

    def test_status_code_400(self):
        """The status_code property is present with 400 response."""
        resp = requests.Response()
        resp.status_code = 400
        err = APIError('', response=resp)
        assert err.status_code == 400

    def test_status_code_500(self):
        """The status_code property is present with 500 response."""
        resp = requests.Response()
        resp.status_code = 500
        err = APIError('', response=resp)
        assert err.status_code == 500

    def test_is_server_error_200(self):
        """Report not server error on 200 response."""
        resp = requests.Response()
        resp.status_code = 200
        err = APIError('', response=resp)
        assert err.is_server_error() is False

    def test_is_server_error_300(self):
        """Report not server error on 300 response."""
        resp = requests.Response()
        resp.status_code = 300
        err = APIError('', response=resp)
        assert err.is_server_error() is False

    def test_is_server_error_400(self):
        """Report not server error on 400 response."""
        resp = requests.Response()
        resp.status_code = 400
        err = APIError('', response=resp)
        assert err.is_server_error() is False

    def test_is_server_error_500(self):
        """Report server error on 500 response."""
        resp = requests.Response()
        resp.status_code = 500
        err = APIError('', response=resp)
        assert err.is_server_error() is True

    def test_is_client_error_500(self):
        """Report not client error on 500 response."""
        resp = requests.Response()
        resp.status_code = 500
        err = APIError('', response=resp)
        assert err.is_client_error() is False

    def test_is_client_error_400(self):
        """Report client error on 400 response."""
        resp = requests.Response()
        resp.status_code = 400
        err = APIError('', response=resp)
        assert err.is_client_error() is True


class CreateUnexpectedKwargsErrorTest(unittest.TestCase):
    def test_create_unexpected_kwargs_error_single(self):
        e = create_unexpected_kwargs_error('f', {'foo': 'bar'})
        assert str(e) == "f() got an unexpected keyword argument 'foo'"

    def test_create_unexpected_kwargs_error_multiple(self):
        e = create_unexpected_kwargs_error('f', {'foo': 'bar', 'baz': 'bosh'})
        assert str(e) == "f() got unexpected keyword arguments 'baz', 'foo'"
