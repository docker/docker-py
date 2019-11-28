import unittest

from .fake_api_client import make_fake_client
from .fake_api import FAKE_SECRET_ID


class CreateServiceTest(unittest.TestCase):
    def test_secrets_repr(self):
        client = make_fake_client()
        secret = client.secrets.create(name="test", data="secret")
        assert secret.__repr__() == "<Secret: '{}'>".format(FAKE_SECRET_ID)
