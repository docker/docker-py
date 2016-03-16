# Using tmpfs

When creating a container, you can specify paths to be mounted with tmpfs using
the `tmpfs` argument to `create_host_config`, similarly to the `--tmpfs`
argument to `docker run`.

This capability is supported in Docker Engine 1.10 and up.

`tmpfs` can be either a list or a dictionary. If it's a list, each item is a
string specifying the path and (optionally) any configuration for the mount:

```python
client.create_container(
    'busybox', 'ls',
    host_config=client.create_host_config(tmpfs=[
        '/mnt/vol2',
        '/mnt/vol1:size=3G,uid=1000'
    ])
)
```

Alternatively, if it's a dictionary, each key is a path and each value contains
the mount options:

```python
client.create_container(
    'busybox', 'ls',
    host_config=client.create_host_config(tmpfs={
        '/mnt/vol2': '',
        '/mnt/vol1': 'size=3G,uid=1000'
    })
)
```
