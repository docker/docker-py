import json

from .. import errors


def _generator_parser(gen):
    for line in gen:
        status = json.loads(line)
        if status.get('error'):
            raise errors.DockerException(status.get('error'))
        yield status


def pull(client, repo, tag=None, insecure_registry=False, auth_config=None):
    """
    Pull an image and stream the response chunks as JSON objects.
    If an error is encountered during streaming, a DockerException will be
    raised.

    **Params:**
        client: a docker `Client` object
        repo: Name of the repository to pull
        tag:  Optional tag name to pull (default: latest)
        insecure_registry: Set to true if pulling from an insecure registry
        auth_config: Optional transient auth config object
    """
    gen = client.pull(
        repo, tag=tag, stream=True, insecure_registry=insecure_registry,
        auth_config=auth_config
    )

    return _generator_parser(gen)


def push(client, repo, tag=None, insecure_registry=False):
    """
    Push an image and stream the response chunks as JSON objects.
    If an error is encountered during streaming, a DockerException will be
    raised.

    **Params:**
        client: a docker `Client` object
        repo: Name of the repository to push
        tag:  Optional tag name to push (default: all)
        insecure_registry: Set to true if pulling from an insecure registry
        auth_config: Optional transient auth config object
    """
    gen = client.push(
        repo, tag=tag, stream=True, insecure_registry=insecure_registry
    )
    return _generator_parser(gen)
