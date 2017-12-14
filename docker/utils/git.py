import tempfile
import shutil
import subprocess
import requests
import os
import logging
import re

try:
    from urlparse import urlparse, urlunparse
except ImportError:
    from urllib.parse import urlparse, urlunparse

from . import tar
from ..errors import GitError


log = logging.getLogger(__name__)


def is_git_url(path):
    """Determines if the provided path is a git URL.

    Args:
        path (str): Path to evaluate

    Returns:
        bool: True, if the path is a valid Git URL
    """
    return path.startswith(("git://", "git@", "github.com/")) or (
        path.startswith(("http://", "https://")) and
        bool(re.search("\.git(?:#.+)?$", path))
    )


def make_git_build_context(git_url, **kwargs):
    """Makes a build context out of a git URL

    Args:
        git_url: URL to the Git repository
        **kwargs: Keyword args passed to `tar`

    Returns:
        A tar archive file object
    """
    root_dir = tempfile.mkdtemp(prefix='docker-build-git')
    try:
        context_dir = clone(git_url, root_dir)

        dockerignore = os.path.join(context_dir, '.dockerignore')
        exclude = None
        if os.path.exists(dockerignore):
            with open(dockerignore, 'r') as f:
                exclude = list(filter(bool, f.read().splitlines()))

        fileobj = tar(context_dir, exclude=exclude, **kwargs)
    finally:
        if os.path.exists(root_dir):
            shutil.rmtree(root_dir)

    return fileobj


def clone(remote_url, dest_dir):
    """Clones a repository into the destination directory

    Returns:
        str: A local path to the build context
    """
    if remote_url.startswith("github.com/"):
        remote_url = 'https://' + remote_url

    url = urlparse(remote_url)

    clone_args = get_clone_args(url, dest_dir)
    git(*clone_args)

    return checkout(url.fragment, dest_dir)


def get_clone_args(url, root_dir):
    """Gets the git arguments to clone a repository into a new directory

    Args:
        url (urlparse.ParseResult): the repository url to clone
        root_dir (str): the directory to clone into

    Returns:
        list: A list of git arguments to clone the repository
    """
    args = ["clone", "--recursive"]
    shallow = len(url.fragment) == 0

    if shallow and url.scheme.startswith("http"):
        smart_http_url = "%s/info/refs?service=git-upload-pack" % \
                         urlunparse(url)
        resp = requests.get(smart_http_url, allow_redirects=True)
        if resp.headers.get("Content-Type", "") != \
                "application/x-git-upload-pack-advertisement":
            shallow = False

    if shallow:
        args += ["--depth", "1"]

    if url.fragment:
        url = (url.scheme, url.netloc, url.path, url.params, url.query, "")

    return args + [urlunparse(url), root_dir]


def checkout(fragment, root_dir):
    """Checks out a git reference into the root directory

    Args:
        fragment (str): the URL fragment specifying the directory to checkout
        root_dir: the root directory of the cloned repository

    Returns:
        str: A local path to the build context

    Raises:
        :py:class:`docker.errors.GitError`
            if checking out the git reference fails
    """
    try:
        ref, context_dir = fragment.split(':', 1)
    except ValueError:
        ref, context_dir = fragment, ""

    if ref:
        git_within_dir(root_dir, "checkout", ref)

    if context_dir:
        full_context_dir = os.path.join(root_dir, context_dir)
        if not os.path.isdir(full_context_dir):
            raise GitError("Error setting git context, "
                           "%s not a directory in git root" % context_dir)

        root_dir = full_context_dir

    return root_dir


def git_within_dir(root_dir, *args):
    return git("--work-tree", root_dir, "--git-dir",
               os.path.join(root_dir, ".git"), *args)


def git(*args):
    """Executes the git command in a subprocess with the specified args

    Args:
        *args (tuple): Variable length string arguments passed to git command

    Returns:
        True if successful

    Raises:
        :py:class:`docker.errors.GitError`
            if the git process returns with a non-zero exit code
    """
    log.debug("Executing: git %s", " ".join(args))
    return_code = subprocess.call(("git",) + args)
    if return_code != 0:
        raise GitError("Error trying to use git: exit status %d" % return_code)

    return True
