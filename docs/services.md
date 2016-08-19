# Swarm services

Starting with Engine version 1.12 (API 1.24), it is possible to manage services
using the Docker Engine API. Note that the engine needs to be part of a
[Swarm cluster](swarm.md) before you can use the service-related methods.

## Creating a service

The `Client.create_service` method lets you create a new service inside the
cluster. The method takes several arguments, `task_template` being mandatory.
This dictionary of values is most easily produced by instantiating a
`TaskTemplate` object.

```python
container_spec = docker.types.ContainerSpec(
    image='busybox', command=['echo', 'hello']
)
task_tmpl = docker.types.TaskTemplate(container_spec)
service_id = client.create_service(task_tmpl, name=name)
```

## Listing services

List all existing services using the `Client.services` method.

```python
client.services(filters={'name': 'mysql'})
```

## Retrieving service configuration

To retrieve detailed information and configuration for a specific service, you
may use the `Client.inspect_service` method using the service's ID or name.

```python
client.inspect_service(service='my_service_name')
```

## Updating service configuration

The `Client.update_service` method lets you update a service's configuration.
The mandatory `version` argument (used to prevent concurrent writes) can be
retrieved using `Client.inspect_service`.

```python
container_spec = docker.types.ContainerSpec(
    image='busybox', command=['echo', 'hello world']
)
task_tmpl = docker.types.TaskTemplate(container_spec)

svc_version = client.inspect_service(svc_id)['Version']['Index']

client.update_service(
    svc_id, svc_version, name='new_name', task_template=task_tmpl
)
```

## Removing a service

A service may be removed simply using the `Client.remove_service` method.
Either the service name or service ID can be used as argument.

```python
client.remove_service('my_service_name')
```

## Service API documentation

### Client.create_service

### Client.inspect_service

### Client.remove_service

### Client.services

### Client.update_service

### Configuration objects (`docker.types`)

#### ContainerSpec

#### LogDriver

#### Mount

#### Resources

#### RestartPolicy

#### TaskTemplate

#### UpdateConfig
