from docker.errors import APIError
from .. import helpers


class ErrorsTest(helpers.BaseTestCase):
    def test_api_error_parses_json(self):
        container = self.client.create_container(
            helpers.BUSYBOX,
            ['sleep', '10']
        )
        self.client.start(container['Id'])
        with self.assertRaises(APIError) as cm:
            self.client.remove_container(container['Id'])
        explanation = cm.exception.explanation
        assert 'You cannot remove a running container' in explanation
        assert '{"message":' not in explanation
        self.client.remove_container(container['Id'], force=True)
