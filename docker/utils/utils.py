import base64
import io
import os
import os.path
import json
import shlex
import tarfile
import tempfile
import warnings
from distutils.version import StrictVersion
from datetime import datetime
from fnmatch import fnmatch

import requests
import six

from .. import constants
from .. import errors
from .. import tls
from ..types import Ulimit, LogConfig

if six.PY2:
    from urllib import splitnport
else:
    from urllib.parse import splitnport

DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_UNIX_SOCKET = "http+unix://var/run/docker.sock"
DEFAULT_NPIPE = 'npipe:////./pipe/docker_engine'

BYTE_UNITS = {
    'b': 1,
    'k': 1024,
    'm': 1024 * 1024,
    'g': 1024 * 1024 * 1024
}


def create_ipam_pool(subnet=None, iprange=None, gateway=None,
                     aux_addresses=None):
    return {
        'Subnet': subnet,
        'IPRange': iprange,
        'Gateway': gateway,
        'AuxiliaryAddresses': aux_addresses
    }


def create_ipam_config(driver='default', pool_configs=None):
    return {
        'Driver': driver,
        'Config': pool_configs or []
    }


def mkbuildcontext(dockerfile):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)
    if isinstance(dockerfile, io.StringIO):
        dfinfo = tarfile.TarInfo('Dockerfile')
        if six.PY3:
            raise TypeError('Please use io.BytesIO to create in-memory '
                            'Dockerfiles with Python 3')
        else:
            dfinfo.size = len(dockerfile.getvalue())
            dockerfile.seek(0)
    elif isinstance(dockerfile, io.BytesIO):
        dfinfo = tarfile.TarInfo('Dockerfile')
        dfinfo.size = len(dockerfile.getvalue())
        dockerfile.seek(0)
    else:
        dfinfo = t.gettarinfo(fileobj=dockerfile, arcname='Dockerfile')
    t.addfile(dfinfo, dockerfile)
    t.close()
    f.seek(0)
    return f


def decode_json_header(header):
    data = base64.b64decode(header)
    if six.PY3:
        data = data.decode('utf-8')
    return json.loads(data)


def tar(path, exclude=None, dockerfile=None, fileobj=None, gzip=False):
    if not fileobj:
        fileobj = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w:gz' if gzip else 'w', fileobj=fileobj)

    root = os.path.abspath(path)
    exclude = exclude or []

    for path in sorted(exclude_paths(root, exclude, dockerfile=dockerfile)):
        t.add(os.path.join(root, path), arcname=path, recursive=False)

    t.close()
    fileobj.seek(0)
    return fileobj


def exclude_paths(root, patterns, dockerfile=None):
    """
    Given a root directory path and a list of .dockerignore patterns, return
    an iterator of all paths (both regular files and directories) in the root
    directory that do *not* match any of the patterns.

    All paths returned are relative to the root.
    """
    if dockerfile is None:
        dockerfile = 'Dockerfile'

    exceptions = [p for p in patterns if p.startswith('!')]

    include_patterns = [p[1:] for p in exceptions]
    include_patterns += [dockerfile, '.dockerignore']

    exclude_patterns = list(set(patterns) - set(exceptions))

    paths = get_paths(root, exclude_patterns, include_patterns,
                      has_exceptions=len(exceptions) > 0)

    return set(paths).union(
        # If the Dockerfile is in a subdirectory that is excluded, get_paths
        # will not descend into it and the file will be skipped. This ensures
        # it doesn't happen.
        set([dockerfile])
        if os.path.exists(os.path.join(root, dockerfile)) else set()
    )


def should_include(path, exclude_patterns, include_patterns):
    """
    Given a path, a list of exclude patterns, and a list of inclusion patterns:

    1. Returns True if the path doesn't match any exclusion pattern
    2. Returns False if the path matches an exclusion pattern and doesn't match
       an inclusion pattern
    3. Returns true if the path matches an exclusion pattern and matches an
       inclusion pattern
    """
    for pattern in exclude_patterns:
        if match_path(path, pattern):
            for pattern in include_patterns:
                if match_path(path, pattern):
                    return True
            return False
    return True


