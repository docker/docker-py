# HostConfig object

The Docker Remote API introduced [support for HostConfig in version 1.15](http://docs.docker.com/reference/api/docker_remote_api_v1.15/#create-a-container).
This object contains all the parameters you could previously pass to `Client.start`.
*It is highly recommended that users pass the HostConfig in the `host_config`*
*param of `Client.create_container` instead of `Client.start`*

## HostConfig helper

### Client.create_host_config

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
reuses another container network stack, 'host': use the host network stack
inside the container or any name that identifies an existing Docker network).

`restart_policy` is available since v1.2.0 and sets the container's *RestartPolicy*
which defines the conditions under which a container should be restarted upon exit.
If no *RestartPolicy* is defined, the container will not be restarted when it exits.
The *RestartPolicy* is specified as a dict. For example, if the container
should always be restarted:
```python
{
    "MaximumRetryCount": 0,
    "Name": "always"
}
```

It is possible to restart the container only on failure as well as limit the number
of restarts. For example:
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

* binds: Volumes to bind. See [Using volumes](volumes.md) for more information.
* port_bindings (dict): Port bindings. See [Port bindings](port-bindings.md)
  for more information.
* lxc_conf (dict): LXC config
* oom_kill_disable (bool): Whether to disable OOM killer
* oom_score_adj (int): An integer value containing the score given to the
  container in order to tune OOM killer preferences
* publish_all_ports (bool): Whether to publish all ports to the host
* links (dict or list of tuples): either as a dictionary mapping name to alias
  or as a list of `(name, alias)` tuples
* privileged (bool): Give extended privileges to this container
* dns (list): Set custom DNS servers
* dns_search (list): DNS search domains
* volumes_from (str or list): List of container names or Ids to get volumes
  from. Optionally a single string joining container id's with commas
* network_mode (str): One of `['bridge', 'none', 'container:<name|id>', 'host']`
* restart_policy (dict):  "Name" param must be one of
  `['on-failure', 'always']`
* cap_add (list of str): Add kernel capabilities
* cap_drop (list of str): Drop kernel capabilities
* extra_hosts (dict): custom host-to-IP mappings (host:ip)
* read_only (bool): mount the container's root filesystem as read only
* pid_mode (str): Set the PID namespace for the container
* ipc_mode (str): Set the IPC mode for the container
* security_opt (list): A list of string values to customize labels for MLS
  systems, such as SELinux.
* ulimits (list): A list of dicts or `docker.utils.Ulimit` objects. A list
  of ulimits to be set in the container.
* log_config (`docker.utils.LogConfig` or dict): Logging configuration to
  container
* mem_limit (str or int): Maximum amount of memory container is allowed to
  consume. (e.g. `'1G'`)
* memswap_limit (str or int): Maximum amount of memory + swap a container is
  allowed to consume.
* mem_swappiness (int): Tune a container's memory swappiness behavior.
  Accepts number between 0 and 100.
* shm_size (str or int): Size of /dev/shm. (e.g. `'1G'`)
* cpu_group (int): The length of a CPU period in microseconds.
* cpu_period (int): Microseconds of CPU time that the container can get in a
  CPU period.
* cpu_shares (int): CPU shares (relative weight)
* cpuset_cpus (str): CPUs in which to allow execution (0-3, 0,1)
* blkio_weight: Block IO weight (relative weight), accepts a weight value
  between 10 and 1000.
* blkio_weight_device: Block IO weight (relative device weight) in the form of:
  `[{"Path": "device_path", "Weight": weight}]`
* device_read_bps: Limit read rate (bytes per second) from a device in the
  form of: `[{"Path": "device_path", "Rate": rate}]`
* device_write_bps: Limit write rate (bytes per second) from a device.
* device_read_iops: Limit read rate (IO per second) from a device.
* device_write_iops: Limit write rate (IO per second) from a device.
* group_add (list): List of additional group names and/or IDs that the
  container process will run as.
* devices (list): Host device bindings. See [host devices](host-devices.md)
  for more information.
* tmpfs: Temporary filesystems to mount. See [Using tmpfs](tmpfs.md) for more
  information.
* sysctls (dict): Kernel parameters to set in the container.
* userns_mode (str): Sets the user namespace mode for the container when user
  namespace remapping option is enabled. Supported values are: `host`
* pids_limit (int): Tune a container’s pids limit. Set -1 for unlimited.

**Returns** (dict) HostConfig dictionary

```python
>>> from docker import Client
>>> cli = Client()
>>> cli.create_host_config(privileged=True, cap_drop=['MKNOD'], volumes_from=['nostalgic_newton'])
{'CapDrop': ['MKNOD'], 'LxcConf': None, 'Privileged': True, 'VolumesFrom': ['nostalgic_newton'], 'PublishAllPorts': False}
```
