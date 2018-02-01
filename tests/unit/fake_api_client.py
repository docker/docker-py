import copy
import docker

from . import fake_api

try:
    from unittest import mock
except ImportError:
    import mock


class CopyReturnMagicMock(mock.MagicMock):
    """
    A MagicMock which deep copies every return value.
    """
    def _mock_call(self, *args, **kwargs):
        ret = super(CopyReturnMagicMock, self)._mock_call(*args, **kwargs)
        if isinstance(ret, (dict, list)):
            ret = copy.deepcopy(ret)
        return ret


def make_fake_api_client():
    """
    Returns non-complete fake APIClient.

    This returns most of the default cases correctly, but most arguments that
    change behaviour will not work.
    """
    api_client = docker.APIClient()
    mock_client = CopyReturnMagicMock(**{
        'build.return_value': fake_api.FAKE_IMAGE_ID,
        'commit.return_value': fake_api.post_fake_commit()[1],
        'containers.return_value': fake_api.get_fake_containers()[1],
        'create_container.return_value':
            fake_api.post_fake_create_container()[1],
        'create_host_config.side_effect': api_client.create_host_config,
        'create_network.return_value': fake_api.post_fake_network()[1],
        'exec_create.return_value': fake_api.post_fake_exec_create()[1],
        'exec_start.return_value': fake_api.post_fake_exec_start()[1],
        'images.return_value': fake_api.get_fake_images()[1],
        'inspect_container.return_value':
            fake_api.get_fake_inspect_container()[1],
        'inspect_image.return_value': fake_api.get_fake_inspect_image()[1],
        'inspect_network.return_value': fake_api.get_fake_network()[1],
        'logs.return_value': [b'hello world\n'],
        'networks.return_value': fake_api.get_fake_network_list()[1],
        'start.return_value': None,
        'wait.return_value': {'StatusCode': 0},
    })
    mock_client._version = docker.constants.DEFAULT_DOCKER_API_VERSION
    return mock_client


def make_fake_client():
    """
    Returns a Client with a fake APIClient.
    """
    client = docker.DockerClient()
    client.api = make_fake_api_client()
    return client
