# Using Tmpfs

Tmpfs declaration is done with the `Client().create_container()`
method by declaring the mountpoints in the `host_config` section.

This is available from docker 1.10.

You can provide a list of declarations similar to the `--tmpfs`
option of the docker commandline client:

```python
container_id = cli.create_container(
    'busybox', 'ls',
    host_config=cli.create_host_config(tmpfs=[
        '/mnt/vol2',
        '/mnt/vol1:size=3G,uid=1000'
    ])
)
```

You can alternatively specify tmpfs as a dict the docker remote
API uses:

```python
container_id = cli.create_container(
    'busybox', 'ls',
    host_config=cli.create_host_config(tmpfs={
        '/mnt/vol2': '',
        '/mnt/vol1': 'size=3G,uid=1000'
    })
)
```
