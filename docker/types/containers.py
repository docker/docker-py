import six
import warnings

from .. import errors
from ..utils.utils import (
    convert_port_bindings, convert_tmpfs_mounts, convert_volume_binds,
    format_environment, format_extra_hosts, normalize_links, parse_bytes,
    parse_devices, split_command, version_gte, version_lt,
)
from .base import DictType
from .healthcheck import Healthcheck


class LogConfigTypesEnum(object):
    _values = (
        'json-file',
        'syslog',
        'journald',
        'gelf',
        'fluentd',
        'none'
    )
    JSON, SYSLOG, JOURNALD, GELF, FLUENTD, NONE = _values


class LogConfig(DictType):
    types = LogConfigTypesEnum

    def __init__(self, **kwargs):
        log_driver_type = kwargs.get('type', kwargs.get('Type'))
        config = kwargs.get('config', kwargs.get('Config')) or {}

        if config and not isinstance(config, dict):
            raise ValueError("LogConfig.config must be a dictionary")

        super(LogConfig, self).__init__({
            'Type': log_driver_type,
            'Config': config
        })

    @property
    def type(self):
        return self['Type']

    @type.setter
    def type(self, value):
        self['Type'] = value

    @property
    def config(self):
        return self['Config']

    def set_config_value(self, key, value):
        self.config[key] = value

    def unset_config(self, key):
        if key in self.config:
            del self.config[key]


class Ulimit(DictType):
    def __init__(self, **kwargs):
        name = kwargs.get('name', kwargs.get('Name'))
        soft = kwargs.get('soft', kwargs.get('Soft'))
        hard = kwargs.get('hard', kwargs.get('Hard'))
        if not isinstance(name, six.string_types):
            raise ValueError("Ulimit.name must be a string")
        if soft and not isinstance(soft, int):
            raise ValueError("Ulimit.soft must be an integer")
        if hard and not isinstance(hard, int):
            raise ValueError("Ulimit.hard must be an integer")
        super(Ulimit, self).__init__({
            'Name': name,
            'Soft': soft,
            'Hard': hard
        })

    @property
    def name(self):
        return self['Name']

    @name.setter
    def name(self, value):
        self['Name'] = value

    @property
    def soft(self):
        return self.get('Soft')

    @soft.setter
    def soft(self, value):
        self['Soft'] = value

    @property
    def hard(self):
        return self.get('Hard')

    @hard.setter
    def hard(self, value):
        self['Hard'] = value


