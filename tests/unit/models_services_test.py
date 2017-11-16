import unittest
from docker.models.services import _get_create_service_kwargs, Service


class CreateServiceKwargsTest(unittest.TestCase):
    def test_get_create_service_kwargs(self):
        kwargs = _get_create_service_kwargs('test', {
            'image': 'foo',
            'command': 'true',
            'name': 'somename',
            'labels': {'key': 'value'},
            'hostname': 'test_host',
            'mode': 'global',
            'update_config': {'update': 'config'},
            'networks': ['somenet'],
            'endpoint_spec': {'blah': 'blah'},
            'container_labels': {'containerkey': 'containervalue'},
            'resources': {'foo': 'bar'},
            'restart_policy': {'restart': 'policy'},
            'log_driver': 'logdriver',
            'log_driver_options': {'foo': 'bar'},
            'args': ['some', 'args'],
            'env': {'FOO': 'bar'},
            'workdir': '/',
            'user': 'bob',
            'mounts': [{'some': 'mounts'}],
            'stop_grace_period': 5,
            'constraints': ['foo=bar'],
        })

        task_template = kwargs.pop('task_template')

        assert kwargs == {
            'name': 'somename',
            'labels': {'key': 'value'},
            'mode': 'global',
            'update_config': {'update': 'config'},
            'networks': ['somenet'],
            'endpoint_spec': {'blah': 'blah'},
        }
        assert set(task_template.keys()) == set([
            'ContainerSpec', 'Resources', 'RestartPolicy', 'Placement',
            'LogDriver'
        ])
        assert task_template['Placement'] == {'Constraints': ['foo=bar']}
        assert task_template['LogDriver'] == {
            'Name': 'logdriver',
            'Options': {'foo': 'bar'}
        }
        assert set(task_template['ContainerSpec'].keys()) == set([
            'Image', 'Command', 'Args', 'Hostname', 'Env', 'Dir', 'User',
            'Labels', 'Mounts', 'StopGracePeriod'
        ])


class ServiceModelTest(unittest.TestCase):
    def test_properties(self):
        service = Service(attrs={
            "ID": "testServiceId",
            "Version": {
                "Index": 1234
            },
            "Spec": {
                "Name": "test-service",
                "Labels": {
                    "service.label": "SampleLabel"
                },
                "TaskTemplate": {
                    "ContainerSpec": {
                        "Image": "alpine:3.5",
                        "Args": [
                            "sleep",
                            "60"
                        ],
                        "TTY": True,
                        "StopGracePeriod": 10000000000,
                        "DNSConfig": {
                            "Nameservers": [
                                "8.8.8.8"
                            ]
                        }
                    },
                    "Resources": {
                        "Limits": {
                            "NanoCPUs": 500000000,
                            "MemoryBytes": 20971520
                        },
                        "Reservations": {
                            "MemoryBytes": 5242880
                        }
                    },
                    "RestartPolicy": {
                        "Condition": "on-failure",
                        "Delay": 5000000000,
                        "MaxAttempts": 0
                    },
                    "Placement": {
                        "Constraints": [
                            "node.role==manager"
                        ],
                        "Preferences": [
                            {
                                "Spread": {
                                    "SpreadDescriptor": "node.labels.server"
                                }
                            }
                        ],
                        "Platforms": [
                            {
                                "Architecture": "amd64",
                                "OS": "linux"
                            },
                            {
                                "OS": "linux"
                            }
                        ]
                    },
                    "Networks": [
                        {
                            "Target": "5xww5vi8gwsowwqbfl8riqmw9"
                        },
                        {
                            "Target": "k44g73q5zpci3ikdpzjbs4g76"
                        }
                    ],
                    "LogDriver": {
                        "Name": "json"
                    },
                    "ForceUpdate": 42,
                    "Runtime": "container"
                },
                "Mode": {
                    "Replicated": {
                        "Replicas": 3
                    }
                },
                "UpdateConfig": {
                    "Parallelism": 1,
                    "FailureAction": "pause",
                    "Monitor": 5000000000,
                    "MaxFailureRatio": 0,
                    "Order": "stop-first"
                },
                "RollbackConfig": {
                    "Parallelism": 2,
                    "FailureAction": "continue",
                    "Monitor": 1000000000,
                    "MaxFailureRatio": 0.3,
                    "Order": "start-first"
                },
                "EndpointSpec": {
                    "Mode": "vip",
                    "Ports": [
                        {
                            "Protocol": "tcp",
                            "TargetPort": 8080,
                            "PublishedPort": 80,
                            "PublishMode": "ingress"
                        },
                        {
                            "Protocol": "udp",
                            "TargetPort": 456,
                            "PublishedPort": 123,
                            "PublishMode": "ingress"
                        }
                    ]
                }
            },
            "Endpoint": {
                "Spec": {}
            }
        })

        assert service.id == 'testServiceId'
        assert service.name == 'test-service'
        assert service.version == 1234
        assert service.labels == {"service.label": "SampleLabel"}

        assert service.task_template.force_update == 42

        container_spec = service.task_template.container_spec
        assert container_spec.image == 'alpine:3.5'
        assert container_spec.args == ['sleep', '60']
        assert container_spec.tty is True
        assert container_spec.stop_grace_period == 10000000000
        assert container_spec.dns_config.nameservers == ['8.8.8.8']

        resources = service.task_template.resources
        assert resources.cpu_limit == 500000000
        assert resources.mem_limit == 20971520
        assert resources.cpu_reservation is None
        assert resources.mem_reservation == 5242880

        restart_policy = service.task_template.restart_policy
        assert restart_policy.condition == 'on-failure'
        assert restart_policy.delay == 5000000000
        assert restart_policy.max_attempts == 0

        placement = service.task_template.placement
        assert placement.constraints == ['node.role==manager']
        assert placement.preferences == [{
            'Spread': {'SpreadDescriptor': 'node.labels.server'}
        }]
        assert placement.platforms == [('amd64', 'linux'), (None, 'linux')]

        assert service.task_template.log_driver == {'Name': 'json'}
        assert service.task_template.networks == [
            '5xww5vi8gwsowwqbfl8riqmw9', 'k44g73q5zpci3ikdpzjbs4g76'
        ]

        assert service.mode.mode == 'replicated'
        assert service.mode.replicas == 3

        update_config = service.update_config
        assert update_config.parallelism == 1
        assert update_config.failure_action == 'pause'
        assert update_config.monitor == 5000000000
        assert update_config.max_failure_ratio == 0
        assert update_config.order == 'stop-first'

        rollback_config = service.rollback_config
        assert rollback_config.parallelism == 2
        assert rollback_config.failure_action == 'continue'
        assert rollback_config.monitor == 1000000000
        assert rollback_config.max_failure_ratio == 0.3
        assert rollback_config.order == 'start-first'

        assert service.endpoint_spec.mode == 'vip'
        assert len(service.endpoint_spec.ports) == 2
        assert service.endpoint_spec.ports[0]['Protocol'] == 'tcp'
        assert service.endpoint_spec.ports[0]['TargetPort'] == 8080
        assert service.endpoint_spec.ports[0]['PublishedPort'] == 80
        assert service.endpoint_spec.ports[0]['PublishMode'] == 'ingress'
        assert service.endpoint_spec.ports[1]['Protocol'] == 'udp'
        assert service.endpoint_spec.ports[1]['TargetPort'] == 456
        assert service.endpoint_spec.ports[1]['PublishedPort'] == 123
        assert service.endpoint_spec.ports[1]['PublishMode'] == 'ingress'
