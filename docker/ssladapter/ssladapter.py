""" Resolves OpenSSL issues in some servers:
      https://lukasa.co.uk/2013/01/Choosing_SSL_Version_In_Requests/
      https://github.com/kennethreitz/requests/pull/799
"""
from distutils.version import StrictVersion
from requests.adapters import HTTPAdapter
try:
    from requests.packages.urllib3.poolmanager import PoolManager
except ImportError:
    import urllib3
    from urllib3.poolmanager import PoolManager


class SSLAdapter(HTTPAdapter):
    '''An HTTPS Transport Adapter that uses an arbitrary SSL version.'''
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        try:
            urllib_ver = urllib3.__version__
        except NameError:
            urllib_ver = urllib3 = None

        if urllib3 and StrictVersion(urllib_ver) <= StrictVersion('1.5'):
            self.poolmanager = PoolManager(num_pools=connections,
                                           maxsize=maxsize,
                                           block=block)
        else:
            self.poolmanager = PoolManager(num_pools=connections,
                                           maxsize=maxsize,
                                           block=block,
                                           ssl_version=self.ssl_version)
