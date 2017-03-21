import copy
from docker.errors import create_unexpected_kwargs_error
from docker.types import TaskTemplate, ContainerSpec
from .resource import Model, Collection


class Service(Model):
    """A service."""
    id_attribute = 'ID'

    @property
    def name(self):
        """The service's name."""
        return self.attrs['Spec']['Name']

    @property
    def version(self):
        """
        The version number of the service. If this is not the same as the
        server, the :py:meth:`update` function will not work and you will
        need to call :py:meth:`reload` before calling it again.
        """
        return self.attrs.get('Version').get('Index')

    def remove(self):
        """
        Stop and remove the service.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        return self.client.api.remove_service(self.id)

    def tasks(self, filters=None):
        """
        List the tasks in this service.

        Args:
            filters (dict): A map of filters to process on the tasks list.
                Valid filters: ``id``, ``name``, ``node``,
                ``label``, and ``desired-state``.

        Returns:
            (:py:class:`list`): List of task dictionaries.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        if filters is None:
            filters = {}
        filters['service'] = self.id
        return self.client.api.tasks(filters=filters)

    def update(self, **kwargs):
        """
        Update a service's configuration. Similar to the ``docker service
        update`` command.

        Takes the same parameters as :py:meth:`~ServiceCollection.create`.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        # Image is required, so if it hasn't been set, use current image
        if 'image' not in kwargs:
            spec = self.attrs['Spec']['TaskTemplate']['ContainerSpec']
            kwargs['image'] = spec['Image']

        create_kwargs = _get_create_service_kwargs('update', kwargs)

        return self.client.api.update_service(
            self.id,
            self.version,
            **create_kwargs
        )

    def logs(self, **kwargs):
        """
            Get log stream for the service.
            Note: This method works only for services with the ``json-file``
            or ``journald`` logging drivers.

            Args:
                details (bool): Show extra details provided to logs.
                    Default: ``False``
                follow (bool): Keep connection open to read logs as they are
                    sent by the Engine. Default: ``False``
                stdout (bool): Return logs from ``stdout``. Default: ``False``
                stderr (bool): Return logs from ``stderr``. Default: ``False``
                since (int): UNIX timestamp for the logs staring point.
                    Default: 0
                timestamps (bool): Add timestamps to every log line.
                tail (string or int): Number of log lines to be returned,
                    counting from the current end of the logs. Specify an
                    integer or ``'all'`` to output all log lines.
                    Default: ``all``

            Returns (generator): Logs for the service.
        """
        is_tty = self.attrs['Spec']['TaskTemplate']['ContainerSpec'].get(
            'TTY', False
        )
        return self.client.api.service_logs(self.id, is_tty=is_tty, **kwargs)


class ServiceCollection(Collection):
    """Services on the Docker server."""
    model = Service

    def create(self, image, command=None, **kwargs):
        """
        Create a service. Similar to the ``docker service create`` command.

        Args:
            image (str): The image name to use for the containers.
            command (list of str or str): Command to run.
            args (list of str): Arguments to the command.
            constraints (list of str): Placement constraints.
            container_labels (dict): Labels to apply to the container.
            endpoint_spec (EndpointSpec): Properties that can be configured to
                access and load balance a service. Default: ``None``.
            env (list of str): Environment variables, in the form
                ``KEY=val``.
            hostname (string): Hostname to set on the container.
            labels (dict): Labels to apply to the service.
            log_driver (str): Log driver to use for containers.
            log_driver_options (dict): Log driver options.
            mode (ServiceMode): Scheduling mode for the service.
                Default:``None``
            mounts (list of str): Mounts for the containers, in the form
                ``source:target:options``, where options is either
                ``ro`` or ``rw``.
            name (str): Name to give to the service.
            networks (list of str): List of network names or IDs to attach
                the service to. Default: ``None``.
            resources (Resources): Resource limits and reservations.
            restart_policy (RestartPolicy): Restart policy for containers.
            secrets (list of :py:class:`docker.types.SecretReference`): List
                of secrets accessible to containers for this service.
            stop_grace_period (int): Amount of time to wait for
                containers to terminate before forcefully killing them.
            update_config (UpdateConfig): Specification for the update strategy
                of the service. Default: ``None``
            user (str): User to run commands as.
            workdir (str): Working directory for commands to run.

        Returns:
            (:py:class:`Service`) The created service.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        kwargs['image'] = image
        kwargs['command'] = command
        create_kwargs = _get_create_service_kwargs('create', kwargs)
        service_id = self.client.api.create_service(**create_kwargs)
        return self.get(service_id)

    def get(self, service_id):
        """
        Get a service.

        Args:
            service_id (str): The ID of the service.

        Returns:
            (:py:class:`Service`): The service.

        Raises:
            :py:class:`docker.errors.NotFound`
                If the service does not exist.
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        return self.prepare_model(self.client.api.inspect_service(service_id))

    def list(self, **kwargs):
        """
        List services.

        Args:
            filters (dict): Filters to process on the nodes list. Valid
                filters: ``id`` and ``name``. Default: ``None``.

        Returns:
            (list of :py:class:`Service`): The services.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        return [
            self.prepare_model(s)
            for s in self.client.api.services(**kwargs)
        ]


# kwargs to copy straight over to ContainerSpec
CONTAINER_SPEC_KWARGS = [
    'image',
    'command',
    'args',
    'env',
    'hostname',
    'workdir',
    'user',
    'labels',
    'mounts',
    'stop_grace_period',
    'secrets',
]

# kwargs to copy straight over to TaskTemplate
TASK_TEMPLATE_KWARGS = [
    'resources',
    'restart_policy',
]

# kwargs to copy straight over to create_service
CREATE_SERVICE_KWARGS = [
    'name',
    'labels',
    'mode',
    'update_config',
    'networks',
    'endpoint_spec',
]


def _get_create_service_kwargs(func_name, kwargs):
    # Copy over things which can be copied directly
    create_kwargs = {}
    for key in copy.copy(kwargs):
        if key in CREATE_SERVICE_KWARGS:
            create_kwargs[key] = kwargs.pop(key)
    container_spec_kwargs = {}
    for key in copy.copy(kwargs):
        if key in CONTAINER_SPEC_KWARGS:
            container_spec_kwargs[key] = kwargs.pop(key)
    task_template_kwargs = {}
    for key in copy.copy(kwargs):
        if key in TASK_TEMPLATE_KWARGS:
            task_template_kwargs[key] = kwargs.pop(key)

    if 'container_labels' in kwargs:
        container_spec_kwargs['labels'] = kwargs.pop('container_labels')

    if 'constraints' in kwargs:
        task_template_kwargs['placement'] = {
            'Constraints': kwargs.pop('constraints')
        }

    if 'log_driver' in kwargs:
        task_template_kwargs['log_driver'] = {
            'Name': kwargs.pop('log_driver'),
            'Options': kwargs.pop('log_driver_options', {})
        }

    # All kwargs should have been consumed by this point, so raise
    # error if any are left
    if kwargs:
        raise create_unexpected_kwargs_error(func_name, kwargs)

    container_spec = ContainerSpec(**container_spec_kwargs)
    task_template_kwargs['container_spec'] = container_spec
    create_kwargs['task_template'] = TaskTemplate(**task_template_kwargs)
    return create_kwargs
