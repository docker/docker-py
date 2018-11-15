from .auth_pb2 import CredentialsResponse
from .auth_grpc import AuthBase
from ..grpc import Attachable
from docker.auth import resolve_authconfig


class Auth(AuthBase, Attachable):
    def __init__(self, authconfig, credstore_env, *args, **kwargs):
        self.authconfig = authconfig
        self.credstore_env = credstore_env
        super(Auth, self).__init__(*args, **kwargs)

    async def Credentials(self, stream):
        request = await stream.recv_message()
        host = request.Host
        auth_data = resolve_authconfig(
            self.authconfig, host, self.credstore_env
        )
        response = None
        if auth_data is None:
            response = CredentialsResponse(Username=None, Secret=None)
        else:
            response = CredentialsResponse(
                Username=auth_data['Username'], Secret=auth_data['Password']
            )
        await stream.send_message(response)
