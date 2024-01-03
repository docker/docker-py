import unittest

from .fake_api_client import make_fake_client
from .fake_api import FAKE_CONFIG_NAME

class CreateConfigsTest(unittest.TestCase):
    def test_create_config(self):
        client = make_fake_client()
        config = client.configs.create(name="super_config", data="config")
        assert config.__repr__() == f"<Config: '{FAKE_CONFIG_NAME}'>"
