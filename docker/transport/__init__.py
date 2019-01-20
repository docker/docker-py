# flake8: noqa
from .unixconn import UnixAdapter
from .ssladapter import SSLAdapter
try:
    from .npipeconn import NpipeAdapter
    from .npipesocket import NpipeSocket
except ImportError:
    pass

try:
    from .sshconn import SSHAdapter
except ImportError:
    pass
