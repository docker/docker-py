docker-py
=========

[![Build Status](https://travis-ci.org/dotcloud/docker-py.png)](https://travis-ci.org/dotcloud/docker-py)

An API client for docker written in Python

API
===

`docker.Client(base_url='unix://var/run/docker.sock', version="1.4",
timeout=60)`  
Client class. `base_url` refers to the protocol+hostname+port where the docker
server is hosted. Version is the version of the API the client will use.

* `c.build(path=None, tag=None, quiet=False, fileobj=None, nocache=False, rm=False)`  
Similar to the `docker build` command. Either `path` or `fileobj` needs to be
set. `path` can be a local path (to a directory containing a Dockerfile) or a
remote URL. `fileobj` must be a readable file-like object to a Dockerfile.

* `c.commit(container, repository=None, tag=None, message=None, author=None, conf=None)`  
Identical to the `docker commit` command.

* `c.containers(quiet=False, all=False, trunc=True, latest=False, since=None,before=None, limit=-1)`  
Identical to the `docker ps` command.

* `c.copy(container, resource)`  
Identical to the `docker cp` command.

* <code>c.create_container(image, command=None, hostname=None, user=None,
        detach=False, stdin_open=False, tty=False, mem_limit=0, ports=None, environment=None, dns=None, volumes=None, volumes_from=None, 
        name=None)</code>  
Creates a container that can then be `start`ed. Parameters are similar to those
for the `docker run` command except it doesn't support the attach options
(`-a`)  
See "Port bindings" and "Using volumes" below for more information on how to
create port bindings and volume mappings.

* `c.diff(container)`  
Identical to the `docker diff` command.

* `c.export(container)`  
Identical to the `docker export` command.

* `c.history(image)`  
Identical to the `docker history` command.

* `c.images(name=None, quiet=False, all=False, viz=False)`  
Identical to the `docker images` command.

* `c.import_image(src, repository=None, tag=None)`  
Identical to the `docker import` command. If `src` is a string or unicode
string, it will be treated as a URL to fetch the image from. To import an image
from the local machine, `src` needs to be a file-like object or bytes
collection.
To import from a tarball use your absolute path to your tarball.
To load arbitrary data as tarball use whatever you want as src and your tarball content in data.

* `c.info()`  
Identical to the `docker info` command.

* `c.insert(url, path)`  
Identical to the `docker insert` command.

* `c.inspect_container(container)`  
Identical to the `docker inspect` command, but only for containers.

* `c.inspect_image(image_id)`  
Identical to the `docker inspect` command, but only for images.

* `c.kill(container, signal=None)`  
Kill a container. Similar to the `docker kill` command.

* `c.login(username, password=None, email=None)`  
Identical to the `docker login` command (but non-interactive, obviously).

* `c.logs(container)`  
Identical to the `docker logs` command.

* `c.port(container, private_port)`  
Identical to the `docker port` command.

* `c.pull(repository, tag=None)`
Identical to the `docker pull` command.

* `c.push(repository)`  
Identical to the `docker push` command.

* `c.remove_container(container, v=False)`  
Remove a container. Similar to the `docker rm` command.

* `c.remove_image(image)`  
Remove an image. Similar to the `docker rmi` command.

* `c.restart(container, timeout=10)`  
Restart a container. Similar to the `docker restart` command.

* `c.search(term)`  
Identical to the `docker search` command.

* `c.start(container, binds=None, port_bindings=None, lxc_conf=None, privileged=False)`
Similar to the `docker start` command, but doesn't support attach options.
Use `docker logs` to recover `stdout`/`stderr`  
`binds` Allows to bind a directory in the host to the container. See 
"Using volumes" below for more information.
`port_bindings` Exposes container ports to the host. See "Port bindings" below
for more information.
`lxc_conf` allows to pass LXC configuration options using a dictionary.
`privileged` starts the container in privileged mode.

* `c.stop(container, timeout=10)`  
Stops a container. Similar to the `docker stop` command.

* `c.tag(image, repository, tag=None, force=False)`  
Identical to the `docker tag` command.

* `c.top(container_id)`  
Identical to the `docker top` command.

* `c.version()`  
Identical to the `docker version` command.

* `c.wait(container)`  
Wait for a container and return its exit code. Similar to the `docker wait`
command.



Port bindings
=============

Port bindings is done in two parts. Firstly, by providing a list of ports to
open inside the container in the `Client.create_container` method.

    client.create_container('busybox', 'ls', ports=[1111, 2222])

If you wish to use UDP instead of TCP (default), you can declare it like such:

    client.create_container('busybox', 'ls', ports=[(1111, 'udp'), 2222])

Bindings are then declared in the `Client.start` method.

    client.start(container_id, port_bindings={
        1111: 4567,
        2222: None
    })

You can limit the host address on which the port will be exposed like such:

    client.start(container_id, port_bindings={
        1111: ('127.0.0.1', 4567)
    })

or without host port assignment:

    client.start(container_id, port_bindings={
        1111: ('127.0.0.1',)
    })



Using volumes
=============

Similarly, volume declaration is done in two parts. First, you have to provide
a list of mountpoints to the `Client.create_container` method.

    client.create_container('busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'])

Volume mappings are then declared inside the `Client.start` method like this:

    client.start(container_id, bindings={
            '/mnt/vol2': '/home/user1/',
            '/mnt/vol1': '/var/www'
    })
