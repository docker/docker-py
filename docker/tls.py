import os

from . import errors
from .ssladapter import ssladapter


class TLSConfig(object):
    cert = None
    verify = None
    ssl_version = None

    def __init__(self, client_cert=None, ca_cert=None, verify=None,
                 ssl_version=None, assert_hostname=None):
        # Argument compatibility/mapping with
        # http://docs.docker.com/examples/https/
        # This diverges from the Docker CLI in that users can specify 'tls'
        # here, but also disable any public/default CA pool verification by
        # leaving tls_verify=False

        # urllib3 sets a default ssl_version if ssl_version is None
        # http://tinyurl.com/kxga8hb
        self.ssl_version = ssl_version
        self.assert_hostname = assert_hostname

        # "tls" and "tls_verify" must have both or neither cert/key files
        # In either case, Alert the user when both are expected, but any are
        # missing.

        if client_cert:
            try:
                tls_cert, tls_key = client_cert
            except ValueError:
                raise errors.TLSParameterError(
                    'client_config must be a tuple of'
                    ' (client certificate, key file)'
                )

            if not (tls_cert and tls_key) or (not os.path.isfile(tls_cert) or
               not os.path.isfile(tls_key)):
                raise errors.TLSParameterError(
                    'Path to a certificate and key files must be provided'
                    ' through the client_config param'
                )
            self.cert = (tls_cert, tls_key)

        # Either set verify to True (public/default CA checks) or to the
        # path of a CA Cert file.
        if verify is not None:
            if not ca_cert:
                self.verify = verify
            elif os.path.isfile(ca_cert):
                if not verify:
                    raise errors.TLSParameterError(
                        'verify can not be False when a CA cert is'
                        ' provided.'
                    )
                self.verify = ca_cert
            else:
                raise errors.TLSParameterError(
                    'Invalid CA certificate provided for `tls_ca_cert`.'
                )

    def configure_client(self, client):
        client.ssl_version = self.ssl_version
        if self.verify is not None:
            client.verify = self.verify
        if self.cert:
            client.cert = self.cert
        client.mount('https://', ssladapter.SSLAdapter(
            ssl_version=self.ssl_version,
            assert_hostname=self.assert_hostname,
        ))
