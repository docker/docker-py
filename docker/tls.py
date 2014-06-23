import os

from . import errors
from .ssladapter import ssladapter


class TLSConfig(object):
    def __init__(self, tls, tls_cert=None, tls_key=None, tls_verify=False,
                 tls_ca_cert=None, ssl_version=None):
        # Argument compatibility/mapping with
        # http://docs.docker.com/examples/https/
        # This diverges from the Docker CLI in that users can specify 'tls'
        # here, but also disable any public/default CA pool verification by
        # leaving tls_verify=False

        # urllib3 sets a default ssl_version if ssl_version is None
        # http://tinyurl.com/kxga8hb
        self.ssl_version = ssl_version

        # "tls" and "tls_verify" must have both or neither cert/key files
        # In either case, Alert the user when both are expected, but any are
        # missing.

        if tls_cert or tls_key:
            if not (tls_cert and tls_key) or (not os.path.isfile(tls_cert) or
               not os.path.isfile(tls_key)):
                raise errors.TLSParameterError(
                    'You must provide either both "tls_cert"/"tls_key" files, '
                    'or neither, in order to use TLS.')
            self.cert = (tls_cert, tls_key)

        # Either set tls_verify to True (public/default CA checks) or to the
        # path of a CA Cert file.
        if tls_verify:
            if not tls_ca_cert:
                self.verify = True
            elif os.path.isfile(tls_ca_cert):
                self.verify = tls_ca_cert
            else:
                raise errors.TLSParameterError(
                    'If "tls_verify" is set, then "tls_ca_cert" must be blank'
                    ' (to check public CA list) OR a path to a Cert File.'
                )
        else:
            self.verify = False

    def configure_client(self, client):
        client.verify = self.verify
        client.ssl_version = self.ssl_version
        client.cert = self.cert
        self.mount('https://', ssladapter.SSLAdapter(self.ssl_version))
