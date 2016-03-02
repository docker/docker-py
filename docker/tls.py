import os
import ssl

from . import errors
from .ssladapter import ssladapter


class TLSConfig(object):
    cert = None
    ca_cert = None
    verify = None
    ssl_version = None

    def __init__(self, client_cert=None, ca_cert=None, verify=None,
                 ssl_version=None, assert_hostname=None,
                 assert_fingerprint=None):
        # Argument compatibility/mapping with
        # https://docs.docker.com/engine/articles/https/
        # This diverges from the Docker CLI in that users can specify 'tls'
        # here, but also disable any public/default CA pool verification by
        # leaving tls_verify=False

        self.assert_hostname = assert_hostname
        self.assert_fingerprint = assert_fingerprint

        # TLS v1.0 seems to be the safest default; SSLv23 fails in mysterious
        # ways: https://github.com/docker/docker-py/issues/963

        self.ssl_version = ssl_version or ssl.PROTOCOL_TLSv1

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

        # If verify is set, make sure the cert exists
        self.verify = verify
        self.ca_cert = ca_cert
        if self.verify and self.ca_cert and not os.path.isfile(self.ca_cert):
            raise errors.TLSParameterError(
                'Invalid CA certificate provided for `tls_ca_cert`.'
            )

    def configure_client(self, client):
        client.ssl_version = self.ssl_version

        if self.verify and self.ca_cert:
            client.verify = self.ca_cert
        else:
            client.verify = self.verify

        if self.cert:
            client.cert = self.cert

        client.mount('https://', ssladapter.SSLAdapter(
            ssl_version=self.ssl_version,
            assert_hostname=self.assert_hostname,
            assert_fingerprint=self.assert_fingerprint,
        ))
