# Using Networks

With the release of Docker 1.9 you can now manage custom networks.


Here you can see how to create a network named ```network1``` using the ```bridge``` driver

```python
docker_client.create_network("network1", driver="bridge")
```

You can also create more advanced networks with custom IPAM configurations. For example, 
setting the subnet to ```192.168.52.0/24``` and gateway to ```192.168.52.254```

```python

ipam_config = docker.utils.create_ipam_config(subnet='192.168.52.0/24', gateway='192.168.52.254')

docker_client.create_network("network1", driver="bridge", ipam=ipam_config)
```