def get_paths(root, exclude_patterns, include_patterns, has_exceptions=False):
    paths = []

    for parent, dirs, files in os.walk(root, topdown=True, followlinks=False):
        parent = os.path.relpath(parent, root)
        if parent == '.':
            parent = ''

        # If exception rules exist, we can't skip recursing into ignored
        # directories, as we need to look for exceptions in them.
        #
        # It may be possible to optimize this further for exception patterns
        # that *couldn't* match within ignored directores.
        #
        # This matches the current docker logic (as of 2015-11-24):
        # https://github.com/docker/docker/blob/37ba67bf636b34dc5c0c0265d62a089d0492088f/pkg/archive/archive.go#L555-L557

        if not has_exceptions:

            # Remove excluded patterns from the list of directories to traverse
            # by mutating the dirs we're iterating over.
            # This looks strange, but is considered the correct way to skip
            # traversal. See https://docs.python.org/2/library/os.html#os.walk

            dirs[:] = [d for d in dirs if
                       should_include(os.path.join(parent, d),
                                      exclude_patterns, include_patterns)]

        for path in dirs:
            if should_include(os.path.join(parent, path),
                              exclude_patterns, include_patterns):
                paths.append(os.path.join(parent, path))

        for path in files:
            if should_include(os.path.join(parent, path),
                              exclude_patterns, include_patterns):
                paths.append(os.path.join(parent, path))

    return paths


def match_path(path, pattern):
    pattern = pattern.rstrip('/')
    if pattern:
        pattern = os.path.relpath(pattern)

    pattern_components = pattern.split('/')
    path_components = path.split('/')[:len(pattern_components)]
    return fnmatch('/'.join(path_components), pattern)


def compare_version(v1, v2):
    """Compare docker versions

    >>> v1 = '1.9'
    >>> v2 = '1.10'
    >>> compare_version(v1, v2)
    1
    >>> compare_version(v2, v1)
    -1
    >>> compare_version(v2, v2)
    0
    """
    s1 = StrictVersion(v1)
    s2 = StrictVersion(v2)
    if s1 == s2:
        return 0
    elif s1 > s2:
        return -1
    else:
        return 1


def version_lt(v1, v2):
    return compare_version(v1, v2) > 0


def version_gte(v1, v2):
    return not version_lt(v1, v2)


def ping_registry(url):
    warnings.warn(
        'The `ping_registry` method is deprecated and will be removed.',
        DeprecationWarning
    )

    return ping(url + '/v2/', [401]) or ping(url + '/v1/_ping')


def ping(url, valid_4xx_statuses=None):
    try:
        res = requests.get(url, timeout=3)
    except Exception:
        return False
    else:
        # We don't send yet auth headers
        # and a v2 registry will respond with status 401
        return (
            res.status_code < 400 or
            (valid_4xx_statuses and res.status_code in valid_4xx_statuses)
        )


def _convert_port_binding(binding):
    result = {'HostIp': '', 'HostPort': ''}
    if isinstance(binding, tuple):
        if len(binding) == 2:
            result['HostPort'] = binding[1]
            result['HostIp'] = binding[0]
        elif isinstance(binding[0], six.string_types):
            result['HostIp'] = binding[0]
        else:
            result['HostPort'] = binding[0]
    elif isinstance(binding, dict):
        if 'HostPort' in binding:
            result['HostPort'] = binding['HostPort']
            if 'HostIp' in binding:
                result['HostIp'] = binding['HostIp']
        else:
            raise ValueError(binding)
    else:
        result['HostPort'] = binding

    if result['HostPort'] is None:
        result['HostPort'] = ''
    else:
        result['HostPort'] = str(result['HostPort'])

    return result


