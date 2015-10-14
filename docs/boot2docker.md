# Using with Boot2docker

For usage with boot2docker, there is a helper function in the utils package named `kwargs_from_env`, it will pass any environment variables from Boot2docker to the Client.

First run boot2docker in your shell:
```bash
$ eval "$(boot2docker shellinit)"
Writing /Users/you/.boot2docker/certs/boot2docker-vm/ca.pem
Writing /Users/you/.boot2docker/certs/boot2docker-vm/cert.pem
Writing /Users/you/.boot2docker/certs/boot2docker-vm/key.pem
```

You can then instantiate `docker.Client` like this:
```python
from docker.client import Client
from docker.utils import kwargs_from_env

cli = Client(**kwargs_from_env())
print cli.version()
```

If you're encountering the following error:
`SSLError: hostname '192.168.59.103' doesn't match 'boot2docker'`, you can:

1. Add an entry to your /etc/hosts file matching boot2docker to the daemon's IP
1. disable hostname validation (but please consider the security implications
   in doing this)

```python
from docker.client import Client
from docker.utils import kwargs_from_env

kwargs = kwargs_from_env()
kwargs['tls'].assert_hostname = False

cli = Client(**kwargs)
print cli.version()
```