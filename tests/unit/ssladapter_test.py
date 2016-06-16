from docker.ssladapter import ssladapter

try:
    from backports.ssl_match_hostname import (
        match_hostname, CertificateError
    )
except ImportError:
    from ssl import (
        match_hostname, CertificateError
    )

try:
    from ssl import OP_NO_SSLv3, OP_NO_SSLv2, OP_NO_TLSv1
except ImportError:
    OP_NO_SSLv2 = 0x1000000
    OP_NO_SSLv3 = 0x2000000
    OP_NO_TLSv1 = 0x4000000

from .. import base


class SSLAdapterTest(base.BaseTestCase):
    def test_only_uses_tls(self):
        ssl_context = ssladapter.urllib3.util.ssl_.create_urllib3_context()

        assert ssl_context.options & OP_NO_SSLv3
        assert ssl_context.options & OP_NO_SSLv2
        assert not ssl_context.options & OP_NO_TLSv1


class MatchHostnameTest(base.BaseTestCase):
    cert = {
        'issuer': (
            (('countryName', u'US'),),
            (('stateOrProvinceName', u'California'),),
            (('localityName', u'San Francisco'),),
            (('organizationName', u'Docker Inc'),),
            (('organizationalUnitName', u'Docker-Python'),),
            (('commonName', u'localhost'),),
            (('emailAddress', u'info@docker.com'),)
        ),
        'notAfter': 'Mar 25 23:08:23 2030 GMT',
        'notBefore': u'Mar 25 23:08:23 2016 GMT',
        'serialNumber': u'BD5F894C839C548F',
        'subject': (
            (('countryName', u'US'),),
            (('stateOrProvinceName', u'California'),),
            (('localityName', u'San Francisco'),),
            (('organizationName', u'Docker Inc'),),
            (('organizationalUnitName', u'Docker-Python'),),
            (('commonName', u'localhost'),),
            (('emailAddress', u'info@docker.com'),)
        ),
        'subjectAltName': (
            ('DNS', u'localhost'),
            ('DNS', u'*.gensokyo.jp'),
            ('IP Address', u'127.0.0.1'),
        ),
        'version': 3
    }

    def test_match_ip_address_success(self):
        assert match_hostname(self.cert, '127.0.0.1') is None

    def test_match_localhost_success(self):
        assert match_hostname(self.cert, 'localhost') is None

    def test_match_dns_success(self):
        assert match_hostname(self.cert, 'touhou.gensokyo.jp') is None

    def test_match_ip_address_failure(self):
        self.assertRaises(
            CertificateError, match_hostname, self.cert, '192.168.0.25'
        )

    def test_match_dns_failure(self):
        self.assertRaises(
            CertificateError, match_hostname, self.cert, 'foobar.co.uk'
        )
