# Client API

To instantiate a `Client` class that will allow you to communicate with a
Docker daemon, simply do:

```python
from docker import Client
c = Client(base_url='unix://var/run/docker.sock')
```

**Params**:

* base_url (str): Refers to the protocol+hostname+port where the Docker server
is hosted.
* version (str): The version of the API the client will use. Specify `'auto'`
  to use the API version provided by the server.
* timeout (int): The HTTP request timeout, in seconds.
* tls (bool or [TLSConfig](tls.md#TLSConfig)): Equivalent CLI options: `docker --tls ...`

****

## attach

The `.logs()` function is a wrapper around this method, which you can use
instead if you want to fetch/stream container output without first retrieving
the entire backlog.

**Params**:

* container (str): The container to attach to
* stdout (bool): Get STDOUT
* stderr (bool): Get STDERR
* stream (bool): Return an interator
* logs (bool): Get all previous output

**Returns** (generator or str): The logs or output for the image

## build

Similar to the `docker build` command. Either `path` or `fileobj` needs to be
set. `path` can be a local path (to a directory containing a Dockerfile) or a
remote URL. `fileobj` must be a readable file-like object to a Dockerfile.

If you have a tar file for the Docker build context (including a Dockerfile)
already, pass a readable file-like object to `fileobj` and also pass
`custom_context=True`. If the stream is compressed also, set `encoding` to the
correct value (e.g `gzip`).

**Params**:

* path (str): Path to the directory containing the Dockerfile
* tag (str): A tag to add to the final image
* quiet (bool): Whether to return the status
* fileobj: A file object to use as the Dockerfile. (Or a file-like object)
* nocache (bool): Don't use the cache when set to `True`
* rm (bool): Remove intermediate containers. The `docker build` command now
  defaults to ``--rm=true``, but we have kept the old default of `False`
  to preserve backward compatibility
* stream (bool): *Deprecated for API version > 1.8 (always True)*.
  Return a blocking generator you can iterate over to retrieve build output as
  it happens
* timeout (int): HTTP timeout
* custom_context (bool): Optional if using `fileobj`
* encoding (str): The encoding for a stream. Set to `gzip` for compressing
* pull (bool): Downloads any updates to the FROM image in Dockerfiles
* forcerm (bool): Always remove intermediate containers, even after unsuccessful builds
* dockerfile (str): path within the build context to the Dockerfile
* container_limits (dict): A dictionary of limits applied to each container
  created by the build process. Valid keys:
    - memory (int): set memory limit for build
    - memswap (int): Total memory (memory + swap), -1 to disable swap
    - cpushares (int): CPU shares (relative weight)
    - cpusetcpus (str): CPUs in which to allow exection, e.g., `"0-3"`, `"0,1"`

**Returns** (generator): A generator of the build output

```python
>>> from io import BytesIO
>>> from docker import Client
>>> dockerfile = '''
... # Shared Volume
... FROM busybox:buildroot-2014.02
... MAINTAINER first last, first.last@yourdomain.com
... VOLUME /data
... CMD ["/bin/sh"]
... '''
>>> f = BytesIO(dockerfile.encode('utf-8'))
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> response = [line for line in cli.build(
...     fileobj=f, rm=True, tag='yourname/volume'
... )]
>>> response
['{"stream":" ---\\u003e a9eb17255234\\n"}',
'{"stream":"Step 1 : MAINTAINER first last, first.last@yourdomain.com\\n"}',
'{"stream":" ---\\u003e Running in 08787d0ee8b1\\n"}',
'{"stream":" ---\\u003e 23e5e66a4494\\n"}',
'{"stream":"Removing intermediate container 08787d0ee8b1\\n"}',
'{"stream":"Step 2 : VOLUME /data\\n"}',
'{"stream":" ---\\u003e Running in abdc1e6896c6\\n"}',
'{"stream":" ---\\u003e 713bca62012e\\n"}',
'{"stream":"Removing intermediate container abdc1e6896c6\\n"}',
'{"stream":"Step 3 : CMD [\\"/bin/sh\\"]\\n"}',
'{"stream":" ---\\u003e Running in dba30f2a1a7e\\n"}',
'{"stream":" ---\\u003e 032b8b2855fc\\n"}',
'{"stream":"Removing intermediate container dba30f2a1a7e\\n"}',
'{"stream":"Successfully built 032b8b2855fc\\n"}']
```

**Raises:** [TypeError](
https://docs.python.org/3.4/library/exceptions.html#TypeError) if `path` nor
`fileobj` are specified

## commit

Identical to the `docker commit` command.

**Params**:

* container (str): The image hash of the container
* repository (str): The repository to push the image to
* tag (str): The tag to push
* message (str): A commit message
* author (str): The name of the author
* conf (dict): The configuraton for the container. See the [Docker remote api](
https://docs.docker.com/reference/api/docker_remote_api/) for full details.

## containers

List containers. Identical to the `docker ps` command.

**Params**:

* quiet (bool): Only display numeric Ids
* all (bool): Show all containers. Only running containers are shown by default
* trunc (bool): Truncate output
* latest (bool): Show only the latest created container, include non-running
ones.
* since (str): Show only containers created since Id or Name, include
non-running ones
* before (str): Show only container created before Id or Name, include
non-running ones
* limit (int): Show `limit` last created containers, include non-running ones
* size (bool): Display sizes
* filters (dict): Filters to be processed on the image list. Available filters:
    - `exited` (int): Only containers with specified exit code
    - `status` (str): One of `restarting`, `running`, `paused`, `exited`
    - `label` (str): format either `"key"` or `"key=value"`

**Returns** (dict): The system's containers

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> cli.containers()
[{'Command': '/bin/sleep 30',
  'Created': 1412574844,
  'Id': '6e276c9e6e5759e12a6a9214efec6439f80b4f37618e1a6547f28a3da34db07a',
  'Image': 'busybox:buildroot-2014.02',
  'Names': ['/grave_mayer'],
  'Ports': [],
  'Status': 'Up 1 seconds'}]
```

## copy
Identical to the `docker cp` command. Get files/folders from the container.

**Params**:

* container (str): The container to copy from
* resource (str): The path within the container

**Returns** (str): The contents of the file as a string

## create_container

Creates a container that can then be `.start()` ed. Parameters are similar to
those for the `docker run` command except it doesn't support the attach
options (`-a`).

See [Port bindings](port-bindings.md) and [Using volumes](volumes.md) for more
information on how to create port bindings and volume mappings.

The `mem_limit` variable accepts float values (which represent the memory limit
of the created container in bytes) or a string with a units identification char
('100000b', 1000k', 128m', '1g'). If a string is specified without a units
character, bytes are assumed as an intended unit.

`volumes_from` and `dns` arguments raise [TypeError](
https://docs.python.org/3.4/library/exceptions.html#TypeError) exception if
they are used against v1.10 and above of the Docker remote API. Those
arguments should be passed to `start()` instead, or as part of the `host_config`
dictionary.

**Params**:

* image (str): The image to run
* command (str or list): The command to be run in the container
* hostname (str): Optional hostname for the container
* user (str or int): Username or UID
* detach (bool): Detached mode: run container in the background and print new
container Id
* stdin_open (bool): Keep STDIN open even if not attached
* tty (bool): Allocate a pseudo-TTY
* mem_limit (float or str): Memory limit (format: [number][optional unit],
where unit = b, k, m, or g)
* ports (list of ints): A list of port numbers
* environment (dict or list): A dictionary or a list of strings in the
following format `["PASSWORD=xxx"]` or `{"PASSWORD": "xxx"}`.
* dns (list): DNS name servers
* volumes (str or list):
* volumes_from (str or list): List of container names or Ids to get volumes
from. Optionally a single string joining container id's with commas
* network_disabled (bool): Disable networking
* name (str): A name for the container
* entrypoint (str or list): An entrypoint
* cpu_shares (int or float): CPU shares (relative weight)
* working_dir (str): Path to the working directory
* domainname (str or list): Set custom DNS search domains
* memswap_limit (int):
* host_config (dict): A [HostConfig](hostconfig.md) dictionary
* mac_address (str): The Mac Address to assign the container
* labels (dict or list): A dictionary of name-value labels (e.g. `{"label1": "value1", "label2": "value2"}`) or a list of names of labels to set with empty values (e.g. `["label1", "label2"]`)

**Returns** (dict): A dictionary with an image 'Id' key and a 'Warnings' key.

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> container = cli.create_container(image='busybox:latest', command='/bin/sleep 30')
>>> print(container)
{'Id': '8a61192da2b3bb2d922875585e29b74ec0dc4e0117fcbf84c962204e97564cd7',
 'Warnings': None}
```

## diff

Inspect changes on a container's filesystem

**Params**:

* container (str): The container to diff

**Returns** (str):

## events

Identical to the `docker events` command: get real time events from the server. The `events`
function return a blocking generator you can iterate over to retrieve events as they happen.

**Params**:

* since (datetime or int): get events from this point

* until (datetime or int): get events until this point

* filters (dict): filter the events by event time, container or image

**Returns** (generator):

```python
{u'status': u'start',
 u'from': u'image/with:tag',
 u'id': u'container-id',
 u'time': 1423339459}
```

## execute

This command is deprecated for docker-py >= 1.2.0 ; use `exec_create` and
`exec_start` instead.

## exec_create

Sets up an exec instance in a running container.

**Params**:

* container (str): Target container where exec instance will be created
* cmd (str or list): Command to be executed
* stdout (bool): Attach to stdout of the exec command if true. Default: True
* stderr (bool): Attach to stderr of the exec command if true. Default: True
* tty (bool): Allocate a pseudo-TTY. Default: False

**Returns** (dict): A dictionary with an exec 'Id' key.


## exec_inspect

Return low-level information about an exec command.

**Params**:

* exec_id (str): ID of the exec instance

**Returns** (dict): Dictionary of values returned by the endpoint.


## exec_resize

Resize the tty session used by the specified exec command.

**Params**:

* exec_id (str): ID of the exec instance
* height (int): Height of tty session
* width (int): Width of tty session

## exec_start

Start a previously set up exec instance.

**Params**:

* exec_id (str): ID of the exec instance
* detach (bool): If true, detach from the exec command. Default: False
* tty (bool): Allocate a pseudo-TTY. Default: False
* stream (bool): Stream response data

**Returns** (generator or str): If `stream=True`, a generator yielding response
chunks. A string containing response data otherwise.

## export

Export the contents of a filesystem as a tar archive to STDOUT

**Params**:

* container (str): The container to export

**Returns** (str): The filesystem tar archive as a str

## get_image

Get an image from the docker daemon. Similar to the `docker save` command.

**Params**:

* image (str): Image name to get

**Returns** (urllib3.response.HTTPResponse object): The response from the docker daemon

An example of how to get (save) an image to a file.
```python
>>> from docker import Client
>>> cli = Client(base_url='unix://var/run/docker.sock')
>>> image = cli.get_image(“fedora:latest”)
>>> image_tar = open(‘/tmp/fedora-latest.tar’,’w’)
>>> image_tar.write(image.data)
>>> image_tar.close()
```

## history

Show the history of an image

**Params**:

* image (str): The image to show history for

**Returns** (str): The history of the image

## images

List images. Identical to the `docker images` command.

**Params**:

* name (str): Only show images belonging to the repository `name`
* quiet (bool): Only show numeric Ids. Returns a list
* all (bool): Show all images (by default filter out the intermediate image
layers)
* filters (dict): Filters to be processed on the image list. Available filters:
    - `dangling` (bool)
    - `label` (str): format either `"key"` or `"key=value"`

**Returns** (dict or list): A list if `quiet=True`, otherwise a dict.

```python
[{'Created': 1401926735,
'Id': 'a9eb172552348a9a49180694790b33a1097f546456d041b6e82e4d7716ddb721',
'ParentId': '120e218dd395ec314e7b6249f39d2853911b3d6def6ea164ae05722649f34b16',
'RepoTags': ['busybox:buildroot-2014.02', 'busybox:latest'],
'Size': 0,
'VirtualSize': 2433303},
...
```

## import_image

Similar to the `docker import` command.

If `src` is a string or unicode string, it will first be treated as a path to
a tarball on the local system. If there is an error reading from that file,
src will be treated as a URL instead to fetch the image from. You can also pass
an open file handle as 'src', in which case the data will be read from that
file.

If `src` is unset but `image` is set, the `image` paramater will be taken as
the name of an existing image to import from.

**Params**:

* src (str or file): Path to tarfile, URL, or file-like object
* repository (str): The repository to create
* tag (str): The tag to apply
* image (str): Use another image like the `FROM` Dockerfile parameter

## import_image_from_data

Like `.import_image()`, but allows importing in-memory bytes data.

**Params**:

* data (bytes collection): Bytes collection containing valid tar data
* repository (str): The repository to create
* tag (str): The tag to apply

## import_image_from_file

Like `.import_image()`, but only supports importing from a tar file on
disk. If the file doesn't exist it will raise `IOError`.

**Params**:

* filename (str): Full path to a tar file.
* repository (str): The repository to create
* tag (str): The tag to apply

## import_image_from_url

Like `.import_image()`, but only supports importing from a URL.

**Params**:

* url (str): A URL pointing to a tar file.
* repository (str): The repository to create
* tag (str): The tag to apply

## import_image_from_image

Like `.import_image()`, but only supports importing from another image,
like the `FROM` Dockerfile parameter.

**Params**:

* image (str): Image name to import from
* repository (str): The repository to create
* tag (str): The tag to apply

## info

Display system-wide information. Identical to the `docker info` command.

**Returns** (dict): The info as a dict

```
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> cli.info()
{'Containers': 3,
 'Debug': 1,
 'Driver': 'aufs',
 'DriverStatus': [['Root Dir', '/mnt/sda1/var/lib/docker/aufs'],
  ['Dirs', '225']],
 'ExecutionDriver': 'native-0.2',
 'IPv4Forwarding': 1,
 'Images': 219,
 'IndexServerAddress': 'https://index.docker.io/v1/',
 'InitPath': '/usr/local/bin/docker',
 'InitSha1': '',
 'KernelVersion': '3.16.1-tinycore64',
 'MemoryLimit': 1,
 'NEventsListener': 0,
 'NFd': 11,
 'NGoroutines': 12,
 'OperatingSystem': 'Boot2Docker 1.2.0 (TCL 5.3);',
 'SwapLimit': 1}
```

## insert
*DEPRECATED*

## inspect_container

Identical to the `docker inspect` command, but only for containers.

**Params**:

* container (str): The container to inspect

**Returns** (dict): Nearly the same output as `docker inspect`, just as a
single dict

## inspect_image

Identical to the `docker inspect` command, but only for images

**Params**:

* image_id (str): The image to inspect

**Returns** (dict): Nearly the same output as `docker inspect`, just as a
single dict

## kill

Kill a container or send a signal to a container

**Params**:

* container (str): The container to kill
* signal (str or int): The singal to send. Defaults to `SIGKILL`

## login

Nearly identical to the `docker login` command, but non-interactive.

**Params**:

* username (str): The registry username
* password (str): The plaintext password
* email (str): The email for the registry account
* registry (str): URL to the registry. Ex:`https://index.docker.io/v1/`
* reauth (bool): Whether refresh existing authentication on the docker server.
* dockercfg_path (str): Use a custom path for the .dockercfg file
  (default `$HOME/.dockercfg`)

**Returns** (dict): The response from the login request

## logs

Identical to the `docker logs` command. The `stream` parameter makes the `logs`
function return a blocking generator you can iterate over to retrieve log
output as it happens.

**Params**:

* container (str): The container to get logs from
* stdout (bool): Get STDOUT
* stderr (bool): Get STDERR
* stream (bool): Stream the response
* timestamps (bool): Show timestamps
* tail (str or int): Output specified number of lines at the end of logs: `"all"` or `number`. Default `"all"`

**Returns** (generator or str):

## pause

Pauses all processes within a container.

**Params**:

* container (str): The container to pause


## ping

Hits the `/_ping` endpoint of the remote API and returns the result. An
exception will be raised if the endpoint isn't responding.

**Returns** (bool)

## port
Lookup the public-facing port that is NAT-ed to `private_port`. Identical to
the `docker port` command.

**Params**:

* container (str): The container to look up
* private_port (int): The private port to inspect

**Returns** (list of dict): The mapping for the host ports

```bash
$ docker run -d -p 80:80 ubuntu:14.04 /bin/sleep 30
7174d6347063a83f412fad6124c99cffd25ffe1a0807eb4b7f9cec76ac8cb43b
```
```python
>>> cli.port('7174d6347063', 80)
[{'HostIp': '0.0.0.0', 'HostPort': '80'}]
```

## pull

Identical to the `docker pull` command.

**Params**:

* repository (str): The repository to pull
* tag (str): The tag to pull
* stream (bool): Stream the output as a generator
* insecure_registry (bool): Use an insecure registry
* auth_config (dict): Override the credentials that Client.login has set for this request
  `auth_config` should contain the `username` and `password` keys to be valid.

**Returns** (generator or str): The output

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> for line in cli.pull('busybox', stream=True):
...     print(json.dumps(json.loads(line), indent=4))
{
    "status": "Pulling image (latest) from busybox",
    "progressDetail": {},
    "id": "e72ac664f4f0"
}
{
    "status": "Pulling image (latest) from busybox, endpoint: ...",
    "progressDetail": {},
    "id": "e72ac664f4f0"
}
```

## push

Push an image or a repository to the registry. Identical to the `docker push`
command

**Params**:

* repository (str): The repository to push to
* tag (str): An optional tag to push
* stream (bool): Stream the output as a blocking generator
* insecure_registry (bool): Use `http://` to connect to the registry

**Returns** (generator or str): The output of the upload

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> response = [line for line in cli.push('yourname/app', stream=True)]
>>> response
['{"status":"Pushing repository yourname/app (1 tags)"}\\n',
 '{"status":"Pushing","progressDetail":{},"id":"511136ea3c5a"}\\n',
 '{"status":"Image already pushed, skipping","progressDetail":{},
    "id":"511136ea3c5a"}\\n',
 ...
 '{"status":"Pushing tag for rev [918af568e6e5] on {
    https://cdn-registry-1.docker.io/v1/repositories/
    yourname/app/tags/latest}"}\\n']
```

## remove_container

Remove a container. Similar to the `docker rm` command.

**Params**:

* container (str): The container to remove
* v (bool): Remove the volumes associated with the container
* link (bool): Remove the specified link and not the underlying container
* force (bool): Force the removal of a running container (uses SIGKILL)

## remove_image

Remove an image. Similar to the `docker rmi` command.

**Params**:

* image (str): The image to remove
* force (bool): Force removal of the image
* noprune (bool): Do not delete untagged parents

## rename

Rename a container. Similar to the `docker rename` command.

**Params**:

* container (str): ID of the container to rename
* name (str): New name for the container

## restart

Restart a container. Similar to the `docker restart` command.

If `container` a dict, the `Id` key is used.

**Params**:

* container (str or dict): The container to restart
* timeout (int): Number of seconds to try to stop for before killing the
container. Once killed it will then be restarted. Default is 10 seconds.

## search
Identical to the `docker search` command.

**Params**:

* term (str): A term to search for

**Returns** (list of dicts): The response of the search

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> response = cli.search('nginx')
>>> response[:2]
[{'description': 'Official build of Nginx.',
  'is_official': True,
  'is_trusted': False,
  'name': 'nginx',
  'star_count': 266},
 {'description': 'Trusted automated Nginx (http://nginx.org/) ...',
  'is_official': False,
  'is_trusted': True,
  'name': 'dockerfile/nginx',
  'star_count': 60},
  ...
```

## start

Similar to the `docker start` command, but doesn't support attach options. Use
`.logs()` to recover `stdout`/`stderr`.

`binds` allows to bind a directory in the host to the container. See [Using
volumes](volumes.md) for more information.

`port_bindings` exposes container ports to the host.
See [Port bindings](port-bindings.md) for more information.

`lxc_conf` allows to pass LXC configuration options using a dictionary.

`privileged` starts the container in privileged mode.

[Links](http://docs.docker.io/en/latest/use/working_with_links_names/) can be
specified with the `links` argument. They can either be specified as a
dictionary mapping name to alias or as a list of `(name, alias)` tuples.

`dns` and `volumes_from` are only available if they are used with version v1.10
of docker remote API. Otherwise they are ignored.

`network_mode` is available since v1.11 and sets the Network mode for the
container ('bridge': creates a new network stack for the container on the
Docker bridge, 'none': no networking for this container, 'container:[name|id]':
reuses another container network stack), 'host': use the host network stack
inside the container.

`restart_policy` is available since v1.2.0 and sets the RestartPolicy for how a
container should or should not be restarted on exit. By default the policy is
set to no meaning do not restart the container when it exits. The user may
specify the restart policy as a dictionary for example:
```python
{
    "MaximumRetryCount": 0,
    "Name": "always"
}
```

For always restarting the container on exit or can specify to restart the
container to restart on failure and can limit number of restarts. For example:
```python
{
    "MaximumRetryCount": 5,
    "Name": "on-failure"
}
```

`cap_add` and `cap_drop` are available since v1.2.0 and can be used to add or
drop certain capabilities. The user may specify the capabilities as an array
for example:
```python
[
    "SYS_ADMIN",
    "MKNOD"
]
```

**Params**:

* container (str): The container to start
* binds: Volumes to bind
* port_bindings (dict): Port bindings. See note above
* lxc_conf (dict): LXC config
* publish_all_ports (bool): Whether to publish all ports to the host
* links (dict or list of tuples): See note above
* privileged (bool): Give extended privileges to this container
* dns (list): Set custom DNS servers
* dns_search (list): DNS search  domains
* volumes_from (str or list): List of container names or Ids to get volumes
from. Optionally a single string joining container id's with commas
* network_mode (str): One of `['bridge', None, 'container:<name|id>',
'host']`
* restart_policy (dict): See note above. "Name" param must be one of
`['on-failure', 'always']`
* cap_add (list of str): See note above
* cap_drop (list of str): See note above
* extra_hosts (dict): custom host-to-IP mappings (host:ip)
* pid_mode (str): if set to "host", use the host PID namespace inside the
  container
* security_opt (list): A list of string values to customize labels for MLS systems, such as SELinux.
* ulimits (list): A list of dicts or `docker.utils.Ulimit` objects.

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> container = cli.create_container(
...     image='busybox:latest',
...     command='/bin/sleep 30')
>>> response = cli.start(container=container.get('Id'))
>>> print(response)
None
```

## stats

The Docker API parallel to the `docker stats` command.
This will stream statistics for a specific container.

**Params**:

* container (str): The container to start

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> stats_obj = cli.stats('elasticsearch')
>>> for stat in stats_obj:
>>>     print(stat)
{"read":"2015-02-11T21:47:30.49388286+02:00","network":{"rx_bytes":666052,"rx_packets":4409 ...
...
...
...
```

## stop

Stops a container. Similar to the `docker stop` command.

**Params**:

* container (str): The container to stop
* timeout (int): Timeout in seconds to wait for the container to stop before
sending a `SIGKILL`

## tag

Tag an image into a repository. Identical to the `docker tag` command.

**Params**:

* image (str): The image to tag
* repository (str): The repository to set for the tag
* tag (str): The tag name
* force (bool): Force

**Returns** (bool): True if successful

## top
Display the running processes of a container

**Params**:

* container (str): The container to inspect

**Returns** (str): The output of the top

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> cli.create_container('busybox:latest', '/bin/sleep 30', name='sleeper')
>>> cli.start('sleeper')
>>> cli.top('sleeper')
{'Processes': [['952', 'root', '/bin/sleep 30']],
 'Titles': ['PID', 'USER', 'COMMAND']}
```

## unpause

Unpauses all processes within a container.

**Params**:

* container (str): The container to unpause

## version
Nearly identical to the `docker version` command.

**Returns** (dict): The server version information

```python
>>> from docker import Client
>>> cli = Client(base_url='tcp://127.0.0.1:2375')
>>> cli.version()
{
    "KernelVersion": "3.16.4-tinycore64",
    "Arch": "amd64",
    "ApiVersion": "1.15",
    "Version": "1.3.0",
    "GitCommit": "c78088f",
    "Os": "linux",
    "GoVersion": "go1.3.3"
}
```


## wait
Identical to the `docker wait` command. Block until a container stops, then
print its exit code. Returns the value `-1` if no `StatusCode` is returned by
the API.

If `container` a dict, the `Id` key is used.

**Params**:

* container (str or dict): The container to wait on
* timeout (int): Request timeout

**Returns** (int): The exit code of the container


<!---
TODO:

* events
* load_image
* resize

-->
