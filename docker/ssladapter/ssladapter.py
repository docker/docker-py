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
    def __init__(self, ssl_version=None, assert_hostname=None, **kwargs):
        self.ssl_version = ssl_version
        self.assert_hostname = assert_hostname
        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        kwargs = {
            'num_pools': connections,
            'maxsize': maxsize,
            'block': block,
            'assert_hostname': self.assert_hostname,
        }
        if self.can_override_ssl_version():
            kwargs['ssl_version'] = self.ssl_version

        self.poolmanager = PoolManager(**kwargs)

    def can_override_ssl_version(self):
        urllib_ver = urllib3.__version__.split('-')[0]
        if urllib_ver is None:
            return False
        if urllib_ver == 'dev':
            return True
        return StrictVersion(urllib_ver) > StrictVersion('1.5')
