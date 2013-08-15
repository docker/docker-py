docker-py
=========

An API client for docker written in Python

API
===

`docker.Client(base_url='unix://var/run/docker.sock', version="1.3")`  
Client class. `base_url` refers to the protocol+hostname+port where the docker
server is hosted. Version is the version of the API the client will use.

* `c.build(path=None, tag=None, quiet=False, fileobj=None, nocache=False)`  
Similar to the `docker build` command. Either `path` or `fileobj` needs to be
set. `path` can be a local path (to a directory containing a Dockerfile) or a
remote URL. `fileobj` must be a readable file-like object to a Dockerfile.

* `c.commit(container, repository=None, tag=None, message=None, author=None, conf=None)`  
Identical to the `docker commit` command.

* `c.containers(quiet=False, all=False, trunc=True, latest=False, since=None, before=None, limit=-1)`  
Identical to the `docker ps` command.

* `c.create_container(image, command, hostname=None, user=None, detach=False, stdin_open=False, tty=False, mem_limit=0, ports=None, environment=None, dns=None, volumes=None, volumes_from=None)`  
Creates a container that can then be `start`ed. Parameters are similar to those
for the `docker run` command except it doesn't support the attach options
(`-a`)

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

* `c.info()`  
Identical to the `docker info` command.

* `c.insert(url, path)`  
Identical to the `docker insert` command.

* `c.inspect_container(container_id)`  
Identical to the `docker inspect` command, but can only be used with a container ID.

* `c.inspect_image(container_id)`  
Identical to the `docker inspect` command, but can only be used with an image ID.

* `c.kill(containers...)`  
Identical to the `docker kill` command.

* `c.login(username, password=None, email=None)`  
Identical to the `docker login` command (but non-interactive, obviously).

* `c.logs(container)`  
Identical to the `docker logs` command.

* `c.port(container, private_port)`  
Identical to the `docker port` command.

* `c.pull(repository, tag=None, registry=None)`  
Identical to the `docker pull` command.

* `c.push(repository)`  
Identical to the `docker push` command.

* `c.remove_container(containers..., v=False)`  
Identical to the `docker rm` command.

* `c.remove_image(images...)`  
Identical to the `docker rmi` command.

* `c.restart(containers..., t=10)`  
Identical to the `docker restart` command.

* `c.search(term)`  
Identical to the `docker search` command.

* `c.start(container)`  
Identical to the `docker start` command, but doesn't support attach options.
Use `docker logs` to recover `stdout`/`stderr`

* `c.start(container, binds={'/host': '/mnt'})`  
Allows to bind a directory in the host to the container.
Similar to the `docker run` command with the `-b="/host:/mnt"`.
Requires the container to be created with the volumes argument:
`c.create_container(..., volumes={'/mnt': {}})`

* `c.stop(containers..., t=10)`  
Identical to the `docker stop` command.

* `c.tag(image, repository, tag=None, force=False)`  
Identical to the `docker tag` command.

* `c.version()`  
Identical to the `docker version` command.

* `c.wait(containers...)`  
Identical to the `docker wait` command.

