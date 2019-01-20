import unittest

import docker
import pytest

from .. import helpers
from .base import TEST_API_VERSION
from docker.errors import InvalidArgument
from docker.types.services import ServiceMode


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

    def test_create_with_network(self):
        client = docker.from_env(version=TEST_API_VERSION)
        name = helpers.random_name()
        network = client.networks.create(
            helpers.random_name(), driver='overlay'
        )
        service = client.services.create(
            # create arguments
            name=name,
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300",
            networks=[network.id]
        )
        assert 'Networks' in service.attrs['Spec']['TaskTemplate']
        networks = service.attrs['Spec']['TaskTemplate']['Networks']
        assert len(networks) == 1
        assert networks[0]['Target'] == network.id

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

    def test_update_retains_service_labels(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            labels={'service.label': 'SampleLabel'},
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
        labels = service.attrs['Spec']['Labels']
        assert labels == {'service.label': 'SampleLabel'}

    def test_update_retains_container_labels(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300",
            container_labels={'container.label': 'SampleLabel'}
        )
        service.update(
            # create argument
            name=service.name,
            # ContainerSpec argument
            command="sleep 600"
        )
        service.reload()
        container_spec = service.attrs['Spec']['TaskTemplate']['ContainerSpec']
        assert container_spec['Labels'] == {'container.label': 'SampleLabel'}

    def test_update_remove_service_labels(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            labels={'service.label': 'SampleLabel'},
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        service.update(
            # create argument
            name=service.name,
            labels={},
            # ContainerSpec argument
            command="sleep 600"
        )
        service.reload()
        assert not service.attrs['Spec'].get('Labels')

    @pytest.mark.xfail(reason='Flaky test')
    def test_update_retains_networks(self):
        client = docker.from_env(version=TEST_API_VERSION)
        network_name = helpers.random_name()
        network = client.networks.create(
            network_name, driver='overlay'
        )
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            networks=[network.id],
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        service.reload()
        service.update(
            # create argument
            name=service.name,
            # ContainerSpec argument
            command="sleep 600"
        )
        service.reload()
        networks = service.attrs['Spec']['TaskTemplate']['Networks']
        assert networks == [{'Target': network.id}]

    def test_scale_service(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        tasks = []
        while len(tasks) == 0:
            tasks = service.tasks()
        assert len(tasks) == 1
        service.update(
            mode=docker.types.ServiceMode('replicated', replicas=2),
        )
        while len(tasks) == 1:
            tasks = service.tasks()
        assert len(tasks) >= 2
        # check that the container spec is not overridden with None
        service.reload()
        spec = service.attrs['Spec']['TaskTemplate']['ContainerSpec']
        assert spec.get('Command') == ['sleep', '300']

    def test_scale_method_service(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300",
        )
        tasks = []
        while len(tasks) == 0:
            tasks = service.tasks()
        assert len(tasks) == 1
        service.scale(2)
        while len(tasks) == 1:
            tasks = service.tasks()
        assert len(tasks) >= 2
        # check that the container spec is not overridden with None
        service.reload()
        spec = service.attrs['Spec']['TaskTemplate']['ContainerSpec']
        assert spec.get('Command') == ['sleep', '300']

    def test_scale_method_global_service(self):
        client = docker.from_env(version=TEST_API_VERSION)
        mode = ServiceMode('global')
        service = client.services.create(
            name=helpers.random_name(),
            image="alpine",
            command="sleep 300",
            mode=mode
        )
        tasks = []
        while len(tasks) == 0:
            tasks = service.tasks()
        assert len(tasks) == 1
        with pytest.raises(InvalidArgument):
            service.scale(2)

        assert len(tasks) == 1
        service.reload()
        spec = service.attrs['Spec']['TaskTemplate']['ContainerSpec']
        assert spec.get('Command') == ['sleep', '300']

    @helpers.requires_api_version('1.25')
    def test_force_update_service(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        initial_version = service.version
        assert service.update(
            # create argument
            name=service.name,
            # task template argument
            force_update=10,
            # ContainerSpec argument
            command="sleep 600"
        )
        service.reload()
        assert service.version > initial_version

    @helpers.requires_api_version('1.25')
    def test_force_update_service_using_bool(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        initial_version = service.version
        assert service.update(
            # create argument
            name=service.name,
            # task template argument
            force_update=True,
            # ContainerSpec argument
            command="sleep 600"
        )
        service.reload()
        assert service.version > initial_version

    @helpers.requires_api_version('1.25')
    def test_force_update_service_using_shorthand_method(self):
        client = docker.from_env(version=TEST_API_VERSION)
        service = client.services.create(
            # create arguments
            name=helpers.random_name(),
            # ContainerSpec arguments
            image="alpine",
            command="sleep 300"
        )
        initial_version = service.version
        assert service.force_update()
        service.reload()
        assert service.version > initial_version
