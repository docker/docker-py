# -*- coding: utf-8 -*-

import docker
import pytest

from ..helpers import force_leave_swarm, requires_api_version
from .base import BaseAPIIntegrationTest


@requires_api_version('1.30')
class ConfigAPITest(BaseAPIIntegrationTest):
    @classmethod
    def setup_class(cls):
        client = cls.get_client_instance()
        force_leave_swarm(client)
        cls._init_swarm(client)

    @classmethod
    def teardown_class(cls):
        client = cls.get_client_instance()
        force_leave_swarm(client)

    def test_create_config(self):
        config_id = self.client.create_config(
            'favorite_character', 'sakuya izayoi'
        )
        self.tmp_configs.append(config_id)
        assert 'ID' in config_id
        data = self.client.inspect_config(config_id)
        assert data['Spec']['Name'] == 'favorite_character'

    def test_create_config_unicode_data(self):
        config_id = self.client.create_config(
            'favorite_character', u'いざよいさくや'
        )
        self.tmp_configs.append(config_id)
        assert 'ID' in config_id
        data = self.client.inspect_config(config_id)
        assert data['Spec']['Name'] == 'favorite_character'

    def test_inspect_config(self):
        config_name = 'favorite_character'
        config_id = self.client.create_config(
            config_name, 'sakuya izayoi'
        )
        self.tmp_configs.append(config_id)
        data = self.client.inspect_config(config_id)
        assert data['Spec']['Name'] == config_name
        assert 'ID' in data
        assert 'Version' in data

    def test_remove_config(self):
        config_name = 'favorite_character'
        config_id = self.client.create_config(
            config_name, 'sakuya izayoi'
        )
        self.tmp_configs.append(config_id)

        assert self.client.remove_config(config_id)
        with pytest.raises(docker.errors.NotFound):
            self.client.inspect_config(config_id)

    def test_list_configs(self):
        config_name = 'favorite_character'
        config_id = self.client.create_config(
            config_name, 'sakuya izayoi'
        )
        self.tmp_configs.append(config_id)

        data = self.client.configs(filters={'name': ['favorite_character']})
        assert len(data) == 1
        assert data[0]['ID'] == config_id['ID']
