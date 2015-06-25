import io
import tarfile


def copy_to_fs(client, container, path, target="."):
    """
    Copy file from container to filesystem

    **Params:**
        client: a docker `Client` object
        container_id: ID of the container to copy from
        path: path to the file in the container
        target: folder where file will be copied (default ".")
    """
    response = client.copy(container, path)
    buffer = io.BytesIO()
    buffer.write(response.data)
    buffer.seek(0)
    tar = tarfile.open(fileobj=buffer, mode='r|')
    tar.extractall(path=target)


def start_auto_remove(client, container, *args, **kwargs):
    """
    Start a container and try to remove it when it's finished running,
    similar to using --autorm in the docker CLI.
    **Params:**
        client: a docker `Client` object
        container: ID of the container to be started
        args, kwargs: `Client.start()` arguments
    """
    client.start(container, *args, **kwargs)
    if client.wait(container) == 0:
        return client.remove_container(container)
