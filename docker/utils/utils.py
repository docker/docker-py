# Copyright 2013 dotCloud inc.

#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at

#        http://www.apache.org/licenses/LICENSE-2.0

#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import io
import os
import tarfile
import tempfile
from distutils.version import StrictVersion
from fnmatch import fnmatch

import requests
import six

from .. import errors

DEFAULT_HTTP_HOST = "127.0.0.1"
DEFAULT_UNIX_SOCKET = "http+unix://var/run/docker.sock"


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
    elif isinstance(dockerfile, io.BytesIO):
        dfinfo = tarfile.TarInfo('Dockerfile')
        dfinfo.size = len(dockerfile.getvalue())
    else:
        dfinfo = t.gettarinfo(fileobj=dockerfile, arcname='Dockerfile')
    t.addfile(dfinfo, dockerfile)
    t.close()
    f.seek(0)
    return f


def fnmatch_any(relpath, patterns):
    return any([fnmatch(relpath, pattern) for pattern in patterns])


def tar(path, exclude=None):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)
    for dirpath, dirnames, filenames in os.walk(path):
        relpath = os.path.relpath(dirpath, path)
        if relpath == '.':
            relpath = ''
        if exclude is None:
            fnames = filenames
        else:
            dirnames[:] = [d for d in dirnames
                           if not fnmatch_any(os.path.join(relpath, d),
                                              exclude)]
            fnames = [name for name in filenames
                      if not fnmatch_any(os.path.join(relpath, name),
                                         exclude)]
        for name in fnames:
            arcname = os.path.join(relpath, name)
            t.add(os.path.join(path, arcname), arcname=arcname)
    t.close()
    f.seek(0)
    return f


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


def ping(url):
    try:
        res = requests.get(url, timeout=3)
    except Exception:
        return False
    else:
        return res.status_code < 400


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
            key = key + '/tcp'
        if isinstance(v, list):
            result[key] = [_convert_port_binding(binding) for binding in v]
        else:
            result[key] = [_convert_port_binding(v)]
    return result


def convert_volume_binds(binds):
    result = []
    for k, v in binds.items():
        if isinstance(v, dict):
            result.append('%s:%s:%s' % (
                k, v['bind'], 'ro' if v.get('ro', False) else 'rw'
            ))
        else:
            result.append('%s:%s:rw' % (k, v))
    return result


def parse_repository_tag(repo):
    column_index = repo.rfind(':')
    if column_index < 0:
        return repo, None
    tag = repo[column_index + 1:]
    slash_index = tag.find('/')
    if slash_index < 0:
        return repo[:column_index], tag

    return repo, None


# Based on utils.go:ParseHost http://tinyurl.com/nkahcfh
# fd:// protocol unsupported (for obvious reasons)
# Added support for http and https
# Protocol translation: tcp -> http, unix -> http+unix
def parse_host(addr):
    proto = "http+unix"
    host = DEFAULT_HTTP_HOST
    port = None
    if not addr or addr.strip() == 'unix://':
        return DEFAULT_UNIX_SOCKET

    addr = addr.strip()
    if addr.startswith('http://'):
        addr = addr.replace('http://', 'tcp://')
    if addr.startswith('http+unix://'):
        addr = addr.replace('http+unix://', 'unix://')

    if addr == 'tcp://':
        raise errors.DockerException("Invalid bind address format: %s" % addr)
    elif addr.startswith('unix://'):
        addr = addr[7:]
    elif addr.startswith('tcp://'):
        proto = "http"
        addr = addr[6:]
    elif addr.startswith('https://'):
        proto = "https"
        addr = addr[8:]
    elif addr.startswith('fd://'):
        raise errors.DockerException("fd protocol is not implemented")
    else:
        if "://" in addr:
            raise errors.DockerException(
                "Invalid bind address protocol: %s" % addr
            )
        proto = "http"

    if proto != "http+unix" and ":" in addr:
        host_parts = addr.split(':')
        if len(host_parts) != 2:
            raise errors.DockerException(
                "Invalid bind address format: %s" % addr
            )
        if host_parts[0]:
            host = host_parts[0]

        try:
            port = int(host_parts[1])
        except Exception:
            raise errors.DockerException(
                "Invalid port: %s", addr
            )

    elif proto in ("http", "https") and ':' not in addr:
        raise errors.DockerException("Bind address needs a port: %s" % addr)
    else:
        host = addr

    if proto == "http+unix":
        return "%s://%s" % (proto, host)
    return "%s://%s:%d" % (proto, host, port)
