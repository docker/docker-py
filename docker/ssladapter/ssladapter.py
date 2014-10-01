""" Resolves OpenSSL issues in some servers:
      https://lukasa.co.uk/2013/01/Choosing_SSL_Version_In_Requests/
      https://github.com/kennethreitz/requests/pull/799
"""
from distutils.version import StrictVersion
from requests.adapters import HTTPAdapter
try:
    import requests.packages.urllib3 as urllib3
except ImportError:
    import urllib3


PoolManager = urllib3.poolmanager.PoolManager


class SSLAdapter(HTTPAdapter):
    '''An HTTPS Transport Adapter that uses an arbitrary SSL version.'''
    def __init__(self, ssl_version=None, **kwargs):
        self.ssl_version = ssl_version
        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        urllib_ver = urllib3.__version__.split('-')[0]
        kwargs = {
            'num_pools': connections,
            'maxsize': maxsize,
            'block': block
        }
        if urllib3 and urllib_ver != 'dev' and \
           StrictVersion(urllib_ver) > StrictVersion('1.5'):
            kwargs['ssl_version'] = self.ssl_version

        self.poolmanager = PoolManager(**kwargs)
