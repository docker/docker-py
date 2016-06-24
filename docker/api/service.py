import six

from .. import errors
from .. import utils


class ServiceApiMixin(object):
    @utils.minimum_version('1.24')
    def services(self, filters=None):
        params = {
            'filters': utils.convert_filters(filters) if filters else None
        }
        url = self._url('/services')
        return self._result(self._get(url, params=params), True)

    @utils.minimum_version('1.24')
    def create_service(
            self, task_config, name=None, labels=None, mode=None,
            update_config=None, networks=None, endpoint_config=None
    ):
        url = self._url('/services/create')
        data = {
            'Name': name,
            'Labels': labels,
            'TaskTemplate': task_config,
            'Mode': mode,
            'UpdateConfig': update_config,
            'Networks': networks,
            'Endpoint': endpoint_config
        }
        return self._result(self._post_json(url, data=data), True)

    @utils.minimum_version('1.24')
    @utils.check_resource
    def inspect_service(self, service):
        url = self._url('/services/{0}', service)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.24')
    @utils.check_resource
    def remove_service(self, service):
        url = self._url('/services/{0}', service)
        resp = self._delete(url)
        self._raise_for_status(resp)

    @utils.minimum_version('1.24')
    @utils.check_resource
    def update_service(self, service, task_template=None, name=None,
                       labels=None, mode=None, update_config=None,
                       networks=None, endpoint_config=None):
        url = self._url('/services/{0}/update', service)
        data = {}
        if name is not None:
            data['Name'] = name
        if labels is not None:
            data['Labels'] = labels
        if mode is not None:
            data['Mode'] = mode
        if task_template is not None:
            data['TaskTemplate'] = task_template
        if update_config is not None:
            data['UpdateConfig'] = update_config
        if networks is not None:
            data['Networks'] = networks
        if endpoint_config is not None:
            data['Endpoint'] = endpoint_config

        return self._result(self._post_json(url, data=data), True)


class TaskTemplate(dict):
    def __init__(self, container_spec, resources=None, restart_policy=None,
                 placement=None, log_driver=None):
        self['ContainerSpec'] = container_spec
        if resources:
            self['Resources'] = resources
        if restart_policy:
            self['RestartPolicy'] = restart_policy
        if placement:
            self['Placement'] = placement
        if log_driver:
            self['LogDriver'] = log_driver

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
    def __init__(self, image, command=None, args=None, env=None, workdir=None,
                 user=None, labels=None, mounts=None, stop_grace_period=None):
        self['Image'] = image
        self['Command'] = command
        self['Args'] = args

        if env is not None:
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


class Mount(dict):
    def __init__(self, target, source, type='volume', read_only=False,
                 propagation=None, no_copy=False, labels=None,
                 driver_config=None):
        self['Target'] = target
        self['Source'] = source
        if type not in ('bind', 'volume'):
            raise errors.DockerError(
                'Only acceptable mount types are `bind` and `volume`.'
            )
        self['Type'] = type

        if type == 'bind':
            if propagation is not None:
                self['BindOptions'] = {
                    'Propagation': propagation
                }
            if any(labels, driver_config, no_copy):
                raise errors.DockerError(
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
                volume_opts['driver_config'] = driver_config
            if volume_opts:
                self['VolumeOptions'] = volume_opts
            if propagation:
                raise errors.DockerError(
                    'Mount type is volume but `propagation` argument has been '
                    'provided.'
                )

    @classmethod
    def parse_mount_string(cls, string):
        parts = string.split(':')
        if len(parts) > 3:
            raise errors.DockerError(
                'Invalid mount format "{0}"'.format(string)
            )
        if len(parts) == 1:
            return cls(target=parts[0])
        else:
            target = parts[1]
            source = parts[0]
            read_only = not (len(parts) == 3 or parts[2] == 'ro')
            return cls(target, source, read_only=read_only)


class Resources(dict):
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

        self['Limits'] = limits
        self['Reservation'] = reservation


class UpdateConfig(dict):
    def __init__(self, parallelism=0, delay=None, failure_action='continue'):
        self['Parallelism'] = parallelism
        if delay is not None:
            self['Delay'] = delay
        if failure_action not in ('pause', 'continue'):
            raise errors.DockerError(
                'failure_action must be either `pause` or `continue`.'
            )
        self['FailureAction'] = failure_action


class RestartConditionTypesEnum(object):
    _values = (
        'none',
        'on_failure',
        'any',
    )
    NONE, ON_FAILURE, ANY = _values


class RestartPolicy(dict):
    condition_types = RestartConditionTypesEnum

    def __init__(self, condition=RestartConditionTypesEnum.NONE, delay=0,
                 attempts=0, window=0):
        if condition not in self.condition_types._values:
            raise TypeError(
                'Invalid RestartPolicy condition {0}'.format(condition)
            )

        self['Condition'] = condition
        self['Delay'] = delay
        self['Attempts'] = attempts
        self['Window'] = window
