# Using Networks

## Network creation

With the release of Docker 1.9 you can now manage custom networks.


Here you can see how to create a network named `network1` using
the `bridge` driver

```python
docker_client.create_network("network1", driver="bridge")
```

You can also create more advanced networks with custom IPAM configurations.
For example, setting the subnet to `192.168.52.0/24` and gateway address
to `192.168.52.254`

```python
ipam_pool = docker.utils.create_ipam_pool(
    subnet='192.168.52.0/24',
    gateway='192.168.52.254'
)
ipam_config = docker.utils.create_ipam_config(
    pool_configs=[ipam_pool]
)

docker_client.create_network("network1", driver="bridge", ipam=ipam_config)
```

By default, when you connect a container to an overlay network, Docker also
connects a bridge network to it to provide external connectivity. If you want
to create an externally isolated overlay network, with Docker 1.10 you can
create an internal network.

```python

docker_client.create_network("network1", driver="bridge", internal=True)
```

## Container network configuration

In order to specify which network a container will be connected to, and
additional configuration, use the `networking_config` parameter in
`Client.create_container`. Note that at the time of creation, you can
only connect a container to a single network. Later on, you may create more
connections using `Client.connect_container_to_network`.


```python
networking_config = docker_client.create_networking_config({
    'network1': docker_client.create_endpoint_config(
        ipv4_address='172.28.0.124',
        aliases=['foo', 'bar'],
        links=['container2']
    )
})

ctnr = docker_client.create_container(
    img, command, networking_config=networking_config
)

```

## Network API documentation

### Client.create_networking_config

Create a networking config dictionary to be used as the `networking_config`
parameter in `Client.create_container_config`

**Params**:

* endpoints_config (dict): A dictionary of `network_name -> endpoint_config`
  relationships. Values should be endpoint config dictionaries created by
  `Client.create_endpoint_config`. Defaults to `None` (default config).

**Returns** A networking config dictionary.

```python

docker_client.create_network('network1')

networking_config = docker_client.create_networking_config({
    'network1': docker_client.create_endpoint_config()
})

container = docker_client.create_container(
    img, command, networking_config=networking_config
)
```


### Client.create_endpoint_config

Create an endpoint config dictionary to be used with
`Client.create_networking_config`.

**Params**:

* aliases (list): A list of aliases for this endpoint. Names in that list can
  be used within the network to reach the container. Defaults to `None`.
* links (list): A list of links for this endpoint. Containers declared in this
  list will be [linked](https://docs.docker.com/engine/userguide/networking/work-with-networks/#linking-containers-in-user-defined-networks)
  to this container. Defaults to `None`.
* ipv4_address (str): The IP address of this container on the network,
  using the IPv4 protocol. Defaults to `None`.
* ipv6_address (str): The IP address of this container on the network,
  using the IPv6 protocol. Defaults to `None`.
* link_local_ips (list): A list of link-local (IPv4/IPv6) addresses.

**Returns** An endpoint config dictionary.

```python
endpoint_config = docker_client.create_endpoint_config(
    aliases=['web', 'app'],
    links=['app_db'],
    ipv4_address='132.65.0.123'
)

docker_client.create_network('network1')
networking_config = docker_client.create_networking_config({
    'network1': endpoint_config
})
container = docker_client.create_container(
    img, command, networking_config=networking_config
)
```
### docker.utils.create_ipam_config

Create an IPAM (IP Address Management) config dictionary to be used with
`Client.create_network`.


**Params**:

* driver (str): The IPAM driver to use. Defaults to `'default'`.
* pool_configs (list): A list of pool configuration dictionaries as created
  by `docker.utils.create_ipam_pool`. Defaults to empty list.

**Returns** An IPAM config dictionary

```python
ipam_config = docker.utils.create_ipam_config(driver='default')
network = docker_client.create_network('network1', ipam=ipam_config)
```

### docker.utils.create_ipam_pool

Create an IPAM pool config dictionary to be added to the `pool_configs` param
in `docker.utils.create_ipam_config`.

**Params**:

* subnet (str): Custom subnet for this IPAM pool using the CIDR notation.
  Defaults to `None`.
* iprange (str): Custom IP range for endpoints in this IPAM pool using the
  CIDR notation. Defaults to `None`.
* gateway (str): Custom IP address for the pool's gateway.
* aux_addresses (dict): A dictionary of `key -> ip_address` relationships
  specifying auxiliary addresses that need to be allocated by the
  IPAM driver.

**Returns** An IPAM pool config dictionary

```python
ipam_pool = docker.utils.create_ipam_pool(
    subnet='124.42.0.0/16',
    iprange='124.42.0.0/24',
    gateway='124.42.0.254',
    aux_addresses={
        'reserved1': '124.42.1.1'
    }
)
ipam_config = docker.utils.create_ipam_config(pool_configs=[ipam_pool])
network = docker_client.create_network('network1', ipam=ipam_config)
```
