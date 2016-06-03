# flake8: noqa
from .unixconn import UnixAdapter
try:
    from .npipeconn import NpipeAdapter
except ImportError:
    pass