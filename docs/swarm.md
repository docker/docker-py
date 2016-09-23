# Swarm management

Starting with Engine version 1.12 (API 1.24), it is possible to manage the
engine's associated Swarm cluster using the API.

## Initializing a new Swarm

You can initialize a new Swarm by calling `Client.init_swarm`. An advertising
address needs to be provided, usually simply by indicating which network
interface needs to be used. Advanced options are provided using the
`swarm_spec` parameter, which can easily be created using
`Client.create_swarm_spec`.

```python
spec = client.create_swarm_spec(
  snapshot_interval=5000, log_entries_for_slow_followers=1200
)
client.init_swarm(
  advertise_addr='eth0', listen_addr='0.0.0.0:5000', force_new_cluster=False,
  swarm_spec=spec
)
```

## Joining an existing Swarm

If you're looking to have the engine your client is connected to join an
existing Swarm, this can be accomplished by using the `Client.join_swarm`
method. You will need to provide a list of at least one remote address
corresponding to other machines already part of the swarm as well as the
`join_token`. In most cases, a `listen_addr` and `advertise_addr` for your
node are also required.

```python
client.join_swarm(
  remote_addrs=['192.168.14.221:2377'], join_token='SWMTKN-1-redacted',
  listen_addr='0.0.0.0:5000', advertise_addr='eth0:5000'
)
```

## Leaving the Swarm

To leave the swarm you are currently a member of, simply use
`Client.leave_swarm`. Note that if your engine is the Swarm's manager,
you will need to specify `force=True` to be able to leave.

```python
client.leave_swarm(force=False)
```

## Retrieving Swarm status

You can retrieve information about your current Swarm status by calling
`Client.inspect_swarm`. This method takes no arguments.

```python
client.inspect_swarm()
```

## Listing Swarm nodes

List all nodes that are part of the current Swarm using `Client.nodes`.
The `filters` argument allows to filter the results.

```python
client.nodes(filters={'role': 'manager'})
```

## Swarm API documentation

### Client.init_swarm

Initialize a new Swarm using the current connected engine as the first node.

**Params:**

* advertise_addr (string): Externally reachable address advertised to other
  nodes. This can either be an address/port combination in the form
  `192.168.1.1:4567`, or an interface followed by a port number, like
  `eth0:4567`. If the port number is omitted, the port number from the listen
  address is used. If `advertise_addr` is not specified, it will be
  automatically detected when possible. Default: None
* listen_addr (string): Listen address used for inter-manager communication,
  as well as determining the networking interface used for the VXLAN Tunnel
  Endpoint (VTEP). This can either be an address/port combination in the form
  `192.168.1.1:4567`, or an interface followed by a port number, like
  `eth0:4567`. If the port number is omitted, the default swarm listening port
  is used. Default: '0.0.0.0:2377'
* force_new_cluster (bool): Force creating a new Swarm, even if already part of
  one. Default: False
* swarm_spec (dict): Configuration settings of the new Swarm. Use
  `Client.create_swarm_spec` to generate a valid configuration. Default: None

**Returns:** `True` if the request went through. Raises an `APIError` if it
  fails.

#### Client.create_swarm_spec

Create a `docker.types.SwarmSpec` instance that can be used as the `swarm_spec`
argument in `Client.init_swarm`.

**Params:**

* task_history_retention_limit (int): Maximum number of tasks history stored.
* snapshot_interval (int): Number of logs entries between snapshot.
* keep_old_snapshots (int): Number of snapshots to keep beyond the current
  snapshot.
* log_entries_for_slow_followers (int): Number of log entries to keep around
  to sync up slow followers after a snapshot is created.
* heartbeat_tick (int): Amount of ticks (in seconds) between each heartbeat.
* election_tick (int): Amount of ticks (in seconds) needed without a leader to
  trigger a new election.
* dispatcher_heartbeat_period (int):  The delay for an agent to send a
  heartbeat to the dispatcher.
* node_cert_expiry (int): Automatic expiry for nodes certificates.
* external_ca (dict): Configuration for forwarding signing requests to an
  external certificate authority. Use `docker.types.SwarmExternalCA`.
* name (string): Swarm's name

**Returns:** `docker.types.SwarmSpec` instance.

#### docker.types.SwarmExternalCA

Create a configuration dictionary for the `external_ca` argument in a
`SwarmSpec`.

**Params:**

* protocol (string): Protocol for communication with the external CA (currently
  only “cfssl” is supported).
* url (string): URL where certificate signing requests should be sent.
* options (dict): An object with key/value pairs that are interpreted as
  protocol-specific options for the external CA driver.

### Client.inspect_node

Retrieve low-level information about a Swarm node

**Params:**

* node_id (string): ID of the node to be inspected.

**Returns:** A dictionary containing data about this node. See sample below.

