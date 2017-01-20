import unittest

from .fake_api import FAKE_CONTAINER_ID
from .fake_api_client import make_fake_client


class ModelTest(unittest.TestCase):
    def test_reload(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.attrs['Name'] = "oldname"
        container.reload()
        assert client.api.inspect_container.call_count == 2
        assert container.attrs['Name'] == "foobar"

    def test_hash(self):
        client = make_fake_client()
        container1 = client.containers.get(FAKE_CONTAINER_ID)
        my_set = set([container1])
        assert len(my_set) == 1

        container2 = client.containers.get(FAKE_CONTAINER_ID)
        my_set.add(container2)
        assert len(my_set) == 1

        image1 = client.images.get(FAKE_CONTAINER_ID)
        my_set.add(image1)
        assert len(my_set) == 2
