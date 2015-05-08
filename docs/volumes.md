# Using volumes

Volume declaration is done in two parts.  Provide a list of mountpoints to
the `Client().create_container()` method, and declare mappings in the
`host_config` section.

```python
container_id = c.create_container(
    'busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'],
    host_config=docker.utils.create_host_config(binds={
        '/home/user1/': {
            'bind': '/mnt/vol2',
            'ro': False
        },
        '/var/www': {
            'bind': '/mnt/vol1',
            'ro': True
        }
    })
)
```
