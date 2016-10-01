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

Create a service.

**Params:**

* task_template (dict): Specification of the task to start as part of the new
  service. See the [TaskTemplate class](#TaskTemplate) for details.
* name (string): User-defined name for the service. Optional.
* labels (dict): A map of labels to associate with the service. Optional.
* mode (string): Scheduling mode for the service (`replicated` or `global`).
  Defaults to `replicated`.
* update_config (dict): Specification for the update strategy of the service.
  See the [UpdateConfig class](#UpdateConfig) for details. Default: `None`.
* networks (list): List of network names or IDs to attach the service to.
  Default: `None`.
* endpoint_spec (dict): Properties that can be configured to access and load
  balance a service. Default: `None`.

**Returns:** A dictionary containing an `ID` key for the newly created service.

### Client.inspect_service

Return information on a service.

**Params:**

* service (string): A service identifier (either its name or service ID)

**Returns:** `True` if successful. Raises an `APIError` otherwise.

### Client.remove_service

Stop and remove a service.

**Params:**

* service (string): A service identifier (either its name or service ID)

**Returns:** `True` if successful. Raises an `APIError` otherwise.

### Client.services

List services.

**Params:**

* filters (dict): Filters to process on the nodes list. Valid filters:
  `id` and `name`. Default: `None`.

**Returns:** A list of dictionaries containing data about each service.

### Client.update_service

Update a service.

**Params:**

* service (string): A service identifier (either its name or service ID).
* version (int): The version number of the service object being updated. This
  is required to avoid conflicting writes.
* task_template (dict): Specification of the updated task to start as part of
  the service. See the [TaskTemplate class](#TaskTemplate) for details.
* name (string): New name for the service. Optional.
* labels (dict): A map of labels to associate with the service. Optional.
* mode (string): Scheduling mode for the service (`replicated` or `global`).
  Defaults to `replicated`.
* update_config (dict): Specification for the update strategy of the service.
  See the [UpdateConfig class](#UpdateConfig) for details. Default: `None`.
* networks (list): List of network names or IDs to attach the service to.
  Default: `None`.
* endpoint_spec (dict): Properties that can be configured to access and load
  balance a service. Default: `None`.

**Returns:** `True` if successful. Raises an `APIError` otherwise.

### Configuration objects (`docker.types`)

#### ContainerSpec

A `ContainerSpec` object describes the behavior of containers that are part
of a task, and is used when declaring a `TaskTemplate`.

**Params:**

* image (string): The image name to use for the container.
* command (string or list):  The command to be run in the image.
* args (list): Arguments to the command.
* env (dict): Environment variables.
* dir (string): The working directory for commands to run in.
* user (string): The user inside the container.
* labels (dict): A map of labels to associate with the service.
* mounts (list): A list of specifications for mounts to be added to containers
  created as part of the service. See the [Mount class](#Mount) for details.
* stop_grace_period (int): Amount of time to wait for the container to
  terminate before forcefully killing it.

#### DriverConfig

A `LogDriver` object indicates which driver to use, as well as its
configuration. It can be used for the `log_driver` in a `ContainerSpec`,
and for the `driver_config` in a volume `Mount`.

**Params:**

* name (string): Name of the logging driver to use.
* options (dict): Driver-specific options. Default: `None`.

#### EndpointSpec

An `EndpointSpec` object describes properties to access and load-balance a
service.

**Params:**

* mode (string): The mode of resolution to use for internal load balancing
  between tasks (`'vip'` or `'dnsrr'`). Defaults to `'vip'` if not provided.
* ports (dict): Exposed ports that this service is accessible on from the
  outside, in the form of `{ target_port: published_port }` or
  `{ target_port: (published_port, protocol) }`. Ports can only be provided if
  the `vip` resolution mode is used.

#### Mount

A `Mount` object describes a mounted folder's configuration inside a
container. A list of `Mount`s would be used as part of a `ContainerSpec`.

* target (string): Container path.
* source (string): Mount source (e.g. a volume name or a host path).
* type (string): The mount type (`bind` or `volume`). Default: `volume`.
* read_only (bool): Whether the mount should be read-only.
* propagation (string): A propagation mode with the value `[r]private`,
  `[r]shared`, or `[r]slave`. Only valid for the `bind` type.
* no_copy (bool): False if the volume should be populated with the data from
  the target. Default: `False`. Only valid for the `volume` type.
* labels (dict): User-defined name and labels for the volume. Only valid for
  the `volume` type.
* driver_config (dict): Volume driver configuration.
  See the [DriverConfig class](#DriverConfig) for details. Only valid for the
  `volume` type.

#### Resources

A `Resources` object configures resource allocation for containers when
made part of a `ContainerSpec`.

**Params:**

* cpu_limit (int): CPU limit in units of 10^9 CPU shares.
* mem_limit (int): Memory limit in Bytes.
* cpu_reservation (int): CPU reservation in units of 10^9 CPU shares.
* mem_reservation (int): Memory reservation in Bytes.

#### RestartPolicy

A `RestartPolicy` object is used when creating a `ContainerSpec`. It dictates
whether a container should restart after stopping or failing.

* condition (string): Condition for restart (`none`, `on-failure`, or `any`).
  Default: `none`.
* delay (int): Delay between restart attempts. Default: 0
* attempts (int): Maximum attempts to restart a given container before giving
  up. Default value is 0, which is ignored.
* window (int): Time window used to evaluate the restart policy. Default value
  is 0, which is unbounded.


#### TaskTemplate

A `TaskTemplate` object can be used to describe the task specification to be
used when creating or updating a service.

**Params:**

* container_spec (dict): Container settings for containers started as part of
  this task. See the [ContainerSpec class](#ContainerSpec) for details.
* log_driver (dict): Log configuration for containers created as part of the
  service. See the [DriverConfig class](#DriverConfig) for details.
* resources (dict): Resource requirements which apply to each individual
  container created as part of the service. See the
  [Resources class](#Resources) for details.
* restart_policy (dict): Specification for the restart policy which applies
  to containers created as part of this service. See the
  [RestartPolicy class](#RestartPolicy) for details.
* placement (list): A list of constraints.


#### UpdateConfig

An `UpdateConfig` object can be used to specify the way container updates
should be performed by a service.

**Params:**

* parallelism (int): Maximum number of tasks to be updated in one iteration
  (0 means unlimited parallelism). Default: 0.
* delay (int): Amount of time between updates.
* failure_action (string): Action to take if an updated task fails to run, or
  stops running during the update. Acceptable values are `continue` and
  `pause`. Default: `continue`
