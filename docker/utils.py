import six
import tarfile
import tempfile

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