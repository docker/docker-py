import asyncio
import binascii
import hashlib
import os

import base36
import grpclib.server

from docker.utils import version_gte
from docker.utils.config import config_dir

HEADER_SESSION_ID = "X-Docker-Expose-Session-Uuid"
HEADER_SESSION_NAME = "X-Docker-Expose-Session-Name"
HEADER_SESSION_SHAREDKEY = "X-Docker-Expose-Session-Sharedkey"
HEADER_SESSION_METHOD = "X-Docker-Expose-Session-Grpc-Method"


def is_session_supported(client, for_stream):
    if not for_stream and version_gte(client._version, '1.39'):
        return True

    servinfo = client.ping2()
    return servinfo['experimental'] and version_gte(client._version, '1.31')


def try_session(client, context_dir, for_stream):
    if is_session_supported(client, for_stream):
        shared_key = get_build_shared_key(context_dir)
        session = Session(context_dir, shared_key)

        return session
    return None


def get_build_shared_key(folder):
    k = '{}:{}'.format(node_identifier(), folder)
    h = hashlib.sha256()
    h.update(k)
    return h.hexdigest()


def node_identifier():
    cfgdir = config_dir()
    session_file = os.path.join(cfgdir, '.buildNodeID')
    try:
        if not os.path.isfile(session_file):
            with open(session_file, 'w') as sess_fp:
                b = os.urandom(32)
                sess_fp.write(binascii.hexlify(b).decode('ascii'))

        with open(session_file, 'r') as sess_fp:
            return sess_fp.read()
    except OSError:
        pass

    return cfgdir


def generate_session_id():
    b = os.urandom(17)
    b[0] |= 0x80
    return base36.dumps(int.from_bytes(b, 'big'))[:25]


class Session(object):
    def __init__(self, name, shared_key):
        self.id = generate_session_id()
        self.name = name
        self.shared_key = shared_key
        self.grpc_server = grpclib.server.Server(
            [], asyncio.get_event_loop()
        )
        self.sock = None

    def allow(self, attachable):
        attachable.register(self.grpc_server)

    def run(self, sock):
        meta = {
            HEADER_SESSION_ID: self.id,
            HEADER_SESSION_NAME: self.name,
            HEADER_SESSION_SHAREDKEY: self.shared_key,
        }

        # FIXME: some loop for headerSessionMethod

        self.sock = sock

        await self.serve(meta)

    async def serve(self, metadata):
        # FIXME: Figure out what to do with metadata
        await self.grpc_server.start(sock=self.sock)
        print('Serving on socket {}'.format(self.sock))
        try:
            await self.grpc_server.wait_closed()
        except asyncio.CancelledError:
            self.grpc_server.close()
            await self.grpc_server.wait_closed()

    def close(self):
        if self.sock:
            self.sock.close()
        self.grpc_server.close()
        self.closed = True
