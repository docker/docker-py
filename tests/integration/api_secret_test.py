# -*- coding: utf-8 -*-

import docker
import pytest

from ..helpers import force_leave_swarm, requires_api_version
from .base import BaseAPIIntegrationTest


@requires_api_version('1.25')
class SecretAPITest(BaseAPIIntegrationTest):
    def setUp(self):
        super(SecretAPITest, self).setUp()
        self.init_swarm()

    def tearDown(self):
        super(SecretAPITest, self).tearDown()
        force_leave_swarm(self.client)

    def test_create_secret(self):
        secret_id = self.client.create_secret(
            'favorite_character', 'sakuya izayoi'
        )
        self.tmp_secrets.append(secret_id)
        assert 'ID' in secret_id
        data = self.client.inspect_secret(secret_id)
        assert data['Spec']['Name'] == 'favorite_character'

    def test_create_secret_unicode_data(self):
        secret_id = self.client.create_secret(
            'favorite_character', u'いざよいさくや'
        )
        self.tmp_secrets.append(secret_id)
        assert 'ID' in secret_id
        data = self.client.inspect_secret(secret_id)
        assert data['Spec']['Name'] == 'favorite_character'

    def test_inspect_secret(self):
        secret_name = 'favorite_character'
        secret_id = self.client.create_secret(
            secret_name, 'sakuya izayoi'
        )
        self.tmp_secrets.append(secret_id)
        data = self.client.inspect_secret(secret_id)
        assert data['Spec']['Name'] == secret_name
        assert 'ID' in data
        assert 'Version' in data

    def test_remove_secret(self):
        secret_name = 'favorite_character'
        secret_id = self.client.create_secret(
            secret_name, 'sakuya izayoi'
        )
        self.tmp_secrets.append(secret_id)

        assert self.client.remove_secret(secret_id)
        with pytest.raises(docker.errors.NotFound):
            self.client.inspect_secret(secret_id)

    def test_list_secrets(self):
        secret_name = 'favorite_character'
        secret_id = self.client.create_secret(
            secret_name, 'sakuya izayoi'
        )
        self.tmp_secrets.append(secret_id)

        data = self.client.secrets(filters={'names': ['favorite_character']})
        assert len(data) == 1
        assert data[0]['ID'] == secret_id['ID']
