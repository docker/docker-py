# Port bindings
Port bindings is done in two parts. Firstly, by providing a list of ports to
open inside the container in the `Client().create_container()` method.

```python
container_id = c.create_container('busybox', 'ls', ports=[1111, 2222])
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

If you wish to use UDP instead of TCP (default), you need to declare it
like such in both the `create_container()` and `start()` calls:

```python
container_id = c.create_container(
	'busybox',
	'ls',
	ports=[(1111, 'udp'), 2222]
)
c.start(container_id, port_bindings={'1111/udp': 4567, 2222: None})
```

