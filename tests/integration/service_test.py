import random

import docker
# import pytest

from ..base import requires_api_version
from .. import helpers


BUSYBOX = helpers.BUSYBOX


class ServiceTest(helpers.BaseTestCase):
    def setUp(self):
        super(ServiceTest, self).setUp()
        try:
            self.client.leave_swarm(force=True)
        except docker.errors.APIError:
            pass
        self.client.init_swarm('eth0')

    def tearDown(self):
        super(ServiceTest, self).tearDown()
        for service in self.client.services(filters={'name': 'dockerpytest_'}):
            try:
                self.client.remove_service(service['ID'])
            except docker.errors.APIError:
                pass
        try:
            self.client.leave_swarm(force=True)
        except docker.errors.APIError:
            pass

    def get_service_name(self):
        return 'dockerpytest_{0:x}'.format(random.getrandbits(64))

    def create_simple_service(self, name=None):
        if name:
            name = 'dockerpytest_{0}'.format(name)
        else:
            name = self.get_service_name()

        container_spec = docker.api.ContainerSpec('busybox', ['echo', 'hello'])
        task_tmpl = docker.api.TaskTemplate(container_spec)
        return name, self.client.create_service(task_tmpl, name=name)

    @requires_api_version('1.24')
    def test_list_services(self):
        services = self.client.services()
        assert isinstance(services, list)

        test_services = self.client.services(filters={'name': 'dockerpytest_'})
        assert len(test_services) == 0
        self.create_simple_service()
        test_services = self.client.services(filters={'name': 'dockerpytest_'})
        assert len(test_services) == 1
        assert 'dockerpytest_' in test_services[0]['Spec']['Name']

    def test_inspect_service_by_id(self):
        svc_name, svc_id = self.create_simple_service()
        svc_info = self.client.inspect_service(svc_id)
        assert 'ID' in svc_info
        assert svc_info['ID'] == svc_id['ID']

    def test_inspect_service_by_name(self):
        svc_name, svc_id = self.create_simple_service()
        svc_info = self.client.inspect_service(svc_name)
        assert 'ID' in svc_info
        assert svc_info['ID'] == svc_id['ID']

    def test_remove_service_by_id(self):
        svc_name, svc_id = self.create_simple_service()
        assert self.client.remove_service(svc_id)
        test_services = self.client.services(filters={'name': 'dockerpytest_'})
        assert len(test_services) == 0

    def test_rempve_service_by_name(self):
        svc_name, svc_id = self.create_simple_service()
        assert self.client.remove_service(svc_name)
        test_services = self.client.services(filters={'name': 'dockerpytest_'})
        assert len(test_services) == 0

    def test_create_service_simple(self):
        name, svc_id = self.create_simple_service()
        assert self.client.inspect_service(svc_id)
        services = self.client.services(filters={'name': name})
        assert len(services) == 1
        assert services[0]['ID'] == svc_id['ID']

    def test_update_service_name(self):
        name, svc_id = self.create_simple_service()
        svc_info = self.client.inspect_service(svc_id)
        svc_version = svc_info['Version']['Index']
        new_name = self.get_service_name()
        assert self.client.update_service(
            svc_id, svc_version, name=new_name,
            task_template=svc_info['Spec']['TaskTemplate']
        )
        svc_info = self.client.inspect_service(svc_id)
        assert svc_info['Spec']['Name'] == new_name
