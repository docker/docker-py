import unittest

from .fake_api_client import make_fake_client
from .fake_api import FAKE_SECRET_NAME


class CreateServiceTest(unittest.TestCase):
    def test_secrets_repr(self):
        client = make_fake_client()
        secret = client.secrets.create(name="super_secret", data="secret")
        assert secret.__repr__() == f"<Secret: '{FAKE_SECRET_NAME}'>"
