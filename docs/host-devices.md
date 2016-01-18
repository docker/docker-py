# Access to devices on the host

If you need to directly expose some host devices to a container, you can use
the devices parameter in the `host_config` param in `Client.create_container`
as shown below:

```python
cli.create_container(
    'busybox', 'true', host_config=cli.create_host_config(devices=[
        '/dev/sda:/dev/xvda:rwm'
    ])
)
```

Each string is a single mapping using the following format:
`<path_on_host>:<path_in_container>:<cgroup_permissions>`
The above example allows the container to have read-write access to
the host's `/dev/sda` via a node named `/dev/xvda` inside the container.

As a more verbose alternative, each host device definition can be specified as
a dictionary with the following keys:

```python
{
    'PathOnHost': '/dev/sda1',
    'PathInContainer': '/dev/xvda',
    'CgroupPermissions': 'rwm'
}
```
