""" Resolves OpenSSL issues in some servers:
      https://lukasa.co.uk/2013/01/Choosing_SSL_Version_In_Requests/
      https://github.com/kennethreitz/requests/pull/799
"""
from distutils.version import StrictVersion
from requests.adapters import HTTPAdapter
import ssl

try:
    import requests.packages.urllib3 as urllib3
except ImportError:
    import urllib3

PoolManager = urllib3.poolmanager.PoolManager


def get_max_tls_protocol():
    protocols = ('PROTOCOL_TLSv1_2',
                 'PROTOCOL_TLSv1_1',
                 'PROTOCOL_TLSv1')
    for proto in protocols:
        if hasattr(ssl, proto):
            return getattr(ssl, proto)


class SSLAdapter(HTTPAdapter):
    '''An HTTPS Transport Adapter that uses an arbitrary SSL version.'''
    def __init__(self, ssl_version=None, assert_hostname=None,
                 assert_fingerprint=None, **kwargs):
        ssl_version = ssl_version or get_max_tls_protocol()
        self.ssl_version = ssl_version
        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint
        super(SSLAdapter, self).__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        kwargs = {
            'num_pools': connections,
            'maxsize': maxsize,
            'block': block,
            'assert_hostname': self.assert_hostname,
            'assert_fingerprint': self.assert_fingerprint,
        }
        if self.can_override_ssl_version():
            kwargs['ssl_version'] = self.ssl_version

        self.poolmanager = PoolManager(**kwargs)

    def get_connection(self, *args, **kwargs):
        """
        Ensure assert_hostname is set correctly on our pool

        We already take care of a normal poolmanager via init_poolmanager

        But we still need to take care of when there is a proxy poolmanager
        """
        conn = super(SSLAdapter, self).get_connection(*args, **kwargs)
        if conn.assert_hostname != self.assert_hostname:
            conn.assert_hostname = self.assert_hostname
        return conn

    def can_override_ssl_version(self):
        urllib_ver = urllib3.__version__.split('-')[0]
        if urllib_ver is None:
            return False
        if urllib_ver == 'dev':
            return True
        return StrictVersion(urllib_ver) > StrictVersion('1.5')
