import six

from .. import errors
from ..constants import IS_WINDOWS_PLATFORM
from ..utils import check_resource, format_environment, split_command


class TaskTemplate(dict):
    """
    Describe the task specification to be used when creating or updating a
    service.

    Args:

        container_spec (ContainerSpec): Container settings for containers
          started as part of this task.
        log_driver (DriverConfig): Log configuration for containers created as
          part of the service.
        resources (Resources): Resource requirements which apply to each
          individual container created as part of the service.
        restart_policy (RestartPolicy): Specification for the restart policy
          which applies to containers created as part of this service.
        placement (:py:class:`list`): A list of constraints.
        force_update (int): A counter that triggers an update even if no
            relevant parameters have been changed.
    """
    def __init__(self, container_spec, resources=None, restart_policy=None,
                 placement=None, log_driver=None, force_update=None):
        self['ContainerSpec'] = container_spec
        if resources:
            self['Resources'] = resources
        if restart_policy:
            self['RestartPolicy'] = restart_policy
        if placement:
            if isinstance(placement, list):
                placement = {'Constraints': placement}
            self['Placement'] = placement
        if log_driver:
            self['LogDriver'] = log_driver

        if force_update is not None:
            if not isinstance(force_update, int):
                raise TypeError('force_update must be an integer')
            self['ForceUpdate'] = force_update

    @property
    def container_spec(self):
        return self.get('ContainerSpec')

    @property
    def resources(self):
        return self.get('Resources')

    @property
    def restart_policy(self):
        return self.get('RestartPolicy')

    @property
    def placement(self):
        return self.get('Placement')


class ContainerSpec(dict):
    """
    Describes the behavior of containers that are part of a task, and is used
    when declaring a :py:class:`~docker.types.TaskTemplate`.

    Args:

        image (string): The image name to use for the container.
        command (string or list):  The command to be run in the image.
        args (:py:class:`list`): Arguments to the command.
        hostname (string): The hostname to set on the container.
        env (dict): Environment variables.
        dir (string): The working directory for commands to run in.
        user (string): The user inside the container.
        labels (dict): A map of labels to associate with the service.
        mounts (:py:class:`list`): A list of specifications for mounts to be
            added to containers created as part of the service. See the
            :py:class:`~docker.types.Mount` class for details.
        stop_grace_period (int): Amount of time to wait for the container to
            terminate before forcefully killing it.
        secrets (list of py:class:`SecretReference`): List of secrets to be
            made available inside the containers.
    """
    def __init__(self, image, command=None, args=None, hostname=None, env=None,
                 workdir=None, user=None, labels=None, mounts=None,
                 stop_grace_period=None, secrets=None):
        self['Image'] = image

        if isinstance(command, six.string_types):
            command = split_command(command)
        self['Command'] = command
        self['Args'] = args

        if hostname is not None:
            self['Hostname'] = hostname
        if env is not None:
            if isinstance(env, dict):
                self['Env'] = format_environment(env)
            else:
                self['Env'] = env
        if workdir is not None:
            self['Dir'] = workdir
        if user is not None:
            self['User'] = user
        if labels is not None:
            self['Labels'] = labels
        if mounts is not None:
            for mount in mounts:
                if isinstance(mount, six.string_types):
                    mounts.append(Mount.parse_mount_string(mount))
                    mounts.remove(mount)
            self['Mounts'] = mounts
        if stop_grace_period is not None:
            self['StopGracePeriod'] = stop_grace_period

        if secrets is not None:
            if not isinstance(secrets, list):
                raise TypeError('secrets must be a list')
            self['Secrets'] = secrets


