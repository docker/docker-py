# Using volumes

Volume declaration is done in two parts.  Provide a list of mountpoints to
the `Client().create_container()` method, and declare mappings in the
`host_config` section.

```python
container_id = cli.create_container(
    'busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'],
    host_config=cli.create_host_config(binds={
        '/home/user1/': {
            'bind': '/mnt/vol2',
            'mode': 'rw',
        },
        '/var/www': {
            'bind': '/mnt/vol1',
            'mode': 'ro',
        }
    })
)
```

You can alternatively specify binds as a list. This code is equivalent to the
example above:

```python
container_id = cli.create_container(
    'busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'],
    host_config=cli.create_host_config(binds=[
        '/home/user1/:/mnt/vol2',
        '/var/www:/mnt/vol1:ro',
    ])
)
```
