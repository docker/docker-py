# Using swarm for API version 1.24 or higher

Swarm initialization is done in two parts.  Provide a listen_addr and `force_new_cluster` (OPTIONAL) to
the `Client().swarm_init()` method, and declare mappings in the
`swarm_opts` section.

```python
swarm_id = cli.swarm_init(listen_addr="0.0.0.0:4500", 
swarm_opts={
  "AcceptancePolicy": {
    "Policies": [
      {
        "Role": "MANAGER",
        "Autoaccept": True
      }
    ]
  }
})
```

Join another swarm, by providing the remote_address, listen_address(optional), 
secret(optional), ca_cert_hash(optional, manager(optional)
```python
cli.swarm_join(
    remote_address="swarm-master:2377",
    manager=True     
)
```


Leave swarm 

```python
cli.swarm_leave()
```
