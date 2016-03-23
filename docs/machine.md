# Using with Docker Toolbox and Machine

In development, Docker recommends using
[Docker Toolbox](https://www.docker.com/products/docker-toolbox) to set up
Docker. It includes a tool called Machine which will create a VM running
Docker Engine and point your shell at it using environment variables.

To configure docker-py with these environment variables

First use Machine to set up the environment variables:
```bash
$ eval "$(docker-machine env)"
```

You can then use docker-py like this:
```python
import docker
client = docker.from_env(assert_hostname=False)
print client.version()
```

**Note:** This snippet is disabling TLS hostname checking with
`assert\_hostname=False`. Machine provides us with the exact certificate
the server is using so this is safe. If you are not using Machine and verifying
the host against a certificate authority, you'll want to enable hostname
verification.
