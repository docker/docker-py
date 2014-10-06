Connection to daemon using HTTPS
================================

**These instructions are docker-py specific.**
Please refer to `the docs`_ first.

.. _the docs: http://docs.docker.com/articles/https/

Authenticate server based on public/default CA pool
---------------------------------------------------

.. code-block:: python

    client = docker.Client(base_url='<https_url>', tls=True)

Equivalent CLI options:
``docker --tls ...``

If you want to use TLS but don't want to verify the server certificate
(for example when testing with a self-signed certificate):

.. code-block:: python

    tls_config = docker.tls.TLSConfig(verify=False)
    client = docker.Client(base_url='<https_url>', tls=tls_config)


Authenticate server based on given CA
-------------------------------------

.. code-block:: python

    tls_config = docker.tls.TLSConfig(ca_cert='/path/to/ca.pem')
    client = docker.Client(base_url='<https_url>', tls=tls_config)


Equivalent CLI options:
``docker --tlsverify --tlscacert /path/to/ca.pem ...``

Authenticate with client certificate not based on a CA
------------------------------------------------------

.. code-block:: python

    tls_config = docker.tls.TLSConfig(
      client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem')
    )
    client = docker.Client(base_url='<https_url>', tls=tls_config)


Equivalent CLI options:
``docker --tls --tlscert /path/to/client-cert.pem --tlskey /path/to/client-key.pem ...``

Authenticate with client certificate based on a CA
--------------------------------------------------

.. code-block:: python

    tls_config = docker.tls.TLSConfig(
      client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem'),
      ca_cert='/path/to/ca.pem'
    )
    client = docker.Client(base_url='<https_url>', tls=tls_config)


Equivalent CLI options:
``docker --tlsverify --tlscert /path/to/client-cert.pem
--tlskey /path/to/client-key.pem --tlscacert /path/to/ca.pem ...``