def convert_port_bindings(port_bindings):
    result = {}
    for k, v in six.iteritems(port_bindings):
        key = str(k)
        if '/' not in key:
            key += '/tcp'
        if isinstance(v, list):
            result[key] = [_convert_port_binding(binding) for binding in v]
        else:
            result[key] = [_convert_port_binding(v)]
    return result


def convert_volume_binds(binds):
    if isinstance(binds, list):
        return binds

    result = []
    for k, v in binds.items():
        if isinstance(k, six.binary_type):
            k = k.decode('utf-8')

        if isinstance(v, dict):
            if 'ro' in v and 'mode' in v:
                raise ValueError(
                    'Binding cannot contain both "ro" and "mode": {}'
                    .format(repr(v))
                )

            bind = v['bind']
            if isinstance(bind, six.binary_type):
                bind = bind.decode('utf-8')

            if 'ro' in v:
                mode = 'ro' if v['ro'] else 'rw'
            elif 'mode' in v:
                mode = v['mode']
            else:
                mode = 'rw'

            result.append(
                six.text_type('{0}:{1}:{2}').format(k, bind, mode)
            )
        else:
            if isinstance(v, six.binary_type):
                v = v.decode('utf-8')
            result.append(
                six.text_type('{0}:{1}:rw').format(k, v)
            )
    return result


def convert_tmpfs_mounts(tmpfs):
    if isinstance(tmpfs, dict):
        return tmpfs

    if not isinstance(tmpfs, list):
        raise ValueError(
            'Expected tmpfs value to be either a list or a dict, found: {}'
            .format(type(tmpfs).__name__)
        )

    result = {}
    for mount in tmpfs:
        if isinstance(mount, six.string_types):
            if ":" in mount:
                name, options = mount.split(":", 1)
            else:
                name = mount
                options = ""

        else:
            raise ValueError(
                "Expected item in tmpfs list to be a string, found: {}"
                .format(type(mount).__name__)
            )

        result[name] = options
    return result


def parse_repository_tag(repo_name):
    parts = repo_name.rsplit('@', 1)
    if len(parts) == 2:
        return tuple(parts)
    parts = repo_name.rsplit(':', 1)
    if len(parts) == 2 and '/' not in parts[1]:
        return tuple(parts)
    return repo_name, None


# Based on utils.go:ParseHost http://tinyurl.com/nkahcfh
# fd:// protocol unsupported (for obvious reasons)
# Added support for http and https
# Protocol translation: tcp -> http, unix -> http+unix
def parse_host(addr, is_win32=False, tls=False):
    proto = "http+unix"
    port = None
    path = ''

    if not addr and is_win32:
        addr = DEFAULT_NPIPE

    if not addr or addr.strip() == 'unix://':
        return DEFAULT_UNIX_SOCKET

    addr = addr.strip()
    if addr.startswith('http://'):
        addr = addr.replace('http://', 'tcp://')
    if addr.startswith('http+unix://'):
        addr = addr.replace('http+unix://', 'unix://')

    if addr == 'tcp://':
        raise errors.DockerException(
            "Invalid bind address format: {0}".format(addr)
        )
    elif addr.startswith('unix://'):
        addr = addr[7:]
    elif addr.startswith('tcp://'):
        proto = 'http{0}'.format('s' if tls else '')
        addr = addr[6:]
    elif addr.startswith('https://'):
        proto = "https"
        addr = addr[8:]
    elif addr.startswith('npipe://'):
        proto = 'npipe'
        addr = addr[8:]
    elif addr.startswith('fd://'):
        raise errors.DockerException("fd protocol is not implemented")
    else:
        if "://" in addr:
            raise errors.DockerException(
                "Invalid bind address protocol: {0}".format(addr)
            )
        proto = "https" if tls else "http"

    if proto in ("http", "https"):
        address_parts = addr.split('/', 1)
        host = address_parts[0]
        if len(address_parts) == 2:
            path = '/' + address_parts[1]
        host, port = splitnport(host)

        if port is None:
            raise errors.DockerException(
                "Invalid port: {0}".format(addr)
            )

        if not host:
            host = DEFAULT_HTTP_HOST
    else:
        host = addr

    if proto in ("http", "https") and port == -1:
        raise errors.DockerException(
            "Bind address needs a port: {0}".format(addr))

    if proto == "http+unix" or proto == 'npipe':
        return "{0}://{1}".format(proto, host)
    return "{0}://{1}:{2}{3}".format(proto, host, port, path)