class Mount(dict):
    """
    Describes a mounted folder's configuration inside a container. A list of
    :py:class:`Mount`s would be used as part of a
    :py:class:`~docker.types.ContainerSpec`.

    Args:

        target (string): Container path.
        source (string): Mount source (e.g. a volume name or a host path).
        type (string): The mount type (``bind`` or ``volume``).
          Default: ``volume``.
        read_only (bool): Whether the mount should be read-only.
        propagation (string): A propagation mode with the value ``[r]private``,
          ``[r]shared``, or ``[r]slave``. Only valid for the ``bind`` type.
        no_copy (bool): False if the volume should be populated with the data
          from the target. Default: ``False``. Only valid for the ``volume``
          type.
        labels (dict): User-defined name and labels for the volume. Only valid
          for the ``volume`` type.
        driver_config (DriverConfig): Volume driver configuration. Only valid
          for the ``volume`` type.
    """
    def __init__(self, target, source, type='volume', read_only=False,
                 propagation=None, no_copy=False, labels=None,
                 driver_config=None):
        self['Target'] = target
        self['Source'] = source
        if type not in ('bind', 'volume'):
            raise errors.InvalidArgument(
                'Only acceptable mount types are `bind` and `volume`.'
            )
        self['Type'] = type
        self['ReadOnly'] = read_only

        if type == 'bind':
            if propagation is not None:
                self['BindOptions'] = {
                    'Propagation': propagation
                }
            if any([labels, driver_config, no_copy]):
                raise errors.InvalidArgument(
                    'Mount type is binding but volume options have been '
                    'provided.'
                )
        else:
            volume_opts = {}
            if no_copy:
                volume_opts['NoCopy'] = True
            if labels:
                volume_opts['Labels'] = labels
            if driver_config:
                volume_opts['DriverConfig'] = driver_config
            if volume_opts:
                self['VolumeOptions'] = volume_opts
            if propagation:
                raise errors.InvalidArgument(
                    'Mount type is volume but `propagation` argument has been '
                    'provided.'
                )

    @classmethod
    def parse_mount_string(cls, string):
        parts = string.split(':')
        if len(parts) > 3:
            raise errors.InvalidArgument(
                'Invalid mount format "{0}"'.format(string)
            )
        if len(parts) == 1:
            return cls(target=parts[0], source=None)
        else:
            target = parts[1]
            source = parts[0]
            mount_type = 'volume'
            if source.startswith('/') or (
                IS_WINDOWS_PLATFORM and source[0].isalpha() and
                source[1] == ':'
            ):
                # FIXME: That windows condition will fail earlier since we
                # split on ':'. We should look into doing a smarter split
                # if we detect we are on Windows.
                mount_type = 'bind'
            read_only = not (len(parts) == 2 or parts[2] == 'rw')
            return cls(target, source, read_only=read_only, type=mount_type)


class Resources(dict):
    """
    Configures resource allocation for containers when made part of a
    :py:class:`~docker.types.ContainerSpec`.

    Args:

        cpu_limit (int): CPU limit in units of 10^9 CPU shares.
        mem_limit (int): Memory limit in Bytes.
        cpu_reservation (int): CPU reservation in units of 10^9 CPU shares.
        mem_reservation (int): Memory reservation in Bytes.
    """
    def __init__(self, cpu_limit=None, mem_limit=None, cpu_reservation=None,
                 mem_reservation=None):
        limits = {}
        reservation = {}
        if cpu_limit is not None:
            limits['NanoCPUs'] = cpu_limit
        if mem_limit is not None:
            limits['MemoryBytes'] = mem_limit
        if cpu_reservation is not None:
            reservation['NanoCPUs'] = cpu_reservation
        if mem_reservation is not None:
            reservation['MemoryBytes'] = mem_reservation

        if limits:
            self['Limits'] = limits
        if reservation:
            self['Reservations'] = reservation


class UpdateConfig(dict):
    """

    Used to specify the way container updates should be performed by a service.

    Args:

        parallelism (int): Maximum number of tasks to be updated in one
          iteration (0 means unlimited parallelism). Default: 0.
        delay (int): Amount of time between updates.
        failure_action (string): Action to take if an updated task fails to
          run, or stops running during the update. Acceptable values are
          ``continue`` and ``pause``. Default: ``continue``
        monitor (int): Amount of time to monitor each updated task for
          failures, in nanoseconds.
        max_failure_ratio (float): The fraction of tasks that may fail during
          an update before the failure action is invoked, specified as a
          floating point number between 0 and 1. Default: 0
    """
    def __init__(self, parallelism=0, delay=None, failure_action='continue',
                 monitor=None, max_failure_ratio=None):
        self['Parallelism'] = parallelism
        if delay is not None:
            self['Delay'] = delay
        if failure_action not in ('pause', 'continue'):
            raise errors.InvalidArgument(
                'failure_action must be either `pause` or `continue`.'
            )
        self['FailureAction'] = failure_action

        if monitor is not None:
            if not isinstance(monitor, int):
                raise TypeError('monitor must be an integer')
            self['Monitor'] = monitor

        if max_failure_ratio is not None:
            if not isinstance(max_failure_ratio, (float, int)):
                raise TypeError('max_failure_ratio must be a float')
            if max_failure_ratio > 1 or max_failure_ratio < 0:
                raise errors.InvalidArgument(
                    'max_failure_ratio must be a number between 0 and 1'
                )
            self['MaxFailureRatio'] = max_failure_ratio


