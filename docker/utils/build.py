import os
import re

from ..constants import IS_WINDOWS_PLATFORM
from fnmatch import fnmatch
from itertools import chain
from .utils import create_archive


def tar(path, exclude=None, dockerfile=None, fileobj=None, gzip=False):
    root = os.path.abspath(path)
    exclude = exclude or []
    return create_archive(
        files=sorted(exclude_paths(root, exclude, dockerfile=dockerfile)),
        root=root, fileobj=fileobj, gzip=gzip
    )


_SEP = re.compile('/|\\\\') if IS_WINDOWS_PLATFORM else re.compile('/')


def exclude_paths(root, patterns, dockerfile=None):
    """
    Given a root directory path and a list of .dockerignore patterns, return
    an iterator of all paths (both regular files and directories) in the root
    directory that do *not* match any of the patterns.

    All paths returned are relative to the root.
    """

    if dockerfile is None:
        dockerfile = 'Dockerfile'

    def normalize(p):
        # Leading and trailing slashes are not relevant. Yes,
        # "foo.py/" must exclude the "foo.py" regular file. "."
        # components are not relevant either, even if the whole
        # pattern is only ".", as the Docker reference states: "For
        # historical reasons, the pattern . is ignored."
        split = [pt for pt in re.split(_SEP, p) if pt and pt != '.']
        # ".." component must be cleared with the potential previous
        # component, regardless of whether it exists: "A preprocessing
        # step [...]  eliminates . and .. elements using Go's
        # filepath.".
        i = 0
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
        [(True, dockerfile.split('/')), (True, ['.dockerignore'])]))))
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
        if os.path.isdir(cur):
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