def parse_devices(devices):
    device_list = []
    for device in devices:
        if isinstance(device, dict):
            device_list.append(device)
            continue
        if not isinstance(device, six.string_types):
            raise errors.DockerException(
                'Invalid device type {0}'.format(type(device))
            )
        device_mapping = device.split(':')
        if device_mapping:
            path_on_host = device_mapping[0]
            if len(device_mapping) > 1:
                path_in_container = device_mapping[1]
            else:
                path_in_container = path_on_host
            if len(device_mapping) > 2:
                permissions = device_mapping[2]
            else:
                permissions = 'rwm'
            device_list.append({
                'PathOnHost': path_on_host,
                'PathInContainer': path_in_container,
                'CgroupPermissions': permissions
            })
    return device_list


def kwargs_from_env(ssl_version=None, assert_hostname=None, environment=None):
    if not environment:
        environment = os.environ
    host = environment.get('DOCKER_HOST')

    # empty string for cert path is the same as unset.
    cert_path = environment.get('DOCKER_CERT_PATH') or None

    # empty string for tls verify counts as "false".
    # Any value or 'unset' counts as true.
    tls_verify = environment.get('DOCKER_TLS_VERIFY')
    if tls_verify == '':
        tls_verify = False
    else:
        tls_verify = tls_verify is not None
    enable_tls = cert_path or tls_verify

    params = {}

    if host:
        params['base_url'] = (
            host.replace('tcp://', 'https://') if enable_tls else host
        )

    if not enable_tls:
        return params

    if not cert_path:
        cert_path = os.path.join(os.path.expanduser('~'), '.docker')

    if not tls_verify and assert_hostname is None:
        # assert_hostname is a subset of TLS verification,
        # so if it's not set already then set it to false.
        assert_hostname = False

    params['tls'] = tls.TLSConfig(
        client_cert=(os.path.join(cert_path, 'cert.pem'),
                     os.path.join(cert_path, 'key.pem')),
        ca_cert=os.path.join(cert_path, 'ca.pem'),
        verify=tls_verify,
        ssl_version=ssl_version,
        assert_hostname=assert_hostname,
    )

    return params


def convert_filters(filters):
    result = {}
    for k, v in six.iteritems(filters):
        if isinstance(v, bool):
            v = 'true' if v else 'false'
        if not isinstance(v, list):
            v = [v, ]
        result[k] = v
    return json.dumps(result)


def datetime_to_timestamp(dt):
    """Convert a UTC datetime to a Unix timestamp"""
    delta = dt - datetime.utcfromtimestamp(0)
    return delta.seconds + delta.days * 24 * 3600


def parse_bytes(s):
    if isinstance(s, six.integer_types + (float,)):
        return s
    if len(s) == 0:
        return 0

    if s[-2:-1].isalpha() and s[-1].isalpha():
        if s[-1] == "b" or s[-1] == "B":
            s = s[:-1]
    units = BYTE_UNITS
    suffix = s[-1].lower()

    # Check if the variable is a string representation of an int
    # without a units part. Assuming that the units are bytes.
    if suffix.isdigit():
        digits_part = s
        suffix = 'b'
    else:
        digits_part = s[:-1]

    if suffix in units.keys() or suffix.isdigit():
        try:
            digits = int(digits_part)
        except ValueError:
            raise errors.DockerException(
                'Failed converting the string value for memory ({0}) to'
                ' an integer.'.format(digits_part)
            )

        # Reconvert to long for the final result
        s = int(digits * units[suffix])
    else:
        raise errors.DockerException(
            'The specified value for memory ({0}) should specify the'
            ' units. The postfix should be one of the `b` `k` `m` `g`'
            ' characters'.format(s)
        )

    return s


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


