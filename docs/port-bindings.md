# Port bindings
Port bindings is done in two parts. Firstly, by providing a list of ports to
open inside the container in the `Client().create_container()` method.
Bindings are declared in the `host_config` parameter.

```python
container_id = cli.create_container(
    'busybox', 'ls', ports=[1111, 2222],
    host_config=cli.create_host_config(port_bindings={
        1111: 4567,
        2222: None
    })
)
```


You can limit the host address on which the port will be exposed like such:

```python
cli.create_host_config(port_bindings={1111: ('127.0.0.1', 4567)})
```

Or without host port assignment:

```python
cli.create_host_config(port_bindings={1111: ('127.0.0.1',)})
```

If you wish to use UDP instead of TCP (default), you need to declare ports
as such in both the config and host config:

```python
container_id = cli.create_container(
	'busybox', 'ls', ports=[(1111, 'udp'), 2222],
    host_config=cli.create_host_config(port_bindings={
        '1111/udp': 4567, 2222: None
    })
)
```
