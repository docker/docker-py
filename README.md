docker-py
=========

[![Build Status](https://travis-ci.org/dotcloud/docker-py.png)](https://travis-ci.org/dotcloud/docker-py)

An API client for docker written in Python

API
===

To instantiate a `Client` class that will allow you to communicate with
a Docker daemon, simply do:

```python
c = docker.Client(base_url='unix://var/run/docker.sock',
                  version='1.6',
                  timeout=10)
```

`base_url` refers to the protocol+hostname+port where the docker server
is hosted. `version` is the version of the API the client will use and
`timeout` specifies the HTTP request timeout, in seconds.

```python
c.build(path=None, tag=None, quiet=False, fileobj=None, nocache=False,
        rm=False, stream=False)
```

Similar to the `docker build` command. Either `path` or `fileobj` needs
to be set. `path` can be a local path (to a directory containing a
Dockerfile) or a remote URL. `fileobj` must be a readable file-like
object to a Dockerfile.

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
                   entrypoint=None, cpu_shares=None, working_dir=None)
```

Creates a container that can then be `start`ed. Parameters are similar
to those for the `docker run` command except it doesn't support the
attach options (`-a`). See "Port bindings" and "Using volumes" below for
more information on how to create port bindings and volume mappings.

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
c.logs(container, stdout=True, stderr=True, stream=False)
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
c.port(container, private_port)
```

Identical to the `docker port` command.

```python
c.pull(repository, tag=None, stream=False)
```

Identical to the `docker pull` command.

```python
c.push(repository, stream=False)
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
        publish_all_ports=False, links=None, privileged=False)
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

If you wish to use UDP instead of TCP (default), you can declare it like such:

```python
c.create_container('busybox', 'ls', ports=[(1111, 'udp'), 2222])
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
    '/home/user1/': '/mnt/vol2',
    '/var/www': '/mnt/vol1'
})
```
