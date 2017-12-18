import unittest

import requests

from docker.errors import (APIError, ContainerError, DockerException,
                           create_unexpected_kwargs_error,
                           create_api_error_from_http_exception)
from .fake_api import FAKE_CONTAINER_ID, FAKE_IMAGE_ID
from .fake_api_client import make_fake_client


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

    def test_create_error_from_exception(self):
            resp = requests.Response()
            resp.status_code = 500
            err = APIError('')
            try:
                resp.raise_for_status()
            except requests.exceptions.HTTPError as e:
                try:
                    create_api_error_from_http_exception(e)
                except APIError as e:
                    err = e
            assert err.is_server_error() is True


class ContainerErrorTest(unittest.TestCase):
    def test_container_without_stderr(self):
        """The massage does not contain stderr"""
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        command = "echo Hello World"
        exit_status = 42
        image = FAKE_IMAGE_ID
        stderr = None

        err = ContainerError(container, exit_status, command, image, stderr)
        msg = ("Command '{}' in image '{}' returned non-zero exit status {}"
               ).format(command, image, exit_status, stderr)
        assert str(err) == msg

    def test_container_with_stderr(self):
        """The massage contains stderr"""
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        command = "echo Hello World"
        exit_status = 42
        image = FAKE_IMAGE_ID
        stderr = "Something went wrong"

        err = ContainerError(container, exit_status, command, image, stderr)
        msg = ("Command '{}' in image '{}' returned non-zero exit status {}: "
               "{}").format(command, image, exit_status, stderr)
        assert str(err) == msg


class CreateUnexpectedKwargsErrorTest(unittest.TestCase):
    def test_create_unexpected_kwargs_error_single(self):
        e = create_unexpected_kwargs_error('f', {'foo': 'bar'})
        assert str(e) == "f() got an unexpected keyword argument 'foo'"

    def test_create_unexpected_kwargs_error_multiple(self):
        e = create_unexpected_kwargs_error('f', {'foo': 'bar', 'baz': 'bosh'})
        assert str(e) == "f() got unexpected keyword arguments 'baz', 'foo'"