def create_host_config(binds=None, port_bindings=None, lxc_conf=None,
                       publish_all_ports=False, links=None, privileged=False,
                       dns=None, dns_search=None, volumes_from=None,
                       network_mode=None, restart_policy=None, cap_add=None,
                       cap_drop=None, devices=None, extra_hosts=None,
                       read_only=None, pid_mode=None, ipc_mode=None,
                       security_opt=None, ulimits=None, log_config=None,
                       mem_limit=None, memswap_limit=None,
                       mem_reservation=None, kernel_memory=None,
                       mem_swappiness=None, cgroup_parent=None,
                       group_add=None, cpu_quota=None,
                       cpu_period=None, blkio_weight=None,
                       blkio_weight_device=None, device_read_bps=None,
                       device_write_bps=None, device_read_iops=None,
                       device_write_iops=None, oom_kill_disable=False,
                       shm_size=None, sysctls=None, version=None, tmpfs=None,
                       oom_score_adj=None, dns_opt=None, cpu_shares=None,
                       cpuset_cpus=None, userns_mode=None, pids_limit=None):

    host_config = {}

    if not version:
        warnings.warn(
            'docker.utils.create_host_config() is deprecated. Please use '
            'Client.create_host_config() instead.'
        )
        version = constants.DEFAULT_DOCKER_API_VERSION

    if mem_limit is not None:
        host_config['Memory'] = parse_bytes(mem_limit)

    if memswap_limit is not None:
        host_config['MemorySwap'] = parse_bytes(memswap_limit)

    if mem_reservation:
        if version_lt(version, '1.21'):
            raise host_config_version_error('mem_reservation', '1.21')

        host_config['MemoryReservation'] = parse_bytes(mem_reservation)

    if kernel_memory:
        if version_lt(version, '1.21'):
            raise host_config_version_error('kernel_memory', '1.21')

        host_config['KernelMemory'] = parse_bytes(kernel_memory)

    if mem_swappiness is not None:
        if version_lt(version, '1.20'):
            raise host_config_version_error('mem_swappiness', '1.20')
        if not isinstance(mem_swappiness, int):
            raise host_config_type_error(
                'mem_swappiness', mem_swappiness, 'int'
            )

        host_config['MemorySwappiness'] = mem_swappiness

    if shm_size is not None:
        if isinstance(shm_size, six.string_types):
            shm_size = parse_bytes(shm_size)

        host_config['ShmSize'] = shm_size

    if pid_mode not in (None, 'host'):
        raise host_config_value_error('pid_mode', pid_mode)
    elif pid_mode:
        host_config['PidMode'] = pid_mode

    if ipc_mode:
        host_config['IpcMode'] = ipc_mode

    if privileged:
        host_config['Privileged'] = privileged

    if oom_kill_disable:
        if version_lt(version, '1.20'):
            raise host_config_version_error('oom_kill_disable', '1.19')

        host_config['OomKillDisable'] = oom_kill_disable

    if oom_score_adj:
        if version_lt(version, '1.22'):
            raise host_config_version_error('oom_score_adj', '1.22')
        if not isinstance(oom_score_adj, int):
            raise host_config_type_error(
                'oom_score_adj', oom_score_adj, 'int'
            )
        host_config['OomScoreAdj'] = oom_score_adj

    if publish_all_ports:
        host_config['PublishAllPorts'] = publish_all_ports

    if read_only is not None:
        host_config['ReadonlyRootfs'] = read_only

    if dns_search:
        host_config['DnsSearch'] = dns_search

    if network_mode:
        host_config['NetworkMode'] = network_mode
    elif network_mode is None and compare_version('1.19', version) > 0:
        host_config['NetworkMode'] = 'default'

    if restart_policy:
        if not isinstance(restart_policy, dict):
            raise host_config_type_error(
                'restart_policy', restart_policy, 'dict'
            )

        host_config['RestartPolicy'] = restart_policy

    if cap_add:
        host_config['CapAdd'] = cap_add

    if cap_drop:
        host_config['CapDrop'] = cap_drop

    if devices:
        host_config['Devices'] = parse_devices(devices)

    if group_add:
        if version_lt(version, '1.20'):
            raise host_config_version_error('group_add', '1.20')

        host_config['GroupAdd'] = [six.text_type(grp) for grp in group_add]

    if dns is not None:
        host_config['Dns'] = dns

    if dns_opt is not None:
        if version_lt(version, '1.21'):
            raise host_config_version_error('dns_opt', '1.21')

        host_config['DnsOptions'] = dns_opt

    if security_opt is not None:
        if not isinstance(security_opt, list):
            raise host_config_type_error('security_opt', security_opt, 'list')

        host_config['SecurityOpt'] = security_opt

    if sysctls:
        if not isinstance(sysctls, dict):
            raise host_config_type_error('sysctls', sysctls, 'dict')
        host_config['Sysctls'] = {}
        for k, v in six.iteritems(sysctls):
            host_config['Sysctls'][k] = six.text_type(v)

    if volumes_from is not None:
        if isinstance(volumes_from, six.string_types):
            volumes_from = volumes_from.split(',')

        host_config['VolumesFrom'] = volumes_from

    if binds is not None:
        host_config['Binds'] = convert_volume_binds(binds)

    if port_bindings is not None:
        host_config['PortBindings'] = convert_port_bindings(port_bindings)

    if extra_hosts is not None:
        if isinstance(extra_hosts, dict):
            extra_hosts = [
                '{0}:{1}'.format(k, v)
                for k, v in sorted(six.iteritems(extra_hosts))
            ]

        host_config['ExtraHosts'] = extra_hosts

    if links is not None:
        host_config['Links'] = normalize_links(links)

    if isinstance(lxc_conf, dict):
        formatted = []
        for k, v in six.iteritems(lxc_conf):
            formatted.append({'Key': k, 'Value': str(v)})
        lxc_conf = formatted

    if lxc_conf is not None:
        host_config['LxcConf'] = lxc_conf

    if cgroup_parent is not None:
        host_config['CgroupParent'] = cgroup_parent

    if ulimits is not None:
        if not isinstance(ulimits, list):
            raise host_config_type_error('ulimits', ulimits, 'list')
        host_config['Ulimits'] = []
        for l in ulimits:
            if not isinstance(l, Ulimit):
                l = Ulimit(**l)
            host_config['Ulimits'].append(l)

    if log_config is not None:
        if not isinstance(log_config, LogConfig):
            if not isinstance(log_config, dict):
                raise host_config_type_error(
                    'log_config', log_config, 'LogConfig'
                )
            log_config = LogConfig(**log_config)

        host_config['LogConfig'] = log_config

    if cpu_quota:
        if not isinstance(cpu_quota, int):
            raise host_config_type_error('cpu_quota', cpu_quota, 'int')
        if version_lt(version, '1.19'):
            raise host_config_version_error('cpu_quota', '1.19')

        host_config['CpuQuota'] = cpu_quota

    if cpu_period:
        if not isinstance(cpu_period, int):
            raise host_config_type_error('cpu_period', cpu_period, 'int')
        if version_lt(version, '1.19'):
            raise host_config_version_error('cpu_period', '1.19')

        host_config['CpuPeriod'] = cpu_period

    if cpu_shares:
        if version_lt(version, '1.18'):
            raise host_config_version_error('cpu_shares', '1.18')

        if not isinstance(cpu_shares, int):
            raise host_config_type_error('cpu_shares', cpu_shares, 'int')

        host_config['CpuShares'] = cpu_shares

    if cpuset_cpus:
        if version_lt(version, '1.18'):
            raise host_config_version_error('cpuset_cpus', '1.18')

        host_config['CpuSetCpus'] = cpuset_cpus

    if blkio_weight:
        if not isinstance(blkio_weight, int):
            raise host_config_type_error('blkio_weight', blkio_weight, 'int')
        if version_lt(version, '1.22'):
            raise host_config_version_error('blkio_weight', '1.22')
        host_config["BlkioWeight"] = blkio_weight

    if blkio_weight_device:
        if not isinstance(blkio_weight_device, list):
            raise host_config_type_error(
                'blkio_weight_device', blkio_weight_device, 'list'
            )
        if version_lt(version, '1.22'):
            raise host_config_version_error('blkio_weight_device', '1.22')
        host_config["BlkioWeightDevice"] = blkio_weight_device

    if device_read_bps:
        if not isinstance(device_read_bps, list):
            raise host_config_type_error(
                'device_read_bps', device_read_bps, 'list'
            )
        if version_lt(version, '1.22'):
            raise host_config_version_error('device_read_bps', '1.22')
        host_config["BlkioDeviceReadBps"] = device_read_bps

    if device_write_bps:
        if not isinstance(device_write_bps, list):
            raise host_config_type_error(
                'device_write_bps', device_write_bps, 'list'
            )
        if version_lt(version, '1.22'):
            raise host_config_version_error('device_write_bps', '1.22')
        host_config["BlkioDeviceWriteBps"] = device_write_bps

    if device_read_iops:
        if not isinstance(device_read_iops, list):
            raise host_config_type_error(
                'device_read_iops', device_read_iops, 'list'
            )
        if version_lt(version, '1.22'):
            raise host_config_version_error('device_read_iops', '1.22')
        host_config["BlkioDeviceReadIOps"] = device_read_iops

    if device_write_iops:
        if not isinstance(device_write_iops, list):
            raise host_config_type_error(
                'device_write_iops', device_write_iops, 'list'
            )
        if version_lt(version, '1.22'):
            raise host_config_version_error('device_write_iops', '1.22')
        host_config["BlkioDeviceWriteIOps"] = device_write_iops

    if tmpfs:
        if version_lt(version, '1.22'):
            raise host_config_version_error('tmpfs', '1.22')
        host_config["Tmpfs"] = convert_tmpfs_mounts(tmpfs)

    if userns_mode:
        if version_lt(version, '1.23'):
            raise host_config_version_error('userns_mode', '1.23')

        if userns_mode != "host":
            raise host_config_value_error("userns_mode", userns_mode)
        host_config['UsernsMode'] = userns_mode

    if pids_limit:
        if not isinstance(pids_limit, int):
            raise host_config_type_error('pids_limit', pids_limit, 'int')
        if version_lt(version, '1.23'):
            raise host_config_version_error('pids_limit', '1.23')
        host_config["PidsLimit"] = pids_limit

    return host_config