```python
{u'CreatedAt': u'2016-08-11T23:28:39.695834296Z',
 u'Description': {u'Engine': {u'EngineVersion': u'1.12.0',
   u'Plugins': [{u'Name': u'bridge', u'Type': u'Network'},
    {u'Name': u'host', u'Type': u'Network'},
    {u'Name': u'null', u'Type': u'Network'},
    {u'Name': u'overlay', u'Type': u'Network'},
    {u'Name': u'local', u'Type': u'Volume'}]},
  u'Hostname': u'dockerserv-1.local.net',
  u'Platform': {u'Architecture': u'x86_64', u'OS': u'linux'},
  u'Resources': {u'MemoryBytes': 8052109312, u'NanoCPUs': 4000000000}},
 u'ID': u'1kqami616p23dz4hd7km35w63',
 u'ManagerStatus': {u'Addr': u'10.0.131.127:2377',
  u'Leader': True,
  u'Reachability': u'reachable'},
 u'Spec': {u'Availability': u'active', u'Role': u'manager'},
 u'Status': {u'State': u'ready'},
 u'UpdatedAt': u'2016-08-11T23:28:39.979829529Z',
 u'Version': {u'Index': 9}}
 ```

### Client.inspect_swarm

Retrieve information about the current Swarm.

**Returns:** A dictionary containing information about the Swarm. See sample
  below.

```python
{u'CreatedAt': u'2016-08-04T21:26:18.779800579Z',
 u'ID': u'8hk6e9wh4iq214qtbgvbp84a9',
 u'JoinTokens': {u'Manager': u'SWMTKN-1-redacted-1',
  u'Worker': u'SWMTKN-1-redacted-2'},
 u'Spec': {u'CAConfig': {u'NodeCertExpiry': 7776000000000000},
  u'Dispatcher': {u'HeartbeatPeriod': 5000000000},
  u'Name': u'default',
  u'Orchestration': {u'TaskHistoryRetentionLimit': 10},
  u'Raft': {u'ElectionTick': 3,
   u'HeartbeatTick': 1,
   u'LogEntriesForSlowFollowers': 500,
   u'SnapshotInterval': 10000},
  u'TaskDefaults': {}},
 u'UpdatedAt': u'2016-08-04T21:26:19.391623265Z',
 u'Version': {u'Index': 11}}
```

### Client.join_swarm

Join an existing Swarm.

**Params:**

* remote_addrs (list): Addresses of one or more manager nodes already
  participating in the Swarm to join.
* join_token (string): Secret token for joining this Swarm.
* listen_addr (string): Listen address used for inter-manager communication
  if the node gets promoted to manager, as well as determining the networking
  interface used for the VXLAN Tunnel Endpoint (VTEP). Default: `None`
* advertise_addr (string): Externally reachable address advertised to other
  nodes. This can either be an address/port combination in the form
  `192.168.1.1:4567`, or an interface followed by a port number, like
  `eth0:4567`. If the port number is omitted, the port number from the listen
  address is used. If AdvertiseAddr is not specified, it will be automatically
  detected when possible. Default: `None`

**Returns:** `True` if the request went through. Raises an `APIError` if it
  fails.

### Client.leave_swarm

Leave a Swarm.

**Params:**

* force (bool): Leave the Swarm even if this node is a manager.
  Default: `False`

**Returns:** `True` if the request went through. Raises an `APIError` if it
  fails.

### Client.nodes

List Swarm nodes

**Params:**

* filters (dict): Filters to process on the nodes list. Valid filters:
  `id`, `name`, `membership` and `role`. Default: `None`

**Returns:** A list of dictionaries containing data about each swarm node.

### Client.update_node

Update the Node's configuration

**Params:**

* version (int): The version number of the node object being updated. This
  is required to avoid conflicting writes.
* node_spec (dict): Configuration settings to update.  Any values not provided 
  will be removed.  See the official [Docker API documentation](https://docs.docker.com/engine/reference/api/docker_remote_api_v1.24/#/update-a-node) for more details.
  Default: `None`.

**Returns:** `True` if the request went through. Raises an `APIError` if it
  fails.

```python
node_spec = {'Availability': 'active',
             'Name': 'node-name',
             'Role': 'manager',				   
             'Labels': {'foo': 'bar'}
            }
client.update_node(node_id='24ifsmvkjbyhk', version=8, node_spec=node_spec)
```

### Client.update_swarm

Update the Swarm's configuration

**Params:**

* version (int): The version number of the swarm object being updated. This
  is required to avoid conflicting writes.
* swarm_spec (dict): Configuration settings to update. Use
  `Client.create_swarm_spec` to generate a valid configuration.
  Default: `None`.
* rotate_worker_token (bool): Rotate the worker join token. Default: `False`.
* rotate_manager_token (bool): Rotate the manager join token. Default: `False`.

**Returns:** `True` if the request went through. Raises an `APIError` if it
  fails.
