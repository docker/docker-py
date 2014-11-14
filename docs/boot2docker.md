# With boot2docker

For usage with boot2docker, there is a helper function in docker.utils named `kwargs_from_env`; it will pass relevant environment variables set by boot2docker to the Client. Starting with boot2docker 1.3.0, this includes settings for TLS authentication.

First run `boot2docker shellinit` in your shell:
```bash
$ $(boot2docker shellinit)
Writing /Users/you/.boot2docker/certs/boot2docker-vm/ca.pem
Writing /Users/you/.boot2docker/certs/boot2docker-vm/cert.pem
Writing /Users/you/.boot2docker/certs/boot2docker-vm/key.pem
export DOCKER_HOST=tcp://192.168.59.103:2376
export DOCKER_CERT_PATH=/Users/you/.boot2docker/certs/boot2docker-vm
export DOCKER_TLS_VERIFY=1
```

and then, in your python script:
```python
from docker.client import Client
from docker.utils import kwargs_from_env
client = Client(**kwargs_from_env())
print client.version()
```