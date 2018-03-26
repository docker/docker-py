import io
import os
import re
import six
import tarfile
import tempfile

from ..constants import IS_WINDOWS_PLATFORM
from fnmatch import fnmatch
from itertools import chain


_SEP = re.compile('/|\\\\') if IS_WINDOWS_PLATFORM else re.compile('/')


def tar(path, exclude=None, dockerfile=None, fileobj=None, gzip=False):
    root = os.path.abspath(path)
    exclude = exclude or []
    dockerfile = dockerfile or (None, None)
    extra_files = []
    if dockerfile[1] is not None:
        dockerignore_contents = '\n'.join(
            (exclude or ['.dockerignore']) + [dockerfile[0]]
        )
        extra_files = [
            ('.dockerignore', dockerignore_contents),
            dockerfile,
        ]
    return create_archive(
        files=sorted(exclude_paths(root, exclude, dockerfile=dockerfile[0])),
        root=root, fileobj=fileobj, gzip=gzip, extra_files=extra_files
    )


def exclude_paths(root, patterns, dockerfile=None):
    """
    Given a root directory path and a list of .dockerignore patterns, return
    an iterator of all paths (both regular files and directories) in the root
    directory that do *not* match any of the patterns.

    All paths returned are relative to the root.
    """

    if dockerfile is None:
        dockerfile = 'Dockerfile'

    def split_path(p):
        return [pt for pt in re.split(_SEP, p) if pt and pt != '.']

    def normalize(p):
        # Leading and trailing slashes are not relevant. Yes,
        # "foo.py/" must exclude the "foo.py" regular file. "."
        # components are not relevant either, even if the whole
        # pattern is only ".", as the Docker reference states: "For
        # historical reasons, the pattern . is ignored."
        # ".." component must be cleared with the potential previous
        # component, regardless of whether it exists: "A preprocessing
        # step [...]  eliminates . and .. elements using Go's
        # filepath.".
        i = 0
        split = split_path(p)
        while i < len(split):
            if split[i] == '..':
                del split[i]
                if i > 0:
                    del split[i - 1]
                    i -= 1
            else:
                i += 1
        return split

    patterns = (
        (True, normalize(p[1:]))
        if p.startswith('!') else
        (False, normalize(p))
        for p in patterns)
    patterns = list(reversed(list(chain(
        # Exclude empty patterns such as "." or the empty string.
        filter(lambda p: p[1], patterns),
        # Always include the Dockerfile and .dockerignore
        [(True, split_path(dockerfile)), (True, ['.dockerignore'])]))))
    return set(walk(root, patterns))


def walk(root, patterns, default=True):
    """
    A collection of file lying below root that should be included according to
    patterns.
    """

    def match(p):
        if p[1][0] == '**':
            rec = (p[0], p[1][1:])
            return [p] + (match(rec) if rec[1] else [rec])
        elif fnmatch(f, p[1][0]):
            return [(p[0], p[1][1:])]
        else:
            return []

    for f in os.listdir(root):
        cur = os.path.join(root, f)
        # The patterns if recursing in that directory.
        sub = list(chain(*(match(p) for p in patterns)))
        # Whether this file is explicitely included / excluded.
        hit = next((p[0] for p in sub if not p[1]), None)
        # Whether this file is implicitely included / excluded.
        matched = default if hit is None else hit
        sub = list(filter(lambda p: p[1], sub))
        if os.path.isdir(cur) and not os.path.islink(cur):
            # Entirely skip directories if there are no chance any subfile will
            # be included.
            if all(not p[0] for p in sub) and not matched:
                continue
            # I think this would greatly speed up dockerignore handling by not
            # recursing into directories we are sure would be entirely
            # included, and only yielding the directory itself, which will be
            # recursively archived anyway. However the current unit test expect
            # the full list of subfiles and I'm not 100% sure it would make no
            # difference yet.
            # if all(p[0] for p in sub) and matched:
            #     yield f
            #     continue
            children = False
            for r in (os.path.join(f, p) for p in walk(cur, sub, matched)):
                yield r
                children = True
            # The current unit tests expect directories only under those
            # conditions. It might be simplifiable though.
            if (not sub or not children) and hit or hit is None and default:
                yield f
        elif matched:
            yield f


def build_file_list(root):
    files = []
    for dirname, dirnames, fnames in os.walk(root):
        for filename in fnames + dirnames:
            longpath = os.path.join(dirname, filename)
            files.append(
                longpath.replace(root, '', 1).lstrip('/')
            )

    return files


def create_archive(root, files=None, fileobj=None, gzip=False,
                   extra_files=None):
    extra_files = extra_files or []
    if not fileobj:
        fileobj = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w:gz' if gzip else 'w', fileobj=fileobj)
    if files is None:
        files = build_file_list(root)
    extra_names = set(e[0] for e in extra_files)
    for path in files:
        if path in extra_names:
            # Extra files override context files with the same name
            continue
        full_path = os.path.join(root, path)

        i = t.gettarinfo(full_path, arcname=path)
        if i is None:
            # This happens when we encounter a socket file. We can safely
            # ignore it and proceed.
            continue

        # Workaround https://bugs.python.org/issue32713
        if i.mtime < 0 or i.mtime > 8**11 - 1:
            i.mtime = int(i.mtime)

        if IS_WINDOWS_PLATFORM:
            # Windows doesn't keep track of the execute bit, so we make files
            # and directories executable by default.
            i.mode = i.mode & 0o755 | 0o111

        if i.isfile():
            try:
                with open(full_path, 'rb') as f:
                    t.addfile(i, f)
            except IOError:
                raise IOError(
                    'Can not read file in context: {}'.format(full_path)
                )
        else:
            # Directories, FIFOs, symlinks... don't need to be read.
            t.addfile(i, None)

    for name, contents in extra_files:
        info = tarfile.TarInfo(name)
        info.size = len(contents)
        t.addfile(info, io.BytesIO(contents.encode('utf-8')))

    t.close()
    fileobj.seek(0)
    return fileobj


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
