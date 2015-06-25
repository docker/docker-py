from . import builds
from . import containers
from . import images

_client = None


def init(client):
    """
    Set a client object to be used by the efficiency module.

    **Params:**
        client: a `docker.Client` object that will be used globally by the
                module
    """
    global _client
    _client = client


def copy_to_fs(container, path, target='.'):
    """
    Copy file from container to filesystem

    **Params:**
        container_id: ID of the container to copy from
        path: path to the file in the container
        target: folder where file will be copied (default ".")
    """
    return containers.copy_to_fs(
        _client, container, path, target
    )


def start_auto_remove(container, *args, **kwargs):
    """
    Start a container and try to remove it when it's finished running,
    similar to using --autorm in the docker CLI.

    **Params:**
        container: ID of the container to be started
        args, kwargs: `Client.start()` arguments
    """
    return containers.start_auto_remove(
        _client, container
    )


def pull(repo, tag=None, insecure_registry=False, auth_config=None):
    """
    Pull an image and stream the response chunks as JSON objects.
    If an error is encountered during streaming, a DockerException will be
    raised.

    **Params:**
        repo: Name of the repository to pull
        tag:  Optional tag name to pull (default: latest)
        insecure_registry: Set to true if pulling from an insecure registry
        auth_config: Optional transient auth config object
    """
    return images.pull(
        _client, repo, tag, insecure_registry, auth_config
    )


def push(repo, tag=None, insecure_registry=False):
    """
    Push an image and stream the response chunks as JSON objects.
    If an error is encountered during streaming, a DockerException will be
    raised.

    **Params:**
        repo: Name of the repository to push
        tag:  Optional tag name to push (default: all)
        insecure_registry: Set to true if pulling from an insecure registry
        auth_config: Optional transient auth config object
    """
    return images.push(
        _client, repo, tag, insecure_registry
    )


def build(path, dockerfile='Dockerfile', **kwargs):
    """
    Build an image from the specified Dockerfile found in context indicated by
    `path`. If an error is encountered during streaming, a DockerException
    will be raised.

    **Params:**
        path: string pointing to the build context. Can be any of:
            * A readable directory containing a valid Dockerfile
            * A tarball (optionally compressed with gzip, xz or bzip2)
            * A valid Dockerfile
            * A valid URL for a remote build context.
        dockerfile: Name of the Dockerfile inside the context path.
                    Default: "Dockerfile"
        kwargs: Additional `docker.Client.build` arguments
    """
    return builds.build(_client, path, dockerfile, **kwargs)


get_build_id = builds.get_build_id
create_context_from_path = builds.create_context_from_path
