# Using volumes

Volume declaration is done in two parts. First, you have to provide
a list of mountpoints to the `Client().create_container()` method.

```python
container_id = c.create_container('busybox', 'ls', volumes=['/mnt/vol1', '/mnt/vol2'])
```

Volume mappings are then declared inside the `Client.start` method like this:

```python
c.start(container_id, binds={
    '/home/user1/':
        {
            'bind': '/mnt/vol2',
            'ro': False
        },
    '/var/www':
        {
            'bind': '/mnt/vol1',
            'ro': True
        }
})
```
