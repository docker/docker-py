import json
import unittest
from unittest import mock

import pytest

from docker.errors import InvalidVersion
from docker.types import EndpointConfig

from .api_test import BaseAPIClientTest


class NetworkGatewayPriorityTest(BaseAPIClientTest):
    """Tests for the gw-priority feature in network operations."""

    def test_connect_container_to_network_with_gw_priority(self):
        """Test connecting a container to a network with gateway priority."""
        network_id = 'abc12345'
        container_id = 'def45678'
        gw_priority = 100

        # Create a mock response object
        fake_resp = mock.Mock()
        fake_resp.status_code = 201
        # If the response is expected to have JSON content, mock the json() method
        # fake_resp.json = mock.Mock(return_value={}) # Example if JSON is needed

        post = mock.Mock(return_value=fake_resp)

        # Mock the API version to be >= 1.48 for this test
        with mock.patch.object(self.client, '_version', '1.48'):
            with mock.patch('docker.api.client.APIClient.post', post):
                self.client.connect_container_to_network(
                    container={'Id': container_id},
                    net_id=network_id,
                    gw_priority=gw_priority
                )

        # Verify the API call was made correctly
        # The version in the URL will be based on the client's _version at the time of _url() call
        # which happens inside connect_container_to_network.
        # Since we patched _version to '1.48', the URL should reflect that.
        assert post.call_args[0][0] == f"http+docker://localhost/v1.48/networks/{network_id}/connect"

        data = json.loads(post.call_args[1]['data'])
        assert data['Container'] == container_id
        assert data['EndpointConfig']['GwPriority'] == gw_priority

    def test_connect_container_to_network_with_gw_priority_and_other_params(self):
        """Test connecting with gw_priority alongside other parameters."""
        network_id = 'abc12345'
        container_id = 'def45678'
        gw_priority = 200

        # Create a mock response object
        fake_resp = mock.Mock()
        fake_resp.status_code = 201
        # If the response is expected to have JSON content, mock the json() method
        # fake_resp.json = mock.Mock(return_value={}) # Example if JSON is needed

        post = mock.Mock(return_value=fake_resp)
        # Mock the API version to be >= 1.48 for this test
        with mock.patch.object(self.client, '_version', '1.48'):
            with mock.patch('docker.api.client.APIClient.post', post):
                self.client.connect_container_to_network(
                    container={'Id': container_id},
                    net_id=network_id,
                    aliases=['web', 'app'],
                    ipv4_address='192.168.1.100',
                    gw_priority=gw_priority
                )

        data = json.loads(post.call_args[1]['data'])
        endpoint_config = data['EndpointConfig']

        assert endpoint_config['GwPriority'] == gw_priority
        assert endpoint_config['Aliases'] == ['web', 'app']
        assert endpoint_config['IPAMConfig']['IPv4Address'] == '192.168.1.100'

    def test_create_endpoint_config_with_gw_priority(self):
        """Test creating endpoint config with gateway priority."""
        # Mock the API version to be >= 1.48 for this test
        with mock.patch.object(self.client, '_version', '1.48'):
            config = self.client.create_endpoint_config(
                gw_priority=150
            )
        assert config['GwPriority'] == 150

    def test_gw_priority_validation_type_error(self):
        """Test that gw_priority must be an integer."""
        # Mock the API version to be >= 1.48 for this test
        with mock.patch.object(self.client, '_version', '1.48'):
            with pytest.raises(TypeError, match='gw_priority must be an integer'):
                self.client.create_endpoint_config(gw_priority="100")

    def test_gw_priority_valid_values(self):
        """Test that various integer values for gw_priority work correctly."""
        # Mock the API version to be >= 1.48 for this test
        with mock.patch.object(self.client, '_version', '1.48'):
            # Test a positive value
            config_positive = self.client.create_endpoint_config(gw_priority=100)
            assert config_positive['GwPriority'] == 100

            # Test zero
            config_zero = self.client.create_endpoint_config(gw_priority=0)
            assert config_zero['GwPriority'] == 0

            # Test a negative value
            config_negative = self.client.create_endpoint_config(gw_priority=-50)
            assert config_negative['GwPriority'] == -50

            # Test a large positive value
            config_large_positive = self.client.create_endpoint_config(gw_priority=70000)
            assert config_large_positive['GwPriority'] == 70000

            # Test a large negative value
            config_large_negative = self.client.create_endpoint_config(gw_priority=-70000)
            assert config_large_negative['GwPriority'] == -70000


class EndpointConfigGatewayPriorityTest(unittest.TestCase):
    """Test EndpointConfig class with gateway priority."""

    def test_endpoint_config_with_gw_priority_supported_version(self):
        """Test EndpointConfig with gw_priority on supported API version."""
        config = EndpointConfig(
            version='1.48',  # Updated API version
            gw_priority=300
        )
        assert config['GwPriority'] == 300

    def test_endpoint_config_with_gw_priority_unsupported_version(self):
        """Test that gw_priority raises error on unsupported API version."""
        with pytest.raises(InvalidVersion, match='gw_priority is not supported for API version < 1.48'): # Updated API version
            EndpointConfig(
                version='1.47', # Updated API version
                gw_priority=300
            )

    def test_endpoint_config_without_gw_priority(self):
        """Test that EndpointConfig works normally without gw_priority."""
        config = EndpointConfig(
            version='1.48', # Updated API version
            aliases=['test'],
            ipv4_address='192.168.1.100'
        )
        assert 'GwPriority' not in config
        assert config['Aliases'] == ['test']
        assert config['IPAMConfig']['IPv4Address'] == '192.168.1.100'

    def test_endpoint_config_gw_priority_type_validation(self):
        """Test type validation for gw_priority in EndpointConfig."""
        with pytest.raises(TypeError, match='gw_priority must be an integer'):
            EndpointConfig(version='1.48', gw_priority='not_an_int') # Updated API version

    def test_endpoint_config_gw_priority_valid_values(self):
        """Test that various integer values for gw_priority work correctly in EndpointConfig."""
        # Test a positive value
        config_positive = EndpointConfig(version='1.48', gw_priority=100)
        assert config_positive['GwPriority'] == 100

        # Test zero
        config_zero = EndpointConfig(version='1.48', gw_priority=0)
        assert config_zero['GwPriority'] == 0

        # Test a negative value
        config_negative = EndpointConfig(version='1.48', gw_priority=-50)
        assert config_negative['GwPriority'] == -50

        # Test a large positive value
        config_large_positive = EndpointConfig(version='1.48', gw_priority=70000)
        assert config_large_positive['GwPriority'] == 70000

        # Test a large negative value
        config_large_negative = EndpointConfig(version='1.48', gw_priority=-70000)
        assert config_large_negative['GwPriority'] == -70000
