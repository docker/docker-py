# flake8: noqa
from .unixconn import UnixAdapter
try:
    from .npipeconn import NpipeAdapter
    from .npipesocket import NpipeSocket
except ImportError:
    pass