def normalize_links(links):
    if isinstance(links, dict):
        links = six.iteritems(links)

    return ['{0}:{1}'.format(k, v) for k, v in sorted(links)]


def create_networking_config(endpoints_config=None):
    networking_config = {}

    if endpoints_config:
        networking_config["EndpointsConfig"] = endpoints_config

    return networking_config


def create_endpoint_config(version, aliases=None, links=None,
                           ipv4_address=None, ipv6_address=None,
                           link_local_ips=None):
    if version_lt(version, '1.22'):
        raise errors.InvalidVersion(
            'Endpoint config is not supported for API version < 1.22'
        )
    endpoint_config = {}

    if aliases:
        endpoint_config["Aliases"] = aliases

    if links:
        endpoint_config["Links"] = normalize_links(links)

    ipam_config = {}
    if ipv4_address:
        ipam_config['IPv4Address'] = ipv4_address

    if ipv6_address:
        ipam_config['IPv6Address'] = ipv6_address

    if link_local_ips is not None:
        if version_lt(version, '1.24'):
            raise errors.InvalidVersion(
                'link_local_ips is not supported for API version < 1.24'
            )
        ipam_config['LinkLocalIPs'] = link_local_ips

    if ipam_config:
        endpoint_config['IPAMConfig'] = ipam_config

    return endpoint_config


def parse_env_file(env_file):
    """
    Reads a line-separated environment file.
    The format of each line should be "key=value".
    """
    environment = {}

    with open(env_file, 'r') as f:
        for line in f:

            if line[0] == '#':
                continue

            parse_line = line.strip().split('=', 1)
            if len(parse_line) == 2:
                k, v = parse_line
                environment[k] = v
            else:
                raise errors.DockerException(
                    'Invalid line in environment file {0}:\n{1}'.format(
                        env_file, line))

    return environment


def split_command(command):
    if six.PY2 and not isinstance(command, six.binary_type):
        command = command.encode('utf-8')
    return shlex.split(command)


def format_environment(environment):
    def format_env(key, value):
        if value is None:
            return key
        return u'{key}={value}'.format(key=key, value=value)
    return [format_env(*var) for var in six.iteritems(environment)]


def create_container_config(
    version, image, command, hostname=None, user=None, detach=False,
    stdin_open=False, tty=False, mem_limit=None, ports=None, environment=None,
    dns=None, volumes=None, volumes_from=None, network_disabled=False,
    entrypoint=None, cpu_shares=None, working_dir=None, domainname=None,
    memswap_limit=None, cpuset=None, host_config=None, mac_address=None,
    labels=None, volume_driver=None, stop_signal=None, networking_config=None,
):
    if isinstance(command, six.string_types):
        command = split_command(command)

    if isinstance(entrypoint, six.string_types):
        entrypoint = split_command(entrypoint)

    if isinstance(environment, dict):
        environment = format_environment(environment)

    if labels is not None and compare_version('1.18', version) < 0:
        raise errors.InvalidVersion(
            'labels were only introduced in API version 1.18'
        )

    if cpuset is not None or cpu_shares is not None:
        if version_gte(version, '1.18'):
            warnings.warn(
                'The cpuset_cpus and cpu_shares options have been moved to '
                'host_config in API version 1.18, and will be removed',
                DeprecationWarning
            )

    if stop_signal is not None and compare_version('1.21', version) < 0:
        raise errors.InvalidVersion(
            'stop_signal was only introduced in API version 1.21'
        )

    if compare_version('1.19', version) < 0:
        if volume_driver is not None:
            raise errors.InvalidVersion(
                'Volume drivers were only introduced in API version 1.19'
            )
        mem_limit = mem_limit if mem_limit is not None else 0
        memswap_limit = memswap_limit if memswap_limit is not None else 0
    else:
        if mem_limit is not None:
            raise errors.InvalidVersion(
                'mem_limit has been moved to host_config in API version 1.19'
            )

        if memswap_limit is not None:
            raise errors.InvalidVersion(
                'memswap_limit has been moved to host_config in API '
                'version 1.19'
            )

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

    if compare_version('1.10', version) >= 0:
        message = ('{0!r} parameter has no effect on create_container().'
                   ' It has been moved to host_config')
        if dns is not None:
            raise errors.InvalidVersion(message.format('dns'))
        if volumes_from is not None:
            raise errors.InvalidVersion(message.format('volumes_from'))

    return {
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
        'StopSignal': stop_signal
    }