class HostConfig(dict):
    def __init__(self, version, binds=None, port_bindings=None,
                 lxc_conf=None, publish_all_ports=False, links=None,
                 privileged=False, dns=None, dns_search=None,
                 volumes_from=None, network_mode=None, restart_policy=None,
                 cap_add=None, cap_drop=None, devices=None, extra_hosts=None,
                 read_only=None, pid_mode=None, ipc_mode=None,
                 security_opt=None, ulimits=None, log_config=None,
                 mem_limit=None, memswap_limit=None, mem_reservation=None,
                 kernel_memory=None, mem_swappiness=None, cgroup_parent=None,
                 group_add=None, cpu_quota=None, cpu_period=None,
                 blkio_weight=None, blkio_weight_device=None,
                 device_read_bps=None, device_write_bps=None,
                 device_read_iops=None, device_write_iops=None,
                 oom_kill_disable=False, shm_size=None, sysctls=None,
                 tmpfs=None, oom_score_adj=None, dns_opt=None, cpu_shares=None,
                 cpuset_cpus=None, userns_mode=None, pids_limit=None,
                 isolation=None, auto_remove=False, storage_opt=None,
                 init=None, init_path=None, volume_driver=None,
                 cpu_count=None, cpu_percent=None, nano_cpus=None,
                 cpuset_mems=None, runtime=None, mounts=None):

        if mem_limit is not None:
            self['Memory'] = parse_bytes(mem_limit)

        if memswap_limit is not None:
            self['MemorySwap'] = parse_bytes(memswap_limit)

        if mem_reservation:
            if version_lt(version, '1.21'):
                raise host_config_version_error('mem_reservation', '1.21')

            self['MemoryReservation'] = parse_bytes(mem_reservation)

        if kernel_memory:
            if version_lt(version, '1.21'):
                raise host_config_version_error('kernel_memory', '1.21')

            self['KernelMemory'] = parse_bytes(kernel_memory)

        if mem_swappiness is not None:
            if version_lt(version, '1.20'):
                raise host_config_version_error('mem_swappiness', '1.20')
            if not isinstance(mem_swappiness, int):
                raise host_config_type_error(
                    'mem_swappiness', mem_swappiness, 'int'
                )

            self['MemorySwappiness'] = mem_swappiness

        if shm_size is not None:
            if isinstance(shm_size, six.string_types):
                shm_size = parse_bytes(shm_size)

            self['ShmSize'] = shm_size

        if pid_mode:
            if version_lt(version, '1.24') and pid_mode != 'host':
                raise host_config_value_error('pid_mode', pid_mode)
            self['PidMode'] = pid_mode

        if ipc_mode:
            self['IpcMode'] = ipc_mode

        if privileged:
            self['Privileged'] = privileged

        if oom_kill_disable:
            if version_lt(version, '1.20'):
                raise host_config_version_error('oom_kill_disable', '1.19')

            self['OomKillDisable'] = oom_kill_disable

        if oom_score_adj:
            if version_lt(version, '1.22'):
                raise host_config_version_error('oom_score_adj', '1.22')
            if not isinstance(oom_score_adj, int):
                raise host_config_type_error(
                    'oom_score_adj', oom_score_adj, 'int'
                )
            self['OomScoreAdj'] = oom_score_adj

        if publish_all_ports:
            self['PublishAllPorts'] = publish_all_ports

        if read_only is not None:
            self['ReadonlyRootfs'] = read_only

        if dns_search:
            self['DnsSearch'] = dns_search

        if network_mode:
            self['NetworkMode'] = network_mode
        elif network_mode is None and version_gte(version, '1.20'):
            self['NetworkMode'] = 'default'

        if restart_policy:
            if not isinstance(restart_policy, dict):
                raise host_config_type_error(
                    'restart_policy', restart_policy, 'dict'
                )

            self['RestartPolicy'] = restart_policy

        if cap_add:
            self['CapAdd'] = cap_add

        if cap_drop:
            self['CapDrop'] = cap_drop

        if devices:
            self['Devices'] = parse_devices(devices)

        if group_add:
            if version_lt(version, '1.20'):
                raise host_config_version_error('group_add', '1.20')

            self['GroupAdd'] = [six.text_type(grp) for grp in group_add]

        if dns is not None:
            self['Dns'] = dns

        if dns_opt is not None:
            if version_lt(version, '1.21'):
                raise host_config_version_error('dns_opt', '1.21')

            self['DnsOptions'] = dns_opt

        if security_opt is not None:
            if not isinstance(security_opt, list):
                raise host_config_type_error(
                    'security_opt', security_opt, 'list'
                )

            self['SecurityOpt'] = security_opt

        if sysctls:
            if not isinstance(sysctls, dict):
                raise host_config_type_error('sysctls', sysctls, 'dict')
            self['Sysctls'] = {}
            for k, v in six.iteritems(sysctls):
                self['Sysctls'][k] = six.text_type(v)

        if volumes_from is not None:
            if isinstance(volumes_from, six.string_types):
                volumes_from = volumes_from.split(',')

            self['VolumesFrom'] = volumes_from

        if binds is not None:
            self['Binds'] = convert_volume_binds(binds)

        if port_bindings is not None:
            self['PortBindings'] = convert_port_bindings(port_bindings)

        if extra_hosts is not None:
            if isinstance(extra_hosts, dict):
                extra_hosts = format_extra_hosts(extra_hosts)

            self['ExtraHosts'] = extra_hosts

        if links is not None:
            self['Links'] = normalize_links(links)

        if isinstance(lxc_conf, dict):
            formatted = []
            for k, v in six.iteritems(lxc_conf):
                formatted.append({'Key': k, 'Value': str(v)})
            lxc_conf = formatted

        if lxc_conf is not None:
            self['LxcConf'] = lxc_conf

        if cgroup_parent is not None:
            self['CgroupParent'] = cgroup_parent

        if ulimits is not None:
            if not isinstance(ulimits, list):
                raise host_config_type_error('ulimits', ulimits, 'list')
            self['Ulimits'] = []
            for l in ulimits:
                if not isinstance(l, Ulimit):
                    l = Ulimit(**l)
                self['Ulimits'].append(l)

        if log_config is not None:
            if not isinstance(log_config, LogConfig):
                if not isinstance(log_config, dict):
                    raise host_config_type_error(
                        'log_config', log_config, 'LogConfig'
                    )
                log_config = LogConfig(**log_config)

            self['LogConfig'] = log_config

        if cpu_quota:
            if not isinstance(cpu_quota, int):
                raise host_config_type_error('cpu_quota', cpu_quota, 'int')
            if version_lt(version, '1.19'):
                raise host_config_version_error('cpu_quota', '1.19')

            self['CpuQuota'] = cpu_quota

        if cpu_period:
            if not isinstance(cpu_period, int):
                raise host_config_type_error('cpu_period', cpu_period, 'int')
            if version_lt(version, '1.19'):
                raise host_config_version_error('cpu_period', '1.19')

            self['CpuPeriod'] = cpu_period

        if cpu_shares:
            if version_lt(version, '1.18'):
                raise host_config_version_error('cpu_shares', '1.18')

            if not isinstance(cpu_shares, int):
                raise host_config_type_error('cpu_shares', cpu_shares, 'int')

            self['CpuShares'] = cpu_shares

        if cpuset_cpus:
            if version_lt(version, '1.18'):
                raise host_config_version_error('cpuset_cpus', '1.18')

            self['CpusetCpus'] = cpuset_cpus

        if cpuset_mems:
            if version_lt(version, '1.19'):
                raise host_config_version_error('cpuset_mems', '1.19')

            if not isinstance(cpuset_mems, str):
                raise host_config_type_error(
                    'cpuset_mems', cpuset_mems, 'str'
                )
            self['CpusetMems'] = cpuset_mems

        if blkio_weight:
            if not isinstance(blkio_weight, int):
                raise host_config_type_error(
                    'blkio_weight', blkio_weight, 'int'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('blkio_weight', '1.22')
            self["BlkioWeight"] = blkio_weight

        if blkio_weight_device:
            if not isinstance(blkio_weight_device, list):
                raise host_config_type_error(
                    'blkio_weight_device', blkio_weight_device, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('blkio_weight_device', '1.22')
            self["BlkioWeightDevice"] = blkio_weight_device

        if device_read_bps:
            if not isinstance(device_read_bps, list):
                raise host_config_type_error(
                    'device_read_bps', device_read_bps, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_read_bps', '1.22')
            self["BlkioDeviceReadBps"] = device_read_bps

        if device_write_bps:
            if not isinstance(device_write_bps, list):
                raise host_config_type_error(
                    'device_write_bps', device_write_bps, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_write_bps', '1.22')
            self["BlkioDeviceWriteBps"] = device_write_bps

        if device_read_iops:
            if not isinstance(device_read_iops, list):
                raise host_config_type_error(
                    'device_read_iops', device_read_iops, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_read_iops', '1.22')
            self["BlkioDeviceReadIOps"] = device_read_iops

        if device_write_iops:
            if not isinstance(device_write_iops, list):
                raise host_config_type_error(
                    'device_write_iops', device_write_iops, 'list'
                )
            if version_lt(version, '1.22'):
                raise host_config_version_error('device_write_iops', '1.22')
            self["BlkioDeviceWriteIOps"] = device_write_iops

        if tmpfs:
            if version_lt(version, '1.22'):
                raise host_config_version_error('tmpfs', '1.22')
            self["Tmpfs"] = convert_tmpfs_mounts(tmpfs)

        if userns_mode:
            if version_lt(version, '1.23'):
                raise host_config_version_error('userns_mode', '1.23')

            if userns_mode != "host":
                raise host_config_value_error("userns_mode", userns_mode)
            self['UsernsMode'] = userns_mode

        if pids_limit:
            if not isinstance(pids_limit, int):
                raise host_config_type_error('pids_limit', pids_limit, 'int')
            if version_lt(version, '1.23'):
                raise host_config_version_error('pids_limit', '1.23')
            self["PidsLimit"] = pids_limit

        if isolation:
            if not isinstance(isolation, six.string_types):
                raise host_config_type_error('isolation', isolation, 'string')
            if version_lt(version, '1.24'):
                raise host_config_version_error('isolation', '1.24')
            self['Isolation'] = isolation

        if auto_remove:
            if version_lt(version, '1.25'):
                raise host_config_version_error('auto_remove', '1.25')
            self['AutoRemove'] = auto_remove

        if storage_opt is not None:
            if version_lt(version, '1.24'):
                raise host_config_version_error('storage_opt', '1.24')
            self['StorageOpt'] = storage_opt

        if init is not None:
            if version_lt(version, '1.25'):
                raise host_config_version_error('init', '1.25')
            self['Init'] = init

        if init_path is not None:
            if version_lt(version, '1.25'):
                raise host_config_version_error('init_path', '1.25')

            if version_gte(version, '1.29'):
                # https://github.com/moby/moby/pull/32470
                raise host_config_version_error('init_path', '1.29', False)
            self['InitPath'] = init_path

        if volume_driver is not None:
            if version_lt(version, '1.21'):
                raise host_config_version_error('volume_driver', '1.21')
            self['VolumeDriver'] = volume_driver

        if cpu_count:
            if not isinstance(cpu_count, int):
                raise host_config_type_error('cpu_count', cpu_count, 'int')
            if version_lt(version, '1.25'):
                raise host_config_version_error('cpu_count', '1.25')

            self['CpuCount'] = cpu_count

        if cpu_percent:
            if not isinstance(cpu_percent, int):
                raise host_config_type_error('cpu_percent', cpu_percent, 'int')
            if version_lt(version, '1.25'):
                raise host_config_version_error('cpu_percent', '1.25')

            self['CpuPercent'] = cpu_percent

        if nano_cpus:
            if not isinstance(nano_cpus, six.integer_types):
                raise host_config_type_error('nano_cpus', nano_cpus, 'int')
            if version_lt(version, '1.25'):
                raise host_config_version_error('nano_cpus', '1.25')

            self['NanoCpus'] = nano_cpus

        if runtime:
            if version_lt(version, '1.25'):
                raise host_config_version_error('runtime', '1.25')
            self['Runtime'] = runtime

        if mounts is not None:
            if version_lt(version, '1.30'):
                raise host_config_version_error('mounts', '1.30')
            self['Mounts'] = mounts


def host_config_type_error(param, param_value, expected):
    error_msg = 'Invalid type for {0} param: expected {1} but found {2}'
    return TypeError(error_msg.format(param, expected, type(param_value)))


def host_config_version_error(param, version, less_than=True):
    operator = '<' if less_than else '>'
    error_msg = '{0} param is not supported in API versions {1} {2}'
    return errors.InvalidVersion(error_msg.format(param, operator, version))


def host_config_value_error(param, param_value):
    error_msg = 'Invalid value for {0} param: {1}'
    return ValueError(error_msg.format(param, param_value))


class ContainerConfig(dict):
    def __init__(
        self, version, image, command, hostname=None, user=None, detach=False,
        stdin_open=False, tty=False, mem_limit=None, ports=None, dns=None,
        environment=None, volumes=None, volumes_from=None,
        network_disabled=False, entrypoint=None, cpu_shares=None,
        working_dir=None, domainname=None, memswap_limit=None, cpuset=None,
        host_config=None, mac_address=None, labels=None, volume_driver=None,
        stop_signal=None, networking_config=None, healthcheck=None,
        stop_timeout=None, runtime=None
    ):
        if version_gte(version, '1.10'):
            message = ('{0!r} parameter has no effect on create_container().'
                       ' It has been moved to host_config')
            if dns is not None:
                raise errors.InvalidVersion(message.format('dns'))
            if volumes_from is not None:
                raise errors.InvalidVersion(message.format('volumes_from'))

        if version_lt(version, '1.18'):
            if labels is not None:
                raise errors.InvalidVersion(
                    'labels were only introduced in API version 1.18'
                )
        else:
            if cpuset is not None or cpu_shares is not None:
                warnings.warn(
                    'The cpuset_cpus and cpu_shares options have been moved to'
                    ' host_config in API version 1.18, and will be removed',
                    DeprecationWarning
                )

        if version_lt(version, '1.19'):
            if volume_driver is not None:
                raise errors.InvalidVersion(
                    'Volume drivers were only introduced in API version 1.19'
                )
            mem_limit = mem_limit if mem_limit is not None else 0
            memswap_limit = memswap_limit if memswap_limit is not None else 0
        else:
            if mem_limit is not None:
                raise errors.InvalidVersion(
                    'mem_limit has been moved to host_config in API version'
                    ' 1.19'
                )

            if memswap_limit is not None:
                raise errors.InvalidVersion(
                    'memswap_limit has been moved to host_config in API '
                    'version 1.19'
                )

        if version_lt(version, '1.21'):
            if stop_signal is not None:
                raise errors.InvalidVersion(
                    'stop_signal was only introduced in API version 1.21'
                )
        else:
            if volume_driver is not None:
                warnings.warn(
                    'The volume_driver option has been moved to'
                    ' host_config in API version 1.21, and will be removed',
                    DeprecationWarning
                )

        if stop_timeout is not None and version_lt(version, '1.25'):
            raise errors.InvalidVersion(
                'stop_timeout was only introduced in API version 1.25'
            )

        if healthcheck is not None:
            if version_lt(version, '1.24'):
                raise errors.InvalidVersion(
                    'Health options were only introduced in API version 1.24'
                )

            if version_lt(version, '1.29') and 'StartPeriod' in healthcheck:
                raise errors.InvalidVersion(
                    'healthcheck start period was introduced in API '
                    'version 1.29'
                )

        if isinstance(command, six.string_types):
            command = split_command(command)

        if isinstance(entrypoint, six.string_types):
            entrypoint = split_command(entrypoint)

        if isinstance(environment, dict):
            environment = format_environment(environment)

        if isinstance(labels, list):
            labels = dict((lbl, six.text_type('')) for lbl in labels)

        if mem_limit is not None:
            mem_limit = parse_bytes(mem_limit)

        if memswap_limit is not None:
            memswap_limit = parse_bytes(memswap_limit)

        if isinstance(ports, list):
            exposed_ports = {}
            for port_definition in ports:
                port = port_definition
                proto = 'tcp'
                if isinstance(port_definition, tuple):
                    if len(port_definition) == 2:
                        proto = port_definition[1]
                    port = port_definition[0]
                exposed_ports['{0}/{1}'.format(port, proto)] = {}
            ports = exposed_ports

        if isinstance(volumes, six.string_types):
            volumes = [volumes, ]

        if isinstance(volumes, list):
            volumes_dict = {}
            for vol in volumes:
                volumes_dict[vol] = {}
            volumes = volumes_dict

        if volumes_from:
            if not isinstance(volumes_from, six.string_types):
                volumes_from = ','.join(volumes_from)
        else:
            # Force None, an empty list or dict causes client.start to fail
            volumes_from = None

        if healthcheck and isinstance(healthcheck, dict):
            healthcheck = Healthcheck(**healthcheck)

        attach_stdin = False
        attach_stdout = False
        attach_stderr = False
        stdin_once = False

        if not detach:
            attach_stdout = True
            attach_stderr = True

            if stdin_open:
                attach_stdin = True
                stdin_once = True

        self.update({
            'Hostname': hostname,
            'Domainname': domainname,
            'ExposedPorts': ports,
            'User': six.text_type(user) if user else None,
            'Tty': tty,
            'OpenStdin': stdin_open,
            'StdinOnce': stdin_once,
            'Memory': mem_limit,
            'AttachStdin': attach_stdin,
            'AttachStdout': attach_stdout,
            'AttachStderr': attach_stderr,
            'Env': environment,
            'Cmd': command,
            'Dns': dns,
            'Image': image,
            'Volumes': volumes,
            'VolumesFrom': volumes_from,
            'NetworkDisabled': network_disabled,
            'Entrypoint': entrypoint,
            'CpuShares': cpu_shares,
            'Cpuset': cpuset,
            'CpusetCpus': cpuset,
            'WorkingDir': working_dir,
            'MemorySwap': memswap_limit,
            'HostConfig': host_config,
            'NetworkingConfig': networking_config,
            'MacAddress': mac_address,
            'Labels': labels,
            'VolumeDriver': volume_driver,
            'StopSignal': stop_signal,
            'Healthcheck': healthcheck,
            'StopTimeout': stop_timeout,
            'Runtime': runtime
        })
