import os
import re
import tarfile
from collections import namedtuple
from .utils import lazy_line_reader

lzma = None
try:
    import lzma
except ImportError as ie:
    try:
        import backports.lzma as lzma
    except ImportError:
        pass


class ContextError(Exception):
    def __init__(self, msg):
        self.message = msg


INVALID_CONTEXT_FORMAT_LONG_FMT = """
Build context at %s is not supported by docker-compose\\n
The path must point to either:
\t * A readable directory containing a valid Dockerfile
\t * A tarball (optionally compressed with gzip, xz or bzip2)
\t * A valid Dockerfile
\t * A valid URL for a remote build context.
%s"""

INVALID_FIRST_INSTRUCTION_FMT = """
Invalid first instruction in Dockerfile %s: '%s'\\n
The first instruction in a Dockerfile must be "FROM ..."""

# these prefixes are treated as remote by the docker daemon
# (ref: pkg/urlutil/*) as of v1.6.0
REMOTE_CONTEXT_PREFIXES = ["http://",
                           "https://",
                           "git://",
                           "git@",
                           "github.com/"]

DOCKERFILE_CMD_RG = re.compile(r"[\t\s]*\\n$|([\s\t]*"
                               r"FROM|MAINTAINER|RUN|CMD|EXPOSE|ENV|ADD|COPY|"
                               r"ENTRYPOINT|VOLUME|USER|WORKDIR|ONBUILD"
                               r"[\s\t]+.+)")


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
    context_maker = detect_context_format(path, dockerfile)
    if context_maker is None:
        raise ContextError("Format not supported at "
                           "%s [dockerfile='%s']." % (path, dockerfile))

    return context_maker(path, dockerfile)


def is_remote(path):
    for prefix in REMOTE_CONTEXT_PREFIXES:
        if path.startswith(prefix):
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
        try:
            if validate_dockerfile_head(path):
                return context_builders['dockerfile']
        except ContextError as e:
            raise e
    else:
        return None


# The actual contents of the tarball are not checked; this just makes sure the
# file exists and that this Python installation recognizes the format.
def is_tarball_context(path):
    if os.path.isdir(path):
        return False

    if tarfile.is_tarfile(path):
        return True

    if lzma is not None:
        try:
            with lzma.LZMAFile(path) as xzfile:
                xzfile.peek(0)
                return True
        except lzma.LZMAError:
            pass
    return False


def is_directory_context(path, dockerfile='Dockerfile'):
    return (
        os.path.isdir(path) and
        dockerfile in os.listdir(path) and
        validate_dockerfile_head(os.path.join(path, dockerfile))
    )


def validate_dockerfile_head(fpath):
    with open(fpath, 'r') as candidate:
        line_reader = lazy_line_reader(candidate)
        first_line = _read_first_instruction_line(line_reader)
        try:
            if not first_line.startswith("FROM"):
                raise ContextError(INVALID_FIRST_INSTRUCTION_FMT %
                                   (fpath, first_line))
        except UnicodeDecodeError:
            return False
    return True


def _read_first_instruction_line(line_reader, marker=r'^[\s\t]*(\#|$)'):
    import re
    cmt_regex = re.compile(marker)
    for line in line_reader:
        if cmt_regex.findall(line):
            continue
        else:
            break

    return line  # only in python...
