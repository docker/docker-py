import unittest
from docker.models.services import _get_create_service_kwargs


class CreateServiceKwargsTest(unittest.TestCase):
    def test_get_create_service_kwargs(self):
        kwargs = _get_create_service_kwargs('test', {
            'image': 'foo',
            'command': 'true',
            'name': 'somename',
            'labels': {'key': 'value'},
            'hostname': 'test_host',
            'mode': 'global',
            'rollback_config': {'rollback': 'config'},
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
            'preferences': ['bar=baz'],
            'platforms': [('x86_64', 'linux')],
            'maxreplicas': 1,
            'sysctls': {'foo': 'bar'}
        })

        task_template = kwargs.pop('task_template')

        assert kwargs == {
            'name': 'somename',
            'labels': {'key': 'value'},
            'mode': 'global',
            'rollback_config': {'rollback': 'config'},
            'update_config': {'update': 'config'},
            'endpoint_spec': {'blah': 'blah'},
        }
        assert set(task_template.keys()) == {
            'ContainerSpec', 'Resources', 'RestartPolicy', 'Placement',
            'LogDriver', 'Networks'
        }
        assert task_template['Placement'] == {
            'Constraints': ['foo=bar'],
            'Preferences': ['bar=baz'],
            'Platforms': [{'Architecture': 'x86_64', 'OS': 'linux'}],
            'MaxReplicas': 1,
        }
        assert task_template['LogDriver'] == {
            'Name': 'logdriver',
            'Options': {'foo': 'bar'}
        }
        assert task_template['Networks'] == [{'Target': 'somenet'}]
        assert set(task_template['ContainerSpec'].keys()) == {
            'Image', 'Command', 'Args', 'Hostname', 'Env', 'Dir', 'User',
            'Labels', 'Mounts', 'StopGracePeriod', 'Sysctls'
        }
