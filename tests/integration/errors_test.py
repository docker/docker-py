import pytest

from docker.errors import APIError

from .base import TEST_IMG, BaseAPIIntegrationTest


class ErrorsTest(BaseAPIIntegrationTest):
    def test_api_error_parses_json(self):
        container = self.client.create_container(TEST_IMG, ['sleep', '10'])
        self.client.start(container['Id'])
        with pytest.raises(APIError) as cm:
            self.client.remove_container(container['Id'])
        explanation = cm.value.explanation.lower()
        assert 'stop the container before' in explanation
        assert '{"message":' not in explanation
        self.client.remove_container(container['Id'], force=True)
