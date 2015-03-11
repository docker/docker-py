## Connection to daemon using HTTPS

**Note:** *These instructions are docker-py specific. Please refer to
[http://docs.docker.com/articles/https/](http://docs.docker.com/articles/https/)
first.*

## TLSConfig

**Params**:

* client_cert (tuple of str): Path to client cert, path to client key
* ca_cert (str): Path to CA cert file
* verify (bool or str): This can be `False` or a path to a CA Cert file
* ssl_version (int): A valid [SSL version](
https://docs.python.org/3.4/library/ssl.html#ssl.PROTOCOL_TLSv1)
* assert_hostname (bool): Verify hostname of docker daemon

### configure_client

**Params**:

* client: ([Client](api.md#client-api)): A client to apply this config to


## Authenticate server based on public/default CA pool

```python
client = docker.Client(base_url='<https_url>', tls=True)
```

Equivalent CLI options:
```bash
docker --tls ...
```

If you want to use TLS but don't want to verify the server certificate
(for example when testing with a self-signed certificate):

```python
tls_config = docker.tls.TLSConfig(verify=False)
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

## Authenticate server based on given CA

```python
tls_config = docker.tls.TLSConfig(ca_cert='/path/to/ca.pem')
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

Equivalent CLI options:
```bash
docker --tlsverify --tlscacert /path/to/ca.pem ...
```

## Authenticate with client certificate, do not authenticate server based on given CA

```python
tls_config = docker.tls.TLSConfig(
  client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem')
)
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

Equivalent CLI options:
```bash
docker --tls --tlscert /path/to/client-cert.pem --tlskey /path/to/client-key.pem ...
```

## Authenticate with client certificate, authenticate server based on given CA

```python
tls_config = docker.tls.TLSConfig(
  client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem'),
  verify='/path/to/ca.pem'
)
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

Equivalent CLI options:
```bash
docker --tlsverify \
	--tlscert /path/to/client-cert.pem \
   --tlskey /path/to/client-key.pem \
   --tlscacert /path/to/ca.pem ...
```
