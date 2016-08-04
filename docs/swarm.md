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

If you're looking to have the engine your client is connected to joining an
existing Swarm, this ca be accomplished by using the `Client.join_swarm`
method. You will need to provide a list of at least one remote address
corresponding to other machines already part of the swarm. In most cases,
a `listen_address` for your node, as well as the `secret` token are required
to join too.

```python
client.join_swarm(
  remote_addresses=['192.168.14.221:2377'], secret='SWMTKN-1-redacted',
  listen_address='0.0.0.0:5000', manager=True
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

## Swarm API documentation

### Client.init_swarm

#### Client.create_swarm_spec

#### docker.utils.SwarmAcceptancePolicy

#### docker.utils.SwarmExternalCA

### Client.inspect_swarm

### Client.join_swarm

### CLient.leave_swarm