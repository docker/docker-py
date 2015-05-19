import os
import tarfile
import six
from collections import namedtuple


class ContextError(Exception):
    def __init__(self, msg):
        self.message = msg


INVALID_CONTEXT_FORMAT_LONG_FMT = """
Build context at %s is not supported by Docker\\n
The path must point to either:
\t * A readable directory containing a valid Dockerfile
\t * A tarball (optionally compressed with gzip, xz or bzip2)
\t * A valid Dockerfile
\t * A valid URL for a remote build context.
%s"""


# these prefixes are treated as remote by the docker daemon
# (ref: pkg/urlutil/*) as of v1.6.0
REMOTE_CONTEXT_PREFIXES = ["http://",
                           "https://",
                           "git://",
                           "git@",
                           "github.com/"]


class BuildContext(namedtuple('BuildContext',
                              ['format', 'path', 'dockerfile', 'job_params'])):
    def __new__(cls, context_format,
                path,
                dockerfile='Dockerfile',
                job_params=None):
        ctx_tuple = super(BuildContext, cls)
        return ctx_tuple.__new__(
            cls,
            context_format,
            path,
            dockerfile,
            job_params,
        )


def make_context_from_tarball(path, dockerfile='Dockerfile'):
    return BuildContext(
        'tarball',
        path,
        dockerfile=dockerfile,
        job_params={
            'encoding': 'gzip',
            'custom_context': True,
            'fileobj': open(path)
        }
    )


def make_context_from_dockerfile(path, dockerfile='Dockerfile'):
    return BuildContext(
        'dockerfile',
        path=path,
        dockerfile=dockerfile,
        job_params={'fileobj': open(path, 'r')},
    )


def make_context_from_url(path, dockerfile='Dockerfile'):
    return BuildContext(
        'remote',
        path,
        dockerfile=dockerfile,
        job_params={},
    )


def make_context_from_directory(path, dockerfile='Dockerfile'):
    return BuildContext(
        'directory',
        path,
        dockerfile=dockerfile,
        job_params={}
    )


context_builders = {
    'tarball': make_context_from_tarball,
    'dockerfile': make_context_from_dockerfile,
    'remote': make_context_from_url,
    'directory': make_context_from_directory
}


def create_context_from_path(path, dockerfile='Dockerfile'):
    if path is None:
        raise ContextError("'path' parameter cannot be None")
    if dockerfile is None:
        raise ContextError("'dockerfile' parameter cannot be None")

    _dockerfile = dockerfile.encode('utf-8')
    _path = path.encode('utf-8')
    context_maker = detect_context_format(_path, _dockerfile)
    if context_maker is None:
        raise ContextError("Format not supported at "
                           "%s [dockerfile='%s']." % (path, dockerfile))

    return context_maker(path, dockerfile)


def is_remote(path):
    if path is None:
        return False

    _path = path
    if isinstance(_path, six.binary_type):
        _path = _path.decode('utf-8')
    for prefix in REMOTE_CONTEXT_PREFIXES:
        if _path.startswith(prefix):
            return True
    return False


def detect_context_format(path, dockerfile='Dockerfile'):
    if is_remote(path):
        return context_builders['remote']

    try:
        os.access(path, os.R_OK)
    except IOError as ioe:
        raise ContextError("%s: %s" % (path, ioe))

    if os.path.isdir(path):
        if dockerfile in os.listdir(path):
            return context_builders['directory']
        else:
            raise ContextError("Directory %s does not contain a Dockerfile"
                               " with name %s" % (path, dockerfile))
    elif is_tarball_context(path):
        return context_builders['tarball']

    elif os.path.isfile(path):
            return context_builders['dockerfile']
    else:
        return None


# The actual contents of the tarball are not checked; this just makes sure the
# file exists and that this Python installation recognizes the format.
def is_tarball_context(path):
    if path is None:
        return False
    _path = path
    if isinstance(_path, six.binary_type):
        _path = _path.decode('utf-8')
    return (not os.path.isdir(_path) and (_path.endswith('.xz') or
                                          tarfile.is_tarfile(_path)))


def is_directory_context(path, dockerfile='Dockerfile'):
    dockerfile_path = os.path.abspath(os.path.join(path, dockerfile))
    return os.path.isdir(path) and os.path.isfile(dockerfile_path)
