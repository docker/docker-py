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

import requests
import six

from .. import constants
from .. import errors
from .. import tls

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


def create_ipam_pool(*args, **kwargs):
    raise errors.DeprecatedMethod(
        'utils.create_ipam_pool has been removed. Please use a '
        'docker.types.IPAMPool object instead.'
    )


def create_ipam_config(*args, **kwargs):
    raise errors.DeprecatedMethod(
        'utils.create_ipam_config has been removed. Please use a '
        'docker.types.IPAMConfig object instead.'
    )


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


def build_file_list(root):
    files = []
    for dirname, dirnames, fnames in os.walk(root):
        for filename in fnames + dirnames:
            longpath = os.path.join(dirname, filename)
            files.append(
                longpath.replace(root, '', 1).lstrip('/')
            )

    return files


def create_archive(root, files=None, fileobj=None, gzip=False):
    if not fileobj:
        fileobj = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w:gz' if gzip else 'w', fileobj=fileobj)
    if files is None:
        files = build_file_list(root)
    for path in files:
        full_path = os.path.join(root, path)
        if not os.access(full_path, os.R_OK):
            raise IOError(
                'Can not access file in context: {}'.format(full_path)
            )
        i = t.gettarinfo(full_path, arcname=path)
        if i is None:
            # This happens when we encounter a socket file. We can safely
            # ignore it and proceed.
            continue

        if constants.IS_WINDOWS_PLATFORM:
            # Windows doesn't keep track of the execute bit, so we make files
            # and directories executable by default.
            i.mode = i.mode & 0o755 | 0o111

        if i.isfile():
            try:
                with open(full_path, 'rb') as f:
                    t.addfile(i, f)
            except IOError:
                t.addfile(i, None)
        else:
            # Directories, FIFOs, symlinks... don't need to be read.
            t.addfile(i, None)
    t.close()
    fileobj.seek(0)
    return fileobj


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


def convert_service_networks(networks):
    if not networks:
        return networks
    if not isinstance(networks, list):
        raise TypeError('networks parameter must be a list.')

    result = []
    for n in networks:
        if isinstance(n, six.string_types):
            n = {'Target': n}
        result.append(n)
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
        return "{0}://{1}".format(proto, host).rstrip('/')
    return "{0}://{1}:{2}{3}".format(proto, host, port, path).rstrip('/')


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


def normalize_links(links):
    if isinstance(links, dict):
        links = six.iteritems(links)

    return ['{0}:{1}'.format(k, v) for k, v in sorted(links)]


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

            line = line.strip()
            if not line:
                continue

            parse_line = line.split('=', 1)
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
        if isinstance(value, six.binary_type):
            value = value.decode('utf-8')

        return u'{key}={value}'.format(key=key, value=value)
    return [format_env(*var) for var in six.iteritems(environment)]


def format_extra_hosts(extra_hosts, task=False):
    # Use format dictated by Swarm API if container is part of a task
    if task:
        return [
            '{} {}'.format(v, k) for k, v in sorted(six.iteritems(extra_hosts))
        ]

    return [
        '{}:{}'.format(k, v) for k, v in sorted(six.iteritems(extra_hosts))
    ]


def create_host_config(self, *args, **kwargs):
    raise errors.DeprecatedMethod(
        'utils.create_host_config has been removed. Please use a '
        'docker.types.HostConfig object instead.'
    )
