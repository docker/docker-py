docker-py
=========

[![Build Status](https://travis-ci.org/docker/docker-py.png)](https://travis-ci.org/docker/docker-py)

An API client for docker written in Python

Installation
============

Our latest stable is always available on PyPi.

    pip install docker-py

API
===

To instantiate a `Client` class that will allow you to communicate with
a Docker daemon, simply do:

```python
c = docker.Client(base_url='unix://var/run/docker.sock',
                  version='1.12',
                  timeout=10)
```

`base_url` refers to the protocol+hostname+port where the docker server
is hosted. `version` is the version of the API the client will use and
`timeout` specifies the HTTP request timeout, in seconds.

```python
c.build(path=None, tag=None, quiet=False, fileobj=None, nocache=False,
        rm=False, stream=False, timeout=None,
        custom_context=False, encoding=None):
```

Similar to the `docker build` command. Either `path` or `fileobj` needs
to be set. `path` can be a local path (to a directory containing a
Dockerfile) or a remote URL. `fileobj` must be a readable file-like
object to a Dockerfile.

If you have a tar file for the docker build context (including a dockerfile)
already, pass a readable file-like object to `fileobj` and also pass
`custom_context=True`. If the stream is compressed also, set `encoding` to
the correct value (e.g `gzip`).

```python
c.commit(container, repository=None, tag=None, message=None, author=None,
         conf=None)
```

Identical to the `docker commit` command.

```python
c.containers(quiet=False, all=False, trunc=True, latest=False, since=None,
             before=None, limit=-1)
```

Identical to the `docker ps` command.

```python
c.copy(container, resource)
```

Identical to the `docker cp` command.

```python
c.create_container(image, command=None, hostname=None, user=None,
                   detach=False, stdin_open=False, tty=False, mem_limit=0,
                   ports=None, environment=None, dns=None, volumes=None,
                   volumes_from=None, network_disabled=False, name=None,
                   entrypoint=None, cpu_shares=None, working_dir=None,
                   memswap_limit=0)
```

Creates a container that can then be `start`ed. Parameters are similar
to those for the `docker run` command except it doesn't support the
attach options (`-a`). See "Port bindings" and "Using volumes" below for
more information on how to create port bindings and volume mappings.

`command` is the command to be run in the container. String or list types are
accepted.

The `environment` variable accepts a dictionary or a list of strings
in the following format `["PASSWORD=xxx"]` or `{"PASSWORD": "xxx"}`.

The `mem_limit` variable accepts float values (which represent the memory limit
of the created container in bytes) or a string with a units identification char
('100000b', 1000k', 128m', '1g'). If a string is specified without a units
character, bytes are assumed as an intended unit.

`volumes_from` and `dns` arguments raise TypeError exception if they are used
against v1.10 of docker remote API. Those arguments should be passed to
`start()` instead.


```python
c.diff(container)
```

Identical to the `docker diff` command.

```python
c.export(container)
```

Identical to the `docker export` command.

```python
c.history(image)
```

Identical to the `docker history` command.

```python
c.images(name=None, quiet=False, all=False, viz=False)
```

Identical to the `docker images` command.

```python
c.import_image(src, data=None, repository=None, tag=None)
```

Identical to the `docker import` command. If `src` is a string or
unicode string, it will be treated as a URL to fetch the image from. To
import an image from the local machine, `src` needs to be a file-like
object or bytes collection.  To import from a tarball use your absolute
path to your tarball.  To load arbitrary data as tarball use whatever
you want as src and your tarball content in data.

```python
c.info()
```

Identical to the `docker info` command.

```python
c.insert(image, url, path)
```

Identical to the `docker insert` command.

```python
c.inspect_container(container)
```

Identical to the `docker inspect` command, but only for containers.

```python
c.inspect_image(image_id)
```

Identical to the `docker inspect` command, but only for images.

```python
c.kill(container, signal=None)
```

Kill a container. Similar to the `docker kill` command.

```python
c.login(username, password=None, email=None, registry=None)
```

Identical to the `docker login` command (but non-interactive, obviously).

```python
c.logs(container, stdout=True, stderr=True, stream=False, timestamps=False)
```

Identical to the `docker logs` command. The `stream` parameter makes the
`logs` function return a blocking generator you can iterate over to
retrieve log output as it happens.

```python
c.attach(container, stdout=True, stderr=True, stream=False, logs=False)
```

The `logs` function is a wrapper around this one, which you can use
instead if you want to fetch/stream container output without first
retrieving the entire backlog.

```python
c.ping()
```

Hits the /_ping endpoint of the remote API and returns the result.
An exception will be raised if the endpoint isn't responding.

```python
c.port(container, private_port)
```

Identical to the `docker port` command.

```python
c.pull(repository, tag=None, stream=False)
```

Identical to the `docker pull` command.

```python
c.push(repository, tag=None, stream=False)
```

Identical to the `docker push` command.

````python
c.remove_container(container, v=False, link=False)
```

Remove a container. Similar to the `docker rm` command.

```python
c.remove_image(image)
```

Remove an image. Similar to the `docker rmi` command.

```python
c.restart(container, timeout=10)
```
Restart a container. Similar to the `docker restart` command.

```python
c.search(term)
```

Identical to the `docker search` command.

```python
c.start(container, binds=None, port_bindings=None, lxc_conf=None,
        publish_all_ports=False, links=None, privileged=False,
        dns=None, dns_search=None, volumes_from=None, network_mode=None, restart_policy=None)
```

Similar to the `docker start` command, but doesn't support attach
options.  Use `docker logs` to recover `stdout`/`stderr`.

`binds` allows to bind a directory in the host to the container. See
"Using volumes" below for more information. `port_bindings` exposes
container ports to the host. See "Port bindings" below for more
information. `lxc_conf` allows to pass LXC configuration options using a
dictionary. `privileged` starts the container in privileged mode.

[Links](http://docs.docker.io/en/latest/use/working_with_links_names/)
can be specified with the `links` argument. They can either be
specified as a dictionary mapping name to alias or as a list of
`(name, alias)` tuples.

`dns` and `volumes_from` are only available if they are used with version v1.10
of docker remote API. Otherwise they are ignored.

`network_mode` is available since v1.11 and sets the Network mode for the
container ('bridge': creates a new network stack for the container on the
docker bridge, 'none': no networking for this container, 'container:[name|id]':
reuses another container network stack), 'host': use the host network stack
inside the container.

`restart_policy` is available since v1.2.0 and sets the RestartPolicy for how a container should or should not be 
restarted on exit. By default the policy is set to no meaning do not restart the container when it exits. 
The user may specify the restart policy as a dictionary for example:
for example: 
```
{
    "MaximumRetryCount": 0, 
    "Name": "always"
}
```
for always restarting the container on exit or can specify to restart the container to restart on failure and can limit
number of restarts. 
for example:
```
{
    "MaximumRetryCount": 5, 
    "Name": "on-failure"
}
```

 
```python
c.stop(container, timeout=10)
```

Stops a container. Similar to the `docker stop` command.

```python
c.tag(image, repository, tag=None, force=False)
```

Identical to the `docker tag` command.

```python
c.top(container)
```

Identical to the `docker top` command.

```python
c.version()
```

Identical to the `docker version` command.

```python
c.wait(container)
```

Wait for a container and return its exit code. Similar to the `docker
wait` command.


Port bindings
=============

Port bindings is done in two parts. Firstly, by providing a list of ports to
open inside the container in the `Client.create_container` method.

```python
c.create_container('busybox', 'ls', ports=[1111, 2222])
```

Bindings are then declared in the `Client.start` method.

```python
c.start(container_id, port_bindings={1111: 4567, 2222: None})
```

You can limit the host address on which the port will be exposed like such:

```python
c.start(container_id, port_bindings={1111: ('127.0.0.1', 4567)})
```

Or without host port assignment:

```python
c.start(container_id, port_bindings={1111: ('127.0.0.1',)})
```

If you wish to use UDP instead of TCP (default), you need to declare it
like such in both the `create_container()` and `start()` calls:

```python
container_id = c.create_container('busybox', 'ls', ports=[(1111, 'udp'), 2222])
c.start(container_id, port_bindings={'1111/udp': 4567, 2222: None})
```


Using volumes
=============

Similarly, volume declaration is done in two parts. First, you have to provide
a list of mountpoints to the `Client.create_container` method.

```python
c.create_container('busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'])
```

Volume mappings are then declared inside the `Client.start` method like this:

```python
c.start(container_id, binds={
    '/home/user1/':
        {
            'bind': '/mnt/vol2',
            'ro': False
        },
    '/var/www':
        {
            'bind': '/mnt/vol1',
            'ro': True
        }
})
```

Connection to daemon using HTTPS
================================

*These instructions are docker-py specific. Please refer to
http://docs.docker.com/articles/https/ first.*

*  Authenticate server based on public/default CA pool

```python
client = docker.Client(base_url='<https_url>', tls=True)
```

Equivalent CLI options: `docker --tls ...`

If you want to use TLS but don't want to verify the server certificate
(for example when testing with a self-signed certificate):

```python
tls_config = docker.tls.TLSConfig(verify=False)
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

* Authenticate server based on given CA

```python
tls_config = docker.tls.TLSConfig(ca_cert='/path/to/ca.pem')
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

Equivalent CLI options: `docker --tlsverify --tlscacert /path/to/ca.pem ...`

* Authenticate with client certificate, do not authenticate server
  based on given CA

```python
tls_config = docker.tls.TLSConfig(
  client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem')
)
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

Equivalent CLI options:
`docker --tls --tlscert /path/to/client-cert.pem
--tlskey /path/to/client-key.pem ...`

* Authenticate with client certificate, authenticate server based on given CA

```python
tls_config = docker.tls.TLSConfig(
  client_cert=('/path/to/client-cert.pem', '/path/to/client-key.pem'),
  ca_cert='/path/to/ca.pem'
)
client = docker.Client(base_url='<https_url>', tls=tls_config)
```

Equivalent CLI options:
`docker --tlsverify --tlscert /path/to/client-cert.pem
--tlskey /path/to/client-key.pem --tlscacert /path/to/ca.pem ...`
