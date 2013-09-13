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

import tarfile
import tempfile

import requests
import six

if six.PY3:
    from io import StringIO
else:
    from StringIO import StringIO


def mkbuildcontext(dockerfile):
    f = tempfile.TemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)
    if isinstance(dockerfile, StringIO):
        dfinfo = tarfile.TarInfo('Dockerfile')
        dfinfo.size = dockerfile.len
    else:
        dfinfo = t.gettarinfo(fileobj=dockerfile, arcname='Dockerfile')
    t.addfile(dfinfo, dockerfile)
    t.close()
    f.seek(0)
    return f


def tar(self, path):
    f = tempfile.TemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)
    t.add(path, arcname='.')
    t.close()
    f.seek(0)
    return f


def compare_version(v1, v2):
    return float(v2) - float(v1)


def ping(url):
    try:
        res = requests.get(url)
        return res.status >= 400
    except Exception:
        return False
