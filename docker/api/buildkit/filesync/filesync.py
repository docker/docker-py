from .filesync_pb2 import BytesMessage
from .filesync_grpc import FileSendBase, FileSyncBase
from ..grpc import Attachable


class FileSync(FileSyncBase, Attachable):
    def __init__(self, *args, **kwargs):
        super(FileSync, self).__init__(*args, **kwargs)

    async def DiffCopy(self, stream):
        pass

    async def TarStream(self, stream):
        pass


class FileSend(FileSendBase, Attachable):
    def __init__(self, *args, **kwargs):
        super(FileSync, self).__init__(*args, **kwargs)

    async def DiffCopy(self, stream):
        pass
