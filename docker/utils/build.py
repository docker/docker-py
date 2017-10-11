import os

from ..constants import IS_WINDOWS_PLATFORM
from .fnmatch import fnmatch
from .utils import create_archive


def tar(path, exclude=None, dockerfile=None, fileobj=None, gzip=False):
    root = os.path.abspath(path)
    exclude = exclude or []

    return create_archive(
        files=sorted(exclude_paths(root, exclude, dockerfile=dockerfile)),
        root=root, fileobj=fileobj, gzip=gzip
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

    patterns = [p.lstrip('/') for p in patterns]
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
        set([dockerfile.replace('/', os.path.sep)])
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


def should_check_directory(directory_path, exclude_patterns, include_patterns):
    """
    Given a directory path, a list of exclude patterns, and a list of inclusion
    patterns:

    1. Returns True if the directory path should be included according to
       should_include.
    2. Returns True if the directory path is the prefix for an inclusion
       pattern
    3. Returns False otherwise
    """

    # To account for exception rules, check directories if their path is a
    # a prefix to an inclusion pattern. This logic conforms with the current
    # docker logic (2016-10-27):
    # https://github.com/docker/docker/blob/bc52939b0455116ab8e0da67869ec81c1a1c3e2c/pkg/archive/archive.go#L640-L671

    def normalize_path(path):
        return path.replace(os.path.sep, '/')

    path_with_slash = normalize_path(directory_path) + '/'
    possible_child_patterns = [
        pattern for pattern in map(normalize_path, include_patterns)
        if (pattern + '/').startswith(path_with_slash)
    ]
    directory_included = should_include(
        directory_path, exclude_patterns, include_patterns
    )
    return directory_included or len(possible_child_patterns) > 0


def get_paths(root, exclude_patterns, include_patterns, has_exceptions=False):
    paths = []

    for parent, dirs, files in os.walk(root, topdown=True, followlinks=False):
        parent = os.path.relpath(parent, root)
        if parent == '.':
            parent = ''

        # Remove excluded patterns from the list of directories to traverse
        # by mutating the dirs we're iterating over.
        # This looks strange, but is considered the correct way to skip
        # traversal. See https://docs.python.org/2/library/os.html#os.walk
        dirs[:] = [
            d for d in dirs if should_check_directory(
                os.path.join(parent, d), exclude_patterns, include_patterns
            )
        ]

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
    pattern = pattern.rstrip('/' + os.path.sep)
    if pattern:
        pattern = os.path.relpath(pattern)

    pattern_components = pattern.split(os.path.sep)
    if len(pattern_components) == 1 and IS_WINDOWS_PLATFORM:
        pattern_components = pattern.split('/')

    if '**' not in pattern:
        path_components = path.split(os.path.sep)[:len(pattern_components)]
    else:
        path_components = path.split(os.path.sep)
    return fnmatch('/'.join(path_components), '/'.join(pattern_components))
