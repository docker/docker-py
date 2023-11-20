import unittest

from .fake_api import FAKE_NETWORK_ID, FAKE_CONTAINER_ID
from .fake_api_client import make_fake_client


class NetworkCollectionTest(unittest.TestCase):

    def test_create(self):
        client = make_fake_client()
        network = client.networks.create("foobar", labels={'foo': 'bar'})
        assert network.id == FAKE_NETWORK_ID
        client.api.inspect_network.assert_called_once_with(FAKE_NETWORK_ID)
        client.api.create_network.assert_called_once_with(
            "foobar",
            labels={'foo': 'bar'}
        )

    def test_get(self):
        client = make_fake_client()
        network = client.networks.get(FAKE_NETWORK_ID)
        assert network.id == FAKE_NETWORK_ID
        client.api.inspect_network.assert_called_once_with(FAKE_NETWORK_ID)

    def test_list(self):
        client = make_fake_client()
        networks = client.networks.list()
        assert networks[0].id == FAKE_NETWORK_ID
        client.api.networks.assert_called_once_with()

        client = make_fake_client()
        client.networks.list(ids=["abc"])
        client.api.networks.assert_called_once_with(ids=["abc"])

        client = make_fake_client()
        client.networks.list(names=["foobar"])
        client.api.networks.assert_called_once_with(names=["foobar"])


class NetworkTest(unittest.TestCase):

    def test_connect(self):
        client = make_fake_client()
        network = client.networks.get(FAKE_NETWORK_ID)
        network.connect(FAKE_CONTAINER_ID)
        client.api.connect_container_to_network.assert_called_once_with(
            FAKE_CONTAINER_ID,
            FAKE_NETWORK_ID
        )

    def test_disconnect(self):
        client = make_fake_client()
        network = client.networks.get(FAKE_NETWORK_ID)
        network.disconnect(FAKE_CONTAINER_ID)
        client.api.disconnect_container_from_network.assert_called_once_with(
            FAKE_CONTAINER_ID,
            FAKE_NETWORK_ID
        )

    def test_remove(self):
        client = make_fake_client()
        network = client.networks.get(FAKE_NETWORK_ID)
        network.remove()
        client.api.remove_network.assert_called_once_with(FAKE_NETWORK_ID)
