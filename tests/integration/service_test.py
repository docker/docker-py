import random

import docker

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

        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
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

    def test_remove_service_by_name(self):
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

    def test_create_service_custom_log_driver(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        log_cfg = docker.types.DriverConfig('none')
        task_tmpl = docker.types.TaskTemplate(
            container_spec, log_driver=log_cfg
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        res_template = svc_info['Spec']['TaskTemplate']
        assert 'LogDriver' in res_template
        assert 'Name' in res_template['LogDriver']
        assert res_template['LogDriver']['Name'] == 'none'

    def test_create_service_with_volume_mount(self):
        vol_name = self.get_service_name()
        container_spec = docker.types.ContainerSpec(
            'busybox', ['ls'],
            mounts=[
                docker.types.Mount(target='/test', source=vol_name)
            ]
        )
        self.tmp_volumes.append(vol_name)
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        cspec = svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert 'Mounts' in cspec
        assert len(cspec['Mounts']) == 1
        mount = cspec['Mounts'][0]
        assert mount['Target'] == '/test'
        assert mount['Source'] == vol_name
        assert mount['Type'] == 'volume'

    def test_create_service_with_resources_constraints(self):
        container_spec = docker.types.ContainerSpec('busybox', ['true'])
        resources = docker.types.Resources(
            cpu_limit=4000000, mem_limit=3 * 1024 * 1024 * 1024,
            cpu_reservation=3500000, mem_reservation=2 * 1024 * 1024 * 1024
        )
        task_tmpl = docker.types.TaskTemplate(
            container_spec, resources=resources
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        res_template = svc_info['Spec']['TaskTemplate']
        assert 'Resources' in res_template
        assert res_template['Resources']['Limits'] == resources['Limits']
        assert res_template['Resources']['Reservations'] == resources[
            'Reservations'
        ]

    def test_create_service_with_update_config(self):
        container_spec = docker.types.ContainerSpec('busybox', ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        update_config = docker.types.UpdateConfig(
            parallelism=10, delay=5, failure_action='pause'
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, update_config=update_config, name=name
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'UpdateConfig' in svc_info['Spec']
        assert update_config == svc_info['Spec']['UpdateConfig']

    def test_create_service_with_restart_policy(self):
        container_spec = docker.types.ContainerSpec('busybox', ['true'])
        policy = docker.types.RestartPolicy(
            docker.types.RestartPolicy.condition_types.ANY,
            delay=5, max_attempts=5
        )
        task_tmpl = docker.types.TaskTemplate(
            container_spec, restart_policy=policy
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'RestartPolicy' in svc_info['Spec']['TaskTemplate']
        assert policy == svc_info['Spec']['TaskTemplate']['RestartPolicy']

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
