# HostConfig object

The Docker Remote API introduced [support for HostConfig in version 1.15](http://docs.docker.com/reference/api/docker_remote_api_v1.15/#create-a-container). This object contains all the parameters you can pass to `Client.start`.

## HostConfig helper

### docker.utils.create_host_config

Creates a HostConfig dictionary to be used with `Client.create_container`.

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


**Params**

* container (str): The container to start
* binds: Volumes to bind. See [Using volumes](volumes.md) for more information.
* port_bindings (dict): Port bindings. See [Port bindings](port-bindings.md)
  for more information.
* lxc_conf (dict): LXC config
* publish_all_ports (bool): Whether to publish all ports to the host
* links (dict or list of tuples): either as a dictionary mapping name to alias or
  as a list of `(name, alias)` tuples
* privileged (bool): Give extended privileges to this container
* dns (list): Set custom DNS servers
* dns_search (list): DNS search domains
* volumes_from (str or list): List of container names or Ids to get volumes
  from. Optionally a single string joining container id's with commas
* network_mode (str): One of `['bridge', None, 'container:<name|id>', 'host']`
* restart_policy (dict):  "Name" param must be one of `['on-failure', 'always']`
* cap_add (list of str): Add kernel capabilities
* cap_drop (list of str): Drop kernel capabilities
* extra_hosts (dict): custom host-to-IP mappings (host:ip)
* read_only (bool): mount the container's root filesystem as read only
* pid_mode (str): if set to "host", use the host PID namespace inside the
  container
* security_opt (list): A list of string values to customize labels for MLS
  systems, such as SELinux.
* ulimits (list): A list of dicts or `docker.utils.Ulimit` objects. A list
  of ulimits to be set in the container.
* log_config (`docker.utils.LogConfig` or dict): Logging configuration to container

**Returns** (dict) HostConfig dictionary

```python
>>> from docker.utils import create_host_config
>>> create_host_config(privileged=True, cap_drop=['MKNOD'], volumes_from=['nostalgic_newton'])
{'CapDrop': ['MKNOD'], 'LxcConf': None, 'Privileged': True, 'VolumesFrom': ['nostalgic_newton'], 'PublishAllPorts': False}
```