Using TLS
=========

.. py:module:: docker.tls

Both the main :py:class:`~docker.client.DockerClient` and low-level
:py:class:`~docker.api.client.APIClient` can connect to the Docker daemon with TLS.

This is all configured automatically for you if you're using :py:func:`~docker.client.from_env`, but if you need some extra control it is possible to configure it manually by using a :py:class:`TLSConfig` object.

Examples
--------

For example, to check the server against a specific CA certificate:

.. code-block:: python

  tls_config = docker.tls.TLSConfig(ca_cert='/path/to/ca.pem', verify=True)
  client = docker.DockerClient(base_url='<https_url>', tls=tls_config)

This is the equivalent of ``docker --tlsverify --tlscacert /path/to/ca.pem ...``.

To authenticate with client certs:

.. code-block:: python

  tls_config = docker.tls.TLSConfig(
    client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem')
  )
  client = docker.DockerClient(base_url='<https_url>', tls=tls_config)

This is the equivalent of ``docker --tls --tlscert /path/to/client-cert.pem --tlskey /path/to/client-key.pem ...``.

Reference
---------

.. autoclass:: TLSConfig()