class RestartConditionTypesEnum(object):
    _values = (
        'none',
        'on-failure',
        'any',
    )
    NONE, ON_FAILURE, ANY = _values


class RestartPolicy(dict):
    """
    Used when creating a :py:class:`~docker.types.ContainerSpec`,
    dictates whether a container should restart after stopping or failing.

    Args:

        condition (string): Condition for restart (``none``, ``on-failure``,
          or ``any``). Default: `none`.
        delay (int): Delay between restart attempts. Default: 0
        attempts (int): Maximum attempts to restart a given container before
          giving up. Default value is 0, which is ignored.
        window (int): Time window used to evaluate the restart policy. Default
          value is 0, which is unbounded.
    """

    condition_types = RestartConditionTypesEnum

    def __init__(self, condition=RestartConditionTypesEnum.NONE, delay=0,
                 max_attempts=0, window=0):
        if condition not in self.condition_types._values:
            raise TypeError(
                'Invalid RestartPolicy condition {0}'.format(condition)
            )

        self['Condition'] = condition
        self['Delay'] = delay
        self['MaxAttempts'] = max_attempts
        self['Window'] = window


class DriverConfig(dict):
    """
    Indicates which driver to use, as well as its configuration. Can be used
    as ``log_driver`` in a :py:class:`~docker.types.ContainerSpec`,
    and for the `driver_config` in a volume
    :py:class:`~docker.types.Mount`.

    Args:

        name (string): Name of the driver to use.
        options (dict): Driver-specific options. Default: ``None``.
    """
    def __init__(self, name, options=None):
        self['Name'] = name
        if options:
            self['Options'] = options


class EndpointSpec(dict):
    """
    Describes properties to access and load-balance a service.

    Args:

        mode (string): The mode of resolution to use for internal load
          balancing between tasks (``'vip'`` or ``'dnsrr'``). Defaults to
          ``'vip'`` if not provided.
        ports (dict): Exposed ports that this service is accessible on from the
          outside, in the form of ``{ target_port: published_port }`` or
          ``{ target_port: (published_port, protocol) }``. Ports can only be
          provided if the ``vip`` resolution mode is used.
    """
    def __init__(self, mode=None, ports=None):
        if ports:
            self['Ports'] = convert_service_ports(ports)
        if mode:
            self['Mode'] = mode


def convert_service_ports(ports):
    if isinstance(ports, list):
        return ports
    if not isinstance(ports, dict):
        raise TypeError(
            'Invalid type for ports, expected dict or list'
        )

    result = []
    for k, v in six.iteritems(ports):
        port_spec = {
            'Protocol': 'tcp',
            'PublishedPort': k
        }

        if isinstance(v, tuple):
            port_spec['TargetPort'] = v[0]
            if len(v) == 2:
                port_spec['Protocol'] = v[1]
        else:
            port_spec['TargetPort'] = v

        result.append(port_spec)
    return result


class ServiceMode(dict):
    """
        Indicate whether a service should be deployed as a replicated or global
        service, and associated parameters

        Args:
            mode (string): Can be either ``replicated`` or ``global``
            replicas (int): Number of replicas. For replicated services only.
    """
    def __init__(self, mode, replicas=None):
        if mode not in ('replicated', 'global'):
            raise errors.InvalidArgument(
                'mode must be either "replicated" or "global"'
            )
        if mode != 'replicated' and replicas is not None:
            raise errors.InvalidArgument(
                'replicas can only be used for replicated mode'
            )
        self[mode] = {}
        if replicas:
            self[mode]['Replicas'] = replicas

    @property
    def mode(self):
        if 'global' in self:
            return 'global'
        return 'replicated'

    @property
    def replicas(self):
        if self.mode != 'replicated':
            return None
        return self['replicated'].get('Replicas')


class SecretReference(dict):
    """
        Secret reference to be used as part of a :py:class:`ContainerSpec`.
        Describes how a secret is made accessible inside the service's
        containers.

        Args:
            secret_id (string): Secret's ID
            secret_name (string): Secret's name as defined at its creation.
            filename (string): Name of the file containing the secret. Defaults
                to the secret's name if not specified.
            uid (string): UID of the secret file's owner. Default: 0
            gid (string): GID of the secret file's group. Default: 0
            mode (int): File access mode inside the container. Default: 0o444
    """
    @check_resource
    def __init__(self, secret_id, secret_name, filename=None, uid=None,
                 gid=None, mode=0o444):
        self['SecretName'] = secret_name
        self['SecretID'] = secret_id
        self['File'] = {
            'Name': filename or secret_name,
            'UID': uid or '0',
            'GID': gid or '0',
            'Mode': mode
        }
