# -*- coding: utf-8 -*-

import random
import time

import docker
import pytest
import six

from ..helpers import (
    force_leave_swarm, requires_api_version, requires_experimental
)
from .base import BaseAPIIntegrationTest, BUSYBOX


class ServiceTest(BaseAPIIntegrationTest):
    @classmethod
    def setup_class(cls):
        client = cls.get_client_instance()
        force_leave_swarm(client)
        cls._init_swarm(client)

    @classmethod
    def teardown_class(cls):
        client = cls.get_client_instance()
        force_leave_swarm(client)

    def tearDown(self):
        for service in self.client.services(filters={'name': 'dockerpytest_'}):
            try:
                self.client.remove_service(service['ID'])
            except docker.errors.APIError:
                pass
        super(ServiceTest, self).tearDown()

    def get_service_name(self):
        return 'dockerpytest_{0:x}'.format(random.getrandbits(64))

    def get_service_container(self, service_name, attempts=20, interval=0.5,
                              include_stopped=False):
        # There is some delay between the service's creation and the creation
        # of the service's containers. This method deals with the uncertainty
        # when trying to retrieve the container associated with a service.
        while True:
            containers = self.client.containers(
                filters={'name': [service_name]}, quiet=True,
                all=include_stopped
            )
            if len(containers) > 0:
                return containers[0]
            attempts -= 1
            if attempts <= 0:
                return None
            time.sleep(interval)

    def create_simple_service(self, name=None, labels=None):
        if name:
            name = 'dockerpytest_{0}'.format(name)
        else:
            name = self.get_service_name()

        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        return name, self.client.create_service(
            task_tmpl, name=name, labels=labels
        )

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

    @requires_api_version('1.24')
    def test_list_services_filter_by_label(self):
        test_services = self.client.services(filters={'label': 'test_label'})
        assert len(test_services) == 0
        self.create_simple_service(labels={'test_label': 'testing'})
        test_services = self.client.services(filters={'label': 'test_label'})
        assert len(test_services) == 1
        assert test_services[0]['Spec']['Labels']['test_label'] == 'testing'

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

    @requires_api_version('1.29')
    def test_inspect_service_insert_defaults(self):
        svc_name, svc_id = self.create_simple_service()
        svc_info = self.client.inspect_service(svc_id)
        svc_info_defaults = self.client.inspect_service(
            svc_id, insert_defaults=True
        )
        assert svc_info != svc_info_defaults
        assert 'RollbackConfig' in svc_info_defaults['Spec']
        assert 'RollbackConfig' not in svc_info['Spec']

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

    @requires_api_version('1.25')
    @requires_experimental(until='1.29')
    def test_service_logs(self):
        name, svc_id = self.create_simple_service()
        assert self.get_service_container(name, include_stopped=True)
        attempts = 20
        while True:
            if attempts == 0:
                self.fail('No service logs produced by endpoint')
                return
            logs = self.client.service_logs(svc_id, stdout=True, is_tty=False)
            try:
                log_line = next(logs)
            except StopIteration:
                attempts -= 1
                time.sleep(0.1)
                continue
            else:
                break

        if six.PY3:
            log_line = log_line.decode('utf-8')
        assert 'hello\n' in log_line

    def test_create_service_custom_log_driver(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['echo', 'hello']
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
            BUSYBOX, ['ls'],
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
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
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

    def _create_service_with_generic_resources(self, generic_resources):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])

        resources = docker.types.Resources(
            generic_resources=generic_resources
        )
        task_tmpl = docker.types.TaskTemplate(
            container_spec, resources=resources
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        return resources, self.client.inspect_service(svc_id)

    @requires_api_version('1.32')
    def test_create_service_with_generic_resources(self):
        successful = [{
            'input': [
                {'DiscreteResourceSpec': {'Kind': 'gpu', 'Value': 1}},
                {'NamedResourceSpec': {'Kind': 'gpu', 'Value': 'test'}}
            ]}, {
            'input': {'gpu': 2, 'mpi': 'latest'},
            'expected': [
                {'DiscreteResourceSpec': {'Kind': 'gpu', 'Value': 2}},
                {'NamedResourceSpec': {'Kind': 'mpi', 'Value': 'latest'}}
            ]}
        ]

        for test in successful:
            t = test['input']
            resrcs, svc_info = self._create_service_with_generic_resources(t)

            assert 'TaskTemplate' in svc_info['Spec']
            res_template = svc_info['Spec']['TaskTemplate']
            assert 'Resources' in res_template
            res_reservations = res_template['Resources']['Reservations']
            assert res_reservations == resrcs['Reservations']
            assert 'GenericResources' in res_reservations

            def _key(d, specs=('DiscreteResourceSpec', 'NamedResourceSpec')):
                return [d.get(s, {}).get('Kind', '') for s in specs]

            actual = res_reservations['GenericResources']
            expected = test.get('expected', test['input'])
            assert sorted(actual, key=_key) == sorted(expected, key=_key)

    @requires_api_version('1.32')
    def test_create_service_with_invalid_generic_resources(self):
        for test_input in ['1', 1.0, lambda: '1', {1, 2}]:
            with pytest.raises(docker.errors.InvalidArgument):
                self._create_service_with_generic_resources(test_input)

    def test_create_service_with_update_config(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
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
        uc = svc_info['Spec']['UpdateConfig']
        assert update_config['Parallelism'] == uc['Parallelism']
        assert update_config['Delay'] == uc['Delay']
        assert update_config['FailureAction'] == uc['FailureAction']

    @requires_api_version('1.25')
    def test_create_service_with_update_config_monitor(self):
        container_spec = docker.types.ContainerSpec('busybox', ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        update_config = docker.types.UpdateConfig(
            monitor=300000000, max_failure_ratio=0.4
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, update_config=update_config, name=name
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'UpdateConfig' in svc_info['Spec']
        uc = svc_info['Spec']['UpdateConfig']
        assert update_config['Monitor'] == uc['Monitor']
        assert update_config['MaxFailureRatio'] == uc['MaxFailureRatio']

    def test_create_service_with_restart_policy(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
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

    def test_create_service_with_custom_networks(self):
        net1 = self.client.create_network(
            'dockerpytest_1', driver='overlay', ipam={'Driver': 'default'}
        )
        self.tmp_networks.append(net1['Id'])
        net2 = self.client.create_network(
            'dockerpytest_2', driver='overlay', ipam={'Driver': 'default'}
        )
        self.tmp_networks.append(net2['Id'])
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, networks=[
                'dockerpytest_1', {'Target': 'dockerpytest_2'}
            ]
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Networks' in svc_info['Spec']
        assert svc_info['Spec']['Networks'] == [
            {'Target': net1['Id']}, {'Target': net2['Id']}
        ]

    def test_create_service_with_placement(self):
        node_id = self.client.nodes()[0]['ID']
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(
            container_spec, placement=['node.id=={}'.format(node_id)]
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Placement' in svc_info['Spec']['TaskTemplate']
        assert (svc_info['Spec']['TaskTemplate']['Placement'] ==
                {'Constraints': ['node.id=={}'.format(node_id)]})

    def test_create_service_with_placement_object(self):
        node_id = self.client.nodes()[0]['ID']
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        placemt = docker.types.Placement(
            constraints=['node.id=={}'.format(node_id)]
        )
        task_tmpl = docker.types.TaskTemplate(
            container_spec, placement=placemt
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Placement' in svc_info['Spec']['TaskTemplate']
        assert svc_info['Spec']['TaskTemplate']['Placement'] == placemt

    @requires_api_version('1.30')
    def test_create_service_with_placement_platform(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        placemt = docker.types.Placement(platforms=[('x86_64', 'linux')])
        task_tmpl = docker.types.TaskTemplate(
            container_spec, placement=placemt
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Placement' in svc_info['Spec']['TaskTemplate']
        assert svc_info['Spec']['TaskTemplate']['Placement'] == placemt

    @requires_api_version('1.27')
    def test_create_service_with_placement_preferences(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        placemt = docker.types.Placement(preferences=[
            {'Spread': {'SpreadDescriptor': 'com.dockerpy.test'}}
        ])
        task_tmpl = docker.types.TaskTemplate(
            container_spec, placement=placemt
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Placement' in svc_info['Spec']['TaskTemplate']
        assert svc_info['Spec']['TaskTemplate']['Placement'] == placemt

    def test_create_service_with_endpoint_spec(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        endpoint_spec = docker.types.EndpointSpec(ports={
            12357: (1990, 'udp'),
            12562: (678,),
            53243: 8080,
        })
        svc_id = self.client.create_service(
            task_tmpl, name=name, endpoint_spec=endpoint_spec
        )
        svc_info = self.client.inspect_service(svc_id)
        ports = svc_info['Spec']['EndpointSpec']['Ports']
        for port in ports:
            if port['PublishedPort'] == 12562:
                assert port['TargetPort'] == 678
                assert port['Protocol'] == 'tcp'
            elif port['PublishedPort'] == 53243:
                assert port['TargetPort'] == 8080
                assert port['Protocol'] == 'tcp'
            elif port['PublishedPort'] == 12357:
                assert port['TargetPort'] == 1990
                assert port['Protocol'] == 'udp'
            else:
                self.fail('Invalid port specification: {0}'.format(port))

        assert len(ports) == 3

    @requires_api_version('1.32')
    def test_create_service_with_endpoint_spec_host_publish_mode(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        endpoint_spec = docker.types.EndpointSpec(ports={
            12357: (1990, None, 'host'),
        })
        svc_id = self.client.create_service(
            task_tmpl, name=name, endpoint_spec=endpoint_spec
        )
        svc_info = self.client.inspect_service(svc_id)
        ports = svc_info['Spec']['EndpointSpec']['Ports']
        assert len(ports) == 1
        port = ports[0]
        assert port['PublishedPort'] == 12357
        assert port['TargetPort'] == 1990
        assert port['Protocol'] == 'tcp'
        assert port['PublishMode'] == 'host'

    def test_create_service_with_env(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['true'], env={'DOCKER_PY_TEST': 1}
        )
        task_tmpl = docker.types.TaskTemplate(
            container_spec,
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        con_spec = svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert 'Env' in con_spec
        assert con_spec['Env'] == ['DOCKER_PY_TEST=1']

    @requires_api_version('1.29')
    def test_create_service_with_update_order(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        update_config = docker.types.UpdateConfig(
            parallelism=10, delay=5, order='start-first'
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, update_config=update_config, name=name
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'UpdateConfig' in svc_info['Spec']
        uc = svc_info['Spec']['UpdateConfig']
        assert update_config['Parallelism'] == uc['Parallelism']
        assert update_config['Delay'] == uc['Delay']
        assert update_config['Order'] == uc['Order']

    @requires_api_version('1.25')
    def test_create_service_with_tty(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['true'], tty=True
        )
        task_tmpl = docker.types.TaskTemplate(
            container_spec,
        )
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        con_spec = svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert 'TTY' in con_spec
        assert con_spec['TTY'] is True

    @requires_api_version('1.25')
    def test_create_service_with_tty_dict(self):
        container_spec = {
            'Image': BUSYBOX,
            'Command': ['true'],
            'TTY': True
        }
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        con_spec = svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert 'TTY' in con_spec
        assert con_spec['TTY'] is True

    def test_create_service_global_mode(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, mode='global'
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Mode' in svc_info['Spec']
        assert 'Global' in svc_info['Spec']['Mode']

    def test_create_service_replicated_mode(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name,
            mode=docker.types.ServiceMode('replicated', 5)
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Mode' in svc_info['Spec']
        assert 'Replicated' in svc_info['Spec']['Mode']
        assert svc_info['Spec']['Mode']['Replicated'] == {'Replicas': 5}

    @requires_api_version('1.25')
    def test_update_service_force_update(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ForceUpdate' in svc_info['Spec']['TaskTemplate']
        assert svc_info['Spec']['TaskTemplate']['ForceUpdate'] == 0
        version_index = svc_info['Version']['Index']

        task_tmpl = docker.types.TaskTemplate(container_spec, force_update=10)
        self.client.update_service(name, version_index, task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert svc_info['Spec']['TaskTemplate']['ForceUpdate'] == 10

    @requires_api_version('1.25')
    def test_create_service_with_secret(self):
        secret_name = 'favorite_touhou'
        secret_data = b'phantasmagoria of flower view'
        secret_id = self.client.create_secret(secret_name, secret_data)
        self.tmp_secrets.append(secret_id)
        secret_ref = docker.types.SecretReference(secret_id, secret_name)
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], secrets=[secret_ref]
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Secrets' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        secrets = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Secrets']
        assert secrets[0] == secret_ref

        container = self.get_service_container(name)
        assert container is not None
        exec_id = self.client.exec_create(
            container, 'cat /run/secrets/{0}'.format(secret_name)
        )
        assert self.client.exec_start(exec_id) == secret_data

    @requires_api_version('1.25')
    def test_create_service_with_unicode_secret(self):
        secret_name = 'favorite_touhou'
        secret_data = u'東方花映塚'
        secret_id = self.client.create_secret(secret_name, secret_data)
        self.tmp_secrets.append(secret_id)
        secret_ref = docker.types.SecretReference(secret_id, secret_name)
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], secrets=[secret_ref]
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Secrets' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        secrets = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Secrets']
        assert secrets[0] == secret_ref

        container = self.get_service_container(name)
        assert container is not None
        exec_id = self.client.exec_create(
            container, 'cat /run/secrets/{0}'.format(secret_name)
        )
        container_secret = self.client.exec_start(exec_id)
        container_secret = container_secret.decode('utf-8')
        assert container_secret == secret_data

    @requires_api_version('1.30')
    def test_create_service_with_config(self):
        config_name = 'favorite_touhou'
        config_data = b'phantasmagoria of flower view'
        config_id = self.client.create_config(config_name, config_data)
        self.tmp_configs.append(config_id)
        config_ref = docker.types.ConfigReference(config_id, config_name)
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], configs=[config_ref]
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Configs' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        configs = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Configs']
        assert configs[0] == config_ref

        container = self.get_service_container(name)
        assert container is not None
        exec_id = self.client.exec_create(
            container, 'cat /{0}'.format(config_name)
        )
        assert self.client.exec_start(exec_id) == config_data

    @requires_api_version('1.30')
    def test_create_service_with_unicode_config(self):
        config_name = 'favorite_touhou'
        config_data = u'東方花映塚'
        config_id = self.client.create_config(config_name, config_data)
        self.tmp_configs.append(config_id)
        config_ref = docker.types.ConfigReference(config_id, config_name)
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], configs=[config_ref]
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Configs' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        configs = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Configs']
        assert configs[0] == config_ref

        container = self.get_service_container(name)
        assert container is not None
        exec_id = self.client.exec_create(
            container, 'cat /{0}'.format(config_name)
        )
        container_config = self.client.exec_start(exec_id)
        container_config = container_config.decode('utf-8')
        assert container_config == config_data

    @requires_api_version('1.25')
    def test_create_service_with_hosts(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], hosts={
                'foobar': '127.0.0.1',
                'baz': '8.8.8.8',
            }
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Hosts' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        hosts = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Hosts']
        assert len(hosts) == 2
        assert '127.0.0.1 foobar' in hosts
        assert '8.8.8.8 baz' in hosts

    @requires_api_version('1.25')
    def test_create_service_with_hostname(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], hostname='foobar.baz.com'
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Hostname' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert (
            svc_info['Spec']['TaskTemplate']['ContainerSpec']['Hostname'] ==
            'foobar.baz.com'
        )

    @requires_api_version('1.25')
    def test_create_service_with_groups(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['sleep', '999'], groups=['shrinemaidens', 'youkais']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Groups' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        groups = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Groups']
        assert len(groups) == 2
        assert 'shrinemaidens' in groups
        assert 'youkais' in groups

    @requires_api_version('1.25')
    def test_create_service_with_dns_config(self):
        dns_config = docker.types.DNSConfig(
            nameservers=['8.8.8.8', '8.8.4.4'],
            search=['local'], options=['debug']
        )
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], dns_config=dns_config
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'DNSConfig' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert (
            dns_config ==
            svc_info['Spec']['TaskTemplate']['ContainerSpec']['DNSConfig']
        )

    @requires_api_version('1.25')
    def test_create_service_with_healthcheck(self):
        second = 1000000000
        hc = docker.types.Healthcheck(
            test='true', retries=3, timeout=1 * second,
            start_period=3 * second, interval=int(second / 2),
        )
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], healthcheck=hc
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert (
            'Healthcheck' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        )
        assert (
            hc ==
            svc_info['Spec']['TaskTemplate']['ContainerSpec']['Healthcheck']
        )

    @requires_api_version('1.28')
    def test_create_service_with_readonly(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], read_only=True
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert (
            'ReadOnly' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        )
        assert svc_info['Spec']['TaskTemplate']['ContainerSpec']['ReadOnly']

    @requires_api_version('1.28')
    def test_create_service_with_stop_signal(self):
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], stop_signal='SIGINT'
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert (
            'StopSignal' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        )
        assert (
            svc_info['Spec']['TaskTemplate']['ContainerSpec']['StopSignal'] ==
            'SIGINT'
        )

    @requires_api_version('1.30')
    def test_create_service_with_privileges(self):
        priv = docker.types.Privileges(selinux_disable=True)
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], privileges=priv
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert (
            'Privileges' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        )
        privileges = (
            svc_info['Spec']['TaskTemplate']['ContainerSpec']['Privileges']
        )
        assert privileges['SELinuxContext']['Disable'] is True

    @requires_api_version('1.25')
    def test_update_service_with_defaults_name(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert 'Name' in svc_info['Spec']
        assert svc_info['Spec']['Name'] == name
        version_index = svc_info['Version']['Index']

        task_tmpl = docker.types.TaskTemplate(container_spec, force_update=10)
        self._update_service(
            svc_id, name, version_index, task_tmpl, fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'Name' in svc_info['Spec']
        assert svc_info['Spec']['Name'] == name

    @requires_api_version('1.25')
    def test_update_service_with_defaults_labels(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, labels={'service.label': 'SampleLabel'}
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Labels' in svc_info['Spec']
        assert 'service.label' in svc_info['Spec']['Labels']
        assert svc_info['Spec']['Labels']['service.label'] == 'SampleLabel'
        version_index = svc_info['Version']['Index']

        task_tmpl = docker.types.TaskTemplate(container_spec, force_update=10)
        self._update_service(
            svc_id, name, version_index, task_tmpl, name=name,
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'Labels' in svc_info['Spec']
        assert 'service.label' in svc_info['Spec']['Labels']
        assert svc_info['Spec']['Labels']['service.label'] == 'SampleLabel'

    def test_update_service_with_defaults_mode(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name,
            mode=docker.types.ServiceMode(mode='replicated', replicas=2)
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Mode' in svc_info['Spec']
        assert 'Replicated' in svc_info['Spec']['Mode']
        assert 'Replicas' in svc_info['Spec']['Mode']['Replicated']
        assert svc_info['Spec']['Mode']['Replicated']['Replicas'] == 2
        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, labels={'force': 'update'},
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'Mode' in svc_info['Spec']
        assert 'Replicated' in svc_info['Spec']['Mode']
        assert 'Replicas' in svc_info['Spec']['Mode']['Replicated']
        assert svc_info['Spec']['Mode']['Replicated']['Replicas'] == 2

    def test_update_service_with_defaults_container_labels(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello'],
            labels={'container.label': 'SampleLabel'}
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, labels={'service.label': 'SampleLabel'}
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        assert 'Labels' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        labels = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Labels']
        assert labels['container.label'] == 'SampleLabel'
        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, labels={'force': 'update'},
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        assert 'Labels' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        labels = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Labels']
        assert labels['container.label'] == 'SampleLabel'

        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        self._update_service(
            svc_id, name, new_index, task_tmpl, fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        newer_index = svc_info['Version']['Index']
        assert newer_index > new_index
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        assert 'Labels' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        labels = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Labels']
        assert labels['container.label'] == 'SampleLabel'

    def test_update_service_with_defaults_update_config(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
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
        uc = svc_info['Spec']['UpdateConfig']
        assert update_config['Parallelism'] == uc['Parallelism']
        assert update_config['Delay'] == uc['Delay']
        assert update_config['FailureAction'] == uc['FailureAction']
        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, labels={'force': 'update'},
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'UpdateConfig' in svc_info['Spec']
        uc = svc_info['Spec']['UpdateConfig']
        assert update_config['Parallelism'] == uc['Parallelism']
        assert update_config['Delay'] == uc['Delay']
        assert update_config['FailureAction'] == uc['FailureAction']

    def test_update_service_with_defaults_networks(self):
        net1 = self.client.create_network(
            'dockerpytest_1', driver='overlay', ipam={'Driver': 'default'}
        )
        self.tmp_networks.append(net1['Id'])
        net2 = self.client.create_network(
            'dockerpytest_2', driver='overlay', ipam={'Driver': 'default'}
        )
        self.tmp_networks.append(net2['Id'])
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, networks=[
                'dockerpytest_1', {'Target': 'dockerpytest_2'}
            ]
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Networks' in svc_info['Spec']
        assert svc_info['Spec']['Networks'] == [
            {'Target': net1['Id']}, {'Target': net2['Id']}
        ]

        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, labels={'force': 'update'},
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'Networks' in svc_info['Spec']['TaskTemplate']
        assert svc_info['Spec']['TaskTemplate']['Networks'] == [
            {'Target': net1['Id']}, {'Target': net2['Id']}
        ]

        self._update_service(
            svc_id, name, new_index, networks=[net1['Id']],
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Networks' in svc_info['Spec']['TaskTemplate']
        assert svc_info['Spec']['TaskTemplate']['Networks'] == [
            {'Target': net1['Id']}
        ]

    def test_update_service_with_defaults_endpoint_spec(self):
        container_spec = docker.types.ContainerSpec(BUSYBOX, ['true'])
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        endpoint_spec = docker.types.EndpointSpec(ports={
            12357: (1990, 'udp'),
            12562: (678,),
            53243: 8080,
        })
        svc_id = self.client.create_service(
            task_tmpl, name=name, endpoint_spec=endpoint_spec
        )
        svc_info = self.client.inspect_service(svc_id)
        print(svc_info)
        ports = svc_info['Spec']['EndpointSpec']['Ports']
        for port in ports:
            if port['PublishedPort'] == 12562:
                assert port['TargetPort'] == 678
                assert port['Protocol'] == 'tcp'
            elif port['PublishedPort'] == 53243:
                assert port['TargetPort'] == 8080
                assert port['Protocol'] == 'tcp'
            elif port['PublishedPort'] == 12357:
                assert port['TargetPort'] == 1990
                assert port['Protocol'] == 'udp'
            else:
                self.fail('Invalid port specification: {0}'.format(port))

        assert len(ports) == 3

        svc_info = self.client.inspect_service(svc_id)
        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, labels={'force': 'update'},
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index

        ports = svc_info['Spec']['EndpointSpec']['Ports']
        for port in ports:
            if port['PublishedPort'] == 12562:
                assert port['TargetPort'] == 678
                assert port['Protocol'] == 'tcp'
            elif port['PublishedPort'] == 53243:
                assert port['TargetPort'] == 8080
                assert port['Protocol'] == 'tcp'
            elif port['PublishedPort'] == 12357:
                assert port['TargetPort'] == 1990
                assert port['Protocol'] == 'udp'
            else:
                self.fail('Invalid port specification: {0}'.format(port))

        assert len(ports) == 3

    @requires_api_version('1.25')
    def test_update_service_remove_healthcheck(self):
        second = 1000000000
        hc = docker.types.Healthcheck(
            test='true', retries=3, timeout=1 * second,
            start_period=3 * second, interval=int(second / 2),
        )
        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], healthcheck=hc
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(task_tmpl, name=name)
        svc_info = self.client.inspect_service(svc_id)
        assert (
            'Healthcheck' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        )
        assert (
            hc ==
            svc_info['Spec']['TaskTemplate']['ContainerSpec']['Healthcheck']
        )

        container_spec = docker.types.ContainerSpec(
            BUSYBOX, ['sleep', '999'], healthcheck={}
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)

        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, task_tmpl, fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        container_spec = svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert (
            'Healthcheck' not in container_spec or
            not container_spec['Healthcheck']
        )

    def test_update_service_remove_labels(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, labels={'service.label': 'SampleLabel'}
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Labels' in svc_info['Spec']
        assert 'service.label' in svc_info['Spec']['Labels']
        assert svc_info['Spec']['Labels']['service.label'] == 'SampleLabel'
        version_index = svc_info['Version']['Index']

        self._update_service(
            svc_id, name, version_index, labels={}, fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert not svc_info['Spec'].get('Labels')

    def test_update_service_remove_container_labels(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello'],
            labels={'container.label': 'SampleLabel'}
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, labels={'service.label': 'SampleLabel'}
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        assert 'Labels' in svc_info['Spec']['TaskTemplate']['ContainerSpec']
        labels = svc_info['Spec']['TaskTemplate']['ContainerSpec']['Labels']
        assert labels['container.label'] == 'SampleLabel'
        version_index = svc_info['Version']['Index']

        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello'],
            labels={}
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        self._update_service(
            svc_id, name, version_index, task_tmpl, fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index
        assert 'TaskTemplate' in svc_info['Spec']
        assert 'ContainerSpec' in svc_info['Spec']['TaskTemplate']
        container_spec = svc_info['Spec']['TaskTemplate']['ContainerSpec']
        assert not container_spec.get('Labels')

    @requires_api_version('1.29')
    def test_update_service_with_network_change(self):
        container_spec = docker.types.ContainerSpec(
            'busybox', ['echo', 'hello']
        )
        task_tmpl = docker.types.TaskTemplate(container_spec)
        net1 = self.client.create_network(
            self.get_service_name(), driver='overlay',
            ipam={'Driver': 'default'}
        )
        self.tmp_networks.append(net1['Id'])
        net2 = self.client.create_network(
            self.get_service_name(), driver='overlay',
            ipam={'Driver': 'default'}
        )
        self.tmp_networks.append(net2['Id'])
        name = self.get_service_name()
        svc_id = self.client.create_service(
            task_tmpl, name=name, networks=[net1['Id']]
        )
        svc_info = self.client.inspect_service(svc_id)
        assert 'Networks' in svc_info['Spec']
        assert len(svc_info['Spec']['Networks']) > 0
        assert svc_info['Spec']['Networks'][0]['Target'] == net1['Id']

        svc_info = self.client.inspect_service(svc_id)
        version_index = svc_info['Version']['Index']

        task_tmpl = docker.types.TaskTemplate(container_spec)
        self._update_service(
            svc_id, name, version_index, task_tmpl, name=name,
            networks=[net2['Id']], fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        task_template = svc_info['Spec']['TaskTemplate']
        assert 'Networks' in task_template
        assert len(task_template['Networks']) > 0
        assert task_template['Networks'][0]['Target'] == net2['Id']

        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']
        assert new_index > version_index

        self._update_service(
            svc_id, name, new_index, name=name, networks=[net1['Id']],
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        task_template = svc_info['Spec']['TaskTemplate']
        assert 'ContainerSpec' in task_template
        new_spec = task_template['ContainerSpec']
        assert 'Image' in new_spec
        assert new_spec['Image'].split(':')[0] == 'busybox'
        assert 'Command' in new_spec
        assert new_spec['Command'] == ['echo', 'hello']
        assert 'Networks' in task_template
        assert len(task_template['Networks']) > 0
        assert task_template['Networks'][0]['Target'] == net1['Id']

        svc_info = self.client.inspect_service(svc_id)
        new_index = svc_info['Version']['Index']

        task_tmpl = docker.types.TaskTemplate(
            container_spec, networks=[net2['Id']]
        )
        self._update_service(
            svc_id, name, new_index, task_tmpl, name=name,
            fetch_current_spec=True
        )
        svc_info = self.client.inspect_service(svc_id)
        task_template = svc_info['Spec']['TaskTemplate']
        assert 'Networks' in task_template
        assert len(task_template['Networks']) > 0
        assert task_template['Networks'][0]['Target'] == net2['Id']

    def _update_service(self, svc_id, *args, **kwargs):
        # service update tests seem to be a bit flaky
        # give them a chance to retry the update with a new version index
        try:
            self.client.update_service(*args, **kwargs)
        except docker.errors.APIError as e:
            if e.explanation.endswith("update out of sequence"):
                svc_info = self.client.inspect_service(svc_id)
                version_index = svc_info['Version']['Index']

                if len(args) > 1:
                    args = (args[0], version_index) + args[2:]
                else:
                    kwargs['version'] = version_index

                self.client.update_service(*args, **kwargs)
            else:
                raise
