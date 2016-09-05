import requests


class APIError(requests.exceptions.HTTPError):
    def __init__(self, message, response, explanation=None):
        # requests 1.2 supports response as a keyword argument, but
        # requests 1.1 doesn't
        super(APIError, self).__init__(message)
        self.response = response

        self.explanation = explanation

        if self.explanation is None and response.content:
            self.explanation = response.content.strip()

    def __str__(self):
        message = super(APIError, self).__str__()

        if self.is_client_error():
            message = '{0} Client Error: {1}'.format(
                self.response.status_code, self.response.reason)

        elif self.is_server_error():
            message = '{0} Server Error: {1}'.format(
                self.response.status_code, self.response.reason)

        if self.explanation:
            message = '{0} ("{1}")'.format(message, self.explanation)

        return message

    def is_client_error(self):
        return 400 <= self.response.status_code < 500

    def is_server_error(self):
        return 500 <= self.response.status_code < 600


class DockerException(Exception):
    pass


class NotFound(APIError):
    pass


class InvalidVersion(DockerException):
    pass


class InvalidRepository(DockerException):
    pass


class InvalidConfigFile(DockerException):
    pass


class DeprecatedMethod(DockerException):
    pass


class TLSParameterError(DockerException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg + (". TLS configurations should map the Docker CLI "
                           "client configurations. See "
                           "https://docs.docker.com/engine/articles/https/ "
                           "for API details.")


class NullResource(DockerException, ValueError):
    pass
