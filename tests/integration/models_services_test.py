import unittest

import docker
import pytest

from .. import helpers
from .base import TEST_API_VERSION


class ServiceTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        client = docker.from_env(version=TEST_API_VERSION)
        helpers.force_leave_swarm(client)
        client.swarm.init('127.0.0.1', listen_addr=helpers.swarm_listen_addr())

    @classmethod
    def tearDownClass(cls):
        helpers.force_leave_swarm(docker.from_env(version=TEST_API_VERSION))

    def test_create(self):
        client = docker.from_env(version=TEST_API_VERSION)
        name = helpers.random_name()
        service = client.services.create(
            # create arguments
            name=name,
            labels={'foo': 'bar'},
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300",
            container_labels={'container': 'label'}
        )
        assert service.name == name
        assert service.attrs['Spec']['Labels']['foo'] == 'bar'
        container_spec = service.attrs['Spec']['TaskTemplate']['ContainerSpec']
        assert "alpine" in container_spec['Image']
        assert container_spec['Labels'] == {'container': 'label'}

    def test_get(self):
        client = docker.from_env(version=TEST_API_VERSION)
        name = helpers.random_name()
        service = client.services.create(
            name=name,
            image="alpine",
            command="sleep 300"
        )
        service = client.services.get(service.id)
        assert service.name == name

    def test_list_remove(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            name=helpers.random_name(),
            image="alpine",
            command="sleep 300"
        )
        assert service in client.services.list()
        service.remove()
        assert service not in client.services.list()

    def test_tasks(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service1 = client.services.create(
            name=helpers.random_name(),
            image="alpine",
            command="sleep 300"
        )
        service2 = client.services.create(
            name=helpers.random_name(),
            image="alpine",
            command="sleep 300"
        )
        tasks = []
        while len(tasks) == 0:
            tasks = service1.tasks()
        assert len(tasks) == 1
        assert tasks[0]['ServiceID'] == service1.id

        tasks = []
        while len(tasks) == 0:
            tasks = service2.tasks()
        assert len(tasks) == 1
        assert tasks[0]['ServiceID'] == service2.id

    @pytest.mark.skip(reason="Makes Swarm unstable?")
    def test_update(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        service.update(
            # create argument
            name=service.name,
            # ContainerSpec argument
            command="sleep 600"
        )
        service.reload()
        container_spec = service.attrs['Spec']['TaskTemplate']['ContainerSpec']
        assert container_spec['Command'] == ["sleep", "600"]
