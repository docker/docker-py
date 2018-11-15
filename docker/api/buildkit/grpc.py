import grpclib.server


class Handler(grpclib.server.Handler):
    def __init__(self, headers, *args, **kwargs):
        self.headers = headers
        super(Handler, self).__init__(*args, **kwargs)

    def accept(self, stream, headers, release_stream):
        for k, v in self.headers.items():
            headers.setdefault(k, v)


class Server(grpclib.server.Server):
    headers = {}

    def add_headers(self, h):
        self.headers.update(h)

    def _protocol_factory(self):
        self.__gc_step__()
        handler = Handler(
            self.headers, self._mapping, self._codec, loop=self._loop
        )
        self._handlers.add(handler)
        return grpclib.server.H2Protocol(
            handler, self._config, loop=self._loop
        )


class Attachable(object):
    def register(self, grpc_server):
        grpc_server._mapping.update(self.__mapping__())
