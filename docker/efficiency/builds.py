import json
import os
import re
import six
import tarfile
import collections

from . import tools
from .. import errors


build_success_re = r'^Successfully built ([a-f0-9]+)\n$'

# these prefixes are treated as remote by the docker daemon
# (ref: pkg/urlutil/*) as of v1.6.0
REMOTE_CONTEXT_PREFIXES = ["http://",
                           "https://",
                           "git://",
                           "git@",
                           "github.com/"]


def get_build_id(build_result, discard_logs=False):
    """ **Params:**
        * `build_result` is a python generator returned by `Client.build`
        * `discard_logs` (bool, default=False). If True, log lines will
          be discarded after they're processed. Limits memory footprint.
        **Returns** tuple:
            1. Image ID if found, None otherwise
            2. List of log lines
    """
    parsed_lines = []
    image_id = None
    for line in build_result:
        try:
            parsed_line = json.loads(line).get('stream', '')
            if not discard_logs:
                parsed_lines.append(parsed_line)
            match = re.match(build_success_re, line)
            if match:
                image_id = match.group(1)
        except ValueError:
            # sometimes all the data is sent on a single line
            # This ONLY works because every line is formatted as
            # {"stream": STRING}
            lines = re.findall('{\s*"stream"\s*:\s*"[^"]*"\s*}', line)
            return get_build_id(lines, discard_logs)

    return image_id, parsed_lines


BuildCtxTuple = collections.namedtuple(
    'BuildContext', ['format', 'path', 'dockerfile', 'job_params']
)


class BuildContext(BuildCtxTuple):
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
        raise errors.ContextError("'path' parameter cannot be None")
    if dockerfile is None:
        raise errors.ContextError("'dockerfile' parameter cannot be None")

    _dockerfile = dockerfile
    _path = path
    if isinstance(_dockerfile, six.string_types):
        _dockerfile = dockerfile.encode('utf-8')
    if isinstance(_path, six.string_types):
        _path = path.encode('utf-8')

    context_maker = detect_context_format(_path, _dockerfile)
    if context_maker is None:
        raise errors.ContextError(
            "Format not supported at {0} [dockerfile='{1}']".format(
                path, dockerfile
            )
        )

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
        raise errors.ContextError("{0}: {1}".format(path, ioe))

    if os.path.isdir(path):
        if dockerfile in os.listdir(path):
            return context_builders['directory']
        else:
            raise errors.ContextError(
                "Directory {0} does not contain a Dockerfile named {1}".format(
                    path, dockerfile
                )
            )
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


def build(client, path, dockerfile='Dockerfile', **kwargs):
    """
    Build an image from the specified Dockerfile found in context indicated by
    `path`. If an error is encountered during streaming, a DockerException
    will be raised.

    **Params:**
        client: a docker `Client` object
        path: string pointing to the build context. Can be any of:
            * A readable directory containing a valid Dockerfile
            * A tarball (optionally compressed with gzip, xz or bzip2)
            * A valid Dockerfile
            * A valid URL for a remote build context.
        dockerfile: Name of the Dockerfile inside the context path.
                    Default: "Dockerfile"
        kwargs: Additional `docker.Client.build` arguments
    """
    ctx = create_context_from_path(path, dockerfile)
    kwargs.update(ctx.job_params)
    gen = client.build(ctx.path, **kwargs)
    return tools.generator_parser(gen)
