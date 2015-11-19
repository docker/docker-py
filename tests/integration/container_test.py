import errno
import os
import shutil
import signal
import struct
import tempfile

import docker
import pytest
import six

from ..base import requires_api_version
from .. import helpers

BUSYBOX = helpers.BUSYBOX


class ListContainersTest(helpers.BaseTestCase):
    def test_list_containers(self):
        res0 = self.client.containers(all=True)
        size = len(res0)
        res1 = self.client.create_container(BUSYBOX, 'true')
        self.assertIn('Id', res1)
        self.client.start(res1['Id'])
        self.tmp_containers.append(res1['Id'])
        res2 = self.client.containers(all=True)
        self.assertEqual(size + 1, len(res2))
        retrieved = [x for x in res2 if x['Id'].startswith(res1['Id'])]
        self.assertEqual(len(retrieved), 1)
        retrieved = retrieved[0]
        self.assertIn('Command', retrieved)
        self.assertEqual(retrieved['Command'], six.text_type('true'))
        self.assertIn('Image', retrieved)
        self.assertRegex(retrieved['Image'], r'busybox:.*')
        self.assertIn('Status', retrieved)


class CreateContainerTest(helpers.BaseTestCase):

    def test_create(self):
        res = self.client.create_container(BUSYBOX, 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])

    def test_create_with_host_pid_mode(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true', host_config=self.client.create_host_config(
                pid_mode='host', network_mode='none'
            )
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)
        self.assertIn('HostConfig', inspect)
        host_config = inspect['HostConfig']
        self.assertIn('PidMode', host_config)
        self.assertEqual(host_config['PidMode'], 'host')

    def test_create_with_links(self):
        res0 = self.client.create_container(
            BUSYBOX, 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)

        self.client.start(container1_id)

        res1 = self.client.create_container(
            BUSYBOX, 'cat',
            detach=True, stdin_open=True,
            environment={'FOO': '1'})

        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)

        self.client.start(container2_id)

        # we don't want the first /
        link_path1 = self.client.inspect_container(container1_id)['Name'][1:]
        link_alias1 = 'mylink1'
        link_env_prefix1 = link_alias1.upper()

        link_path2 = self.client.inspect_container(container2_id)['Name'][1:]
        link_alias2 = 'mylink2'
        link_env_prefix2 = link_alias2.upper()

        res2 = self.client.create_container(
            BUSYBOX, 'env', host_config=self.client.create_host_config(
                links={link_path1: link_alias1, link_path2: link_alias2},
                network_mode='bridge'
            )
        )
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)
        self.assertEqual(self.client.wait(container3_id), 0)

        logs = self.client.logs(container3_id)
        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn('{0}_NAME='.format(link_env_prefix1), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix1), logs)
        self.assertIn('{0}_NAME='.format(link_env_prefix2), logs)
        self.assertIn('{0}_ENV_FOO=1'.format(link_env_prefix2), logs)

    def test_create_with_restart_policy(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '2'],
            host_config=self.client.create_host_config(
                restart_policy={"Name": "always", "MaximumRetryCount": 0},
                network_mode='none'
            )
        )
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        with self.assertRaises(docker.errors.APIError) as exc:
            self.client.remove_container(id)
        err = exc.exception.response.text
        self.assertIn(
            'You cannot remove a running container', err
        )
        self.client.remove_container(id, force=True)

    def test_create_container_with_volumes_from(self):
        vol_names = ['foobar_vol0', 'foobar_vol1']

        res0 = self.client.create_container(
            BUSYBOX, 'true', name=vol_names[0]
        )
        container1_id = res0['Id']
        self.tmp_containers.append(container1_id)
        self.client.start(container1_id)

        res1 = self.client.create_container(
            BUSYBOX, 'true', name=vol_names[1]
        )
        container2_id = res1['Id']
        self.tmp_containers.append(container2_id)
        self.client.start(container2_id)
        with self.assertRaises(docker.errors.DockerException):
            self.client.create_container(
                BUSYBOX, 'cat', detach=True, stdin_open=True,
                volumes_from=vol_names
            )
        res2 = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True,
            host_config=self.client.create_host_config(
                volumes_from=vol_names, network_mode='none'
            )
        )
        container3_id = res2['Id']
        self.tmp_containers.append(container3_id)
        self.client.start(container3_id)

        info = self.client.inspect_container(res2['Id'])
        self.assertCountEqual(info['HostConfig']['VolumesFrom'], vol_names)

    def create_container_readonly_fs(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        ctnr = self.client.create_container(
            BUSYBOX, ['mkdir', '/shrine'],
            host_config=self.client.create_host_config(
                read_only=True, network_mode='none'
            )
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        res = self.client.wait(ctnr)
        self.assertNotEqual(res, 0)

    def create_container_with_name(self):
        res = self.client.create_container(BUSYBOX, 'true', name='foobar')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Name', inspect)
        self.assertEqual('/foobar', inspect['Name'])

    def create_container_privileged(self):
        res = self.client.create_container(
            BUSYBOX, 'true', host_config=self.client.create_host_config(
                privileged=True, network_mode='none'
            )
        )
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)
        # Since Nov 2013, the Privileged flag is no longer part of the
        # container's config exposed via the API (safety concerns?).
        #
        if 'Privileged' in inspect['Config']:
            self.assertEqual(inspect['Config']['Privileged'], True)

    def test_create_with_mac_address(self):
        mac_address_expected = "02:42:ac:11:00:0a"
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'], mac_address=mac_address_expected)

        id = container['Id']

        self.client.start(container)
        res = self.client.inspect_container(container['Id'])
        self.assertEqual(mac_address_expected,
                         res['NetworkSettings']['MacAddress'])

        self.client.kill(id)

    @requires_api_version('1.20')
    def test_group_id_ints(self):
        container = self.client.create_container(
            BUSYBOX, 'id -G',
            host_config=self.client.create_host_config(group_add=[1000, 1001])
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.wait(container)

        logs = self.client.logs(container)
        if six.PY3:
            logs = logs.decode('utf-8')
        groups = logs.strip().split(' ')
        self.assertIn('1000', groups)
        self.assertIn('1001', groups)

    @requires_api_version('1.20')
    def test_group_id_strings(self):
        container = self.client.create_container(
            BUSYBOX, 'id -G', host_config=self.client.create_host_config(
                group_add=['1000', '1001']
            )
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.wait(container)

        logs = self.client.logs(container)
        if six.PY3:
            logs = logs.decode('utf-8')

        groups = logs.strip().split(' ')
        self.assertIn('1000', groups)
        self.assertIn('1001', groups)

    def test_valid_log_driver_and_log_opt(self):
        log_config = docker.utils.LogConfig(
            type='json-file',
            config={'max-file': '100'}
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )
        self.tmp_containers.append(container['Id'])
        self.client.start(container)

        info = self.client.inspect_container(container)
        container_log_config = info['HostConfig']['LogConfig']

        self.assertEqual(container_log_config['Type'], log_config.type)
        self.assertEqual(container_log_config['Config'], log_config.config)

    def test_invalid_log_driver_raises_exception(self):
        log_config = docker.utils.LogConfig(
            type='asdf-nope',
            config={}
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )

        expected_msg = "logger: no log driver named 'asdf-nope' is registered"

        with pytest.raises(docker.errors.APIError) as excinfo:
            # raises an internal server error 500
            self.client.start(container)

        assert expected_msg in str(excinfo.value)

    def test_valid_no_log_driver_specified(self):
        log_config = docker.utils.LogConfig(
            type="",
            config={'max-file': '100'}
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )
        self.tmp_containers.append(container['Id'])
        self.client.start(container)

        info = self.client.inspect_container(container)
        container_log_config = info['HostConfig']['LogConfig']

        self.assertEqual(container_log_config['Type'], "json-file")
        self.assertEqual(container_log_config['Config'], log_config.config)

    def test_valid_no_config_specified(self):
        log_config = docker.utils.LogConfig(
            type="json-file",
            config=None
        )

        container = self.client.create_container(
            BUSYBOX, ['true'],
            host_config=self.client.create_host_config(log_config=log_config)
        )
        self.tmp_containers.append(container['Id'])
        self.client.start(container)

        info = self.client.inspect_container(container)
        container_log_config = info['HostConfig']['LogConfig']

        self.assertEqual(container_log_config['Type'], "json-file")
        self.assertEqual(container_log_config['Config'], {})

    def test_create_with_memory_constraints_with_str(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true',
            host_config=self.client.create_host_config(
                memswap_limit='1G',
                mem_limit='700M'
            )
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)

        self.assertIn('HostConfig', inspect)
        host_config = inspect['HostConfig']
        for limit in ['Memory', 'MemorySwap']:
            self.assertIn(limit, host_config)

    def test_create_with_memory_constraints_with_int(self):
        ctnr = self.client.create_container(
            BUSYBOX, 'true',
            host_config=self.client.create_host_config(mem_swappiness=40)
        )
        self.assertIn('Id', ctnr)
        self.tmp_containers.append(ctnr['Id'])
        self.client.start(ctnr)
        inspect = self.client.inspect_container(ctnr)

        self.assertIn('HostConfig', inspect)
        host_config = inspect['HostConfig']
        self.assertIn('MemorySwappiness', host_config)


class VolumeBindTest(helpers.BaseTestCase):
    def setUp(self):
        super(VolumeBindTest, self).setUp()

        self.mount_dest = '/mnt'

        # Get a random pathname - we don't need it to exist locally
        self.mount_origin = tempfile.mkdtemp()
        shutil.rmtree(self.mount_origin)
        self.filename = 'shared.txt'

        self.run_with_volume(
            False,
            BUSYBOX,
            ['touch', os.path.join(self.mount_dest, self.filename)],
        )

    def test_create_with_binds_rw(self):

        container = self.run_with_volume(
            False,
            BUSYBOX,
            ['ls', self.mount_dest],
        )
        logs = self.client.logs(container)

        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn(self.filename, logs)
        inspect_data = self.client.inspect_container(container)
        self.check_container_data(inspect_data, True)

    def test_create_with_binds_ro(self):
        self.run_with_volume(
            False,
            BUSYBOX,
            ['touch', os.path.join(self.mount_dest, self.filename)],
        )
        container = self.run_with_volume(
            True,
            BUSYBOX,
            ['ls', self.mount_dest],
        )
        logs = self.client.logs(container)

        if six.PY3:
            logs = logs.decode('utf-8')
        self.assertIn(self.filename, logs)

        inspect_data = self.client.inspect_container(container)
        self.check_container_data(inspect_data, False)

    def check_container_data(self, inspect_data, rw):
        if docker.utils.compare_version('1.20', self.client._version) < 0:
            self.assertIn('Volumes', inspect_data)
            self.assertIn(self.mount_dest, inspect_data['Volumes'])
            self.assertEqual(
                self.mount_origin, inspect_data['Volumes'][self.mount_dest]
            )
            self.assertIn(self.mount_dest, inspect_data['VolumesRW'])
            self.assertFalse(inspect_data['VolumesRW'][self.mount_dest])
        else:
            self.assertIn('Mounts', inspect_data)
            filtered = list(filter(
                lambda x: x['Destination'] == self.mount_dest,
                inspect_data['Mounts']
            ))
            self.assertEqual(len(filtered), 1)
            mount_data = filtered[0]
            self.assertEqual(mount_data['Source'], self.mount_origin)
            self.assertEqual(mount_data['RW'], rw)

    def run_with_volume(self, ro, *args, **kwargs):
        return self.run_container(
            *args,
            volumes={self.mount_dest: {}},
            host_config=self.client.create_host_config(
                binds={
                    self.mount_origin: {
                        'bind': self.mount_dest,
                        'ro': ro,
                    },
                },
                network_mode='none'
            ),
            **kwargs
        )


@requires_api_version('1.20')
class ArchiveTest(helpers.BaseTestCase):
    def test_get_file_archive_from_container(self):
        data = 'The Maid and the Pocket Watch of Blood'
        ctnr = self.client.create_container(
            BUSYBOX, 'sh -c "echo {0} > /vol1/data.txt"'.format(data),
            volumes=['/vol1']
        )
        self.tmp_containers.append(ctnr)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        with tempfile.NamedTemporaryFile() as destination:
            strm, stat = self.client.get_archive(ctnr, '/vol1/data.txt')
            for d in strm:
                destination.write(d)
            destination.seek(0)
            retrieved_data = helpers.untar_file(destination, 'data.txt')
            if six.PY3:
                retrieved_data = retrieved_data.decode('utf-8')
            self.assertEqual(data, retrieved_data.strip())

    def test_get_file_stat_from_container(self):
        data = 'The Maid and the Pocket Watch of Blood'
        ctnr = self.client.create_container(
            BUSYBOX, 'sh -c "echo -n {0} > /vol1/data.txt"'.format(data),
            volumes=['/vol1']
        )
        self.tmp_containers.append(ctnr)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        strm, stat = self.client.get_archive(ctnr, '/vol1/data.txt')
        self.assertIn('name', stat)
        self.assertEqual(stat['name'], 'data.txt')
        self.assertIn('size', stat)
        self.assertEqual(stat['size'], len(data))

    def test_copy_file_to_container(self):
        data = b'Deaf To All But The Song'
        with tempfile.NamedTemporaryFile() as test_file:
            test_file.write(data)
            test_file.seek(0)
            ctnr = self.client.create_container(
                BUSYBOX,
                'cat {0}'.format(
                    os.path.join('/vol1', os.path.basename(test_file.name))
                ),
                volumes=['/vol1']
            )
            self.tmp_containers.append(ctnr)
            with helpers.simple_tar(test_file.name) as test_tar:
                self.client.put_archive(ctnr, '/vol1', test_tar)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        logs = self.client.logs(ctnr)
        if six.PY3:
            logs = logs.decode('utf-8')
            data = data.decode('utf-8')
        self.assertEqual(logs.strip(), data)

    def test_copy_directory_to_container(self):
        files = ['a.py', 'b.py', 'foo/b.py']
        dirs = ['foo', 'bar']
        base = helpers.make_tree(dirs, files)
        ctnr = self.client.create_container(
            BUSYBOX, 'ls -p /vol1', volumes=['/vol1']
        )
        self.tmp_containers.append(ctnr)
        with docker.utils.tar(base) as test_tar:
            self.client.put_archive(ctnr, '/vol1', test_tar)
        self.client.start(ctnr)
        self.client.wait(ctnr)
        logs = self.client.logs(ctnr)
        if six.PY3:
            logs = logs.decode('utf-8')
        results = logs.strip().split()
        self.assertIn('a.py', results)
        self.assertIn('b.py', results)
        self.assertIn('foo/', results)
        self.assertIn('bar/', results)


class RenameContainerTest(helpers.BaseTestCase):
    def test_rename_container(self):
        version = self.client.version()['Version']
        name = 'hong_meiling'
        res = self.client.create_container(BUSYBOX, 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.rename(res, name)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Name', inspect)
        if version == '1.5.0':
            self.assertEqual(name, inspect['Name'])
        else:
            self.assertEqual('/{0}'.format(name), inspect['Name'])


class StartContainerTest(helpers.BaseTestCase):
    def test_start_container(self):
        res = self.client.create_container(BUSYBOX, 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res['Id'])
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)

    def test_start_container_with_dict_instead_of_id(self):
        res = self.client.create_container(BUSYBOX, 'true')
        self.assertIn('Id', res)
        self.tmp_containers.append(res['Id'])
        self.client.start(res)
        inspect = self.client.inspect_container(res['Id'])
        self.assertIn('Config', inspect)
        self.assertIn('Id', inspect)
        self.assertTrue(inspect['Id'].startswith(res['Id']))
        self.assertIn('Image', inspect)
        self.assertIn('State', inspect)
        self.assertIn('Running', inspect['State'])
        if not inspect['State']['Running']:
            self.assertIn('ExitCode', inspect['State'])
            self.assertEqual(inspect['State']['ExitCode'], 0)

    def test_run_shlex_commands(self):
        commands = [
            'true',
            'echo "The Young Descendant of Tepes & Septette for the '
            'Dead Princess"',
            'echo -n "The Young Descendant of Tepes & Septette for the '
            'Dead Princess"',
            '/bin/sh -c "echo Hello World"',
            '/bin/sh -c \'echo "Hello World"\'',
            'echo "\"Night of Nights\""',
            'true && echo "Night of Nights"'
        ]
        for cmd in commands:
            container = self.client.create_container(BUSYBOX, cmd)
            id = container['Id']
            self.client.start(id)
            self.tmp_containers.append(id)
            exitcode = self.client.wait(id)
            self.assertEqual(exitcode, 0, msg=cmd)


class WaitTest(helpers.BaseTestCase):
    def test_wait(self):
        res = self.client.create_container(BUSYBOX, ['sleep', '3'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        inspect = self.client.inspect_container(id)
        self.assertIn('Running', inspect['State'])
        self.assertEqual(inspect['State']['Running'], False)
        self.assertIn('ExitCode', inspect['State'])
        self.assertEqual(inspect['State']['ExitCode'], exitcode)

    def test_wait_with_dict_instead_of_id(self):
        res = self.client.create_container(BUSYBOX, ['sleep', '3'])
        id = res['Id']
        self.tmp_containers.append(id)
        self.client.start(res)
        exitcode = self.client.wait(res)
        self.assertEqual(exitcode, 0)
        inspect = self.client.inspect_container(res)
        self.assertIn('Running', inspect['State'])
        self.assertEqual(inspect['State']['Running'], False)
        self.assertIn('ExitCode', inspect['State'])
        self.assertEqual(inspect['State']['ExitCode'], exitcode)


class LogsTest(helpers.BaseTestCase):
    def test_logs(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id)
        self.assertEqual(logs, (snippet + '\n').encode(encoding='ascii'))

    def test_logs_tail_option(self):
        snippet = '''Line1
Line2'''
        container = self.client.create_container(
            BUSYBOX, 'echo "{0}"'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id, tail=1)
        self.assertEqual(logs, 'Line2\n'.encode(encoding='ascii'))

    def test_logs_streaming(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        logs = six.binary_type()
        for chunk in self.client.logs(id, stream=True):
            logs += chunk

        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)

        self.assertEqual(logs, (snippet + '\n').encode(encoding='ascii'))

    def test_logs_with_dict_instead_of_id(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo {0}'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(container)
        self.assertEqual(logs, (snippet + '\n').encode(encoding='ascii'))

    def test_logs_with_tail_0(self):
        snippet = 'Flowering Nights (Sakuya Iyazoi)'
        container = self.client.create_container(
            BUSYBOX, 'echo "{0}"'.format(snippet)
        )
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        logs = self.client.logs(id, tail=0)
        self.assertEqual(logs, ''.encode(encoding='ascii'))


class DiffTest(helpers.BaseTestCase):
    def test_diff(self):
        container = self.client.create_container(BUSYBOX, ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        diff = self.client.diff(id)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        self.assertEqual(len(test_diff), 1)
        self.assertIn('Kind', test_diff[0])
        self.assertEqual(test_diff[0]['Kind'], 1)

    def test_diff_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        exitcode = self.client.wait(id)
        self.assertEqual(exitcode, 0)
        diff = self.client.diff(container)
        test_diff = [x for x in diff if x.get('Path', None) == '/test']
        self.assertEqual(len(test_diff), 1)
        self.assertIn('Kind', test_diff[0])
        self.assertEqual(test_diff[0]['Kind'], 1)


class StopTest(helpers.BaseTestCase):
    def test_stop(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.stop(id, timeout=2)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if helpers.exec_driver_is_native():
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)

    def test_stop_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        self.assertIn('Id', container)
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        self.client.stop(container, timeout=2)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if helpers.exec_driver_is_native():
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)


class KillTest(helpers.BaseTestCase):
    def test_kill(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if helpers.exec_driver_is_native():
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)

    def test_kill_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(container)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        if helpers.exec_driver_is_native():
            self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False)

    def test_kill_with_signal(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '60'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        self.client.kill(id, signal=signal.SIGKILL)
        exitcode = self.client.wait(id)
        self.assertNotEqual(exitcode, 0)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertNotEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], False, state)


class PortTest(helpers.BaseTestCase):
    def test_port(self):

        port_bindings = {
            '1111': ('127.0.0.1', '4567'),
            '2222': ('127.0.0.1', '4568')
        }

        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'], ports=list(port_bindings.keys()),
            host_config=self.client.create_host_config(
                port_bindings=port_bindings, network_mode='bridge'
            )
        )
        id = container['Id']

        self.client.start(container)

        # Call the port function on each biding and compare expected vs actual
        for port in port_bindings:
            actual_bindings = self.client.port(container, port)
            port_binding = actual_bindings.pop()

            ip, host_port = port_binding['HostIp'], port_binding['HostPort']

            self.assertEqual(ip, port_bindings[port][0])
            self.assertEqual(host_port, port_bindings[port][1])

        self.client.kill(id)


class ContainerTopTest(helpers.BaseTestCase):
    def test_top(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'])

        id = container['Id']

        self.client.start(container)
        res = self.client.top(container['Id'])
        self.assertEqual(
            res['Titles'],
            ['UID', 'PID', 'PPID', 'C', 'STIME', 'TTY', 'TIME', 'CMD']
        )
        self.assertEqual(len(res['Processes']), 1)
        self.assertEqual(res['Processes'][0][7], 'sleep 60')
        self.client.kill(id)

    def test_top_with_psargs(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'])

        id = container['Id']

        self.client.start(container)
        res = self.client.top(container['Id'], 'waux')
        self.assertEqual(
            res['Titles'],
            ['USER', 'PID', '%CPU', '%MEM', 'VSZ', 'RSS',
                'TTY', 'STAT', 'START', 'TIME', 'COMMAND'],
        )
        self.assertEqual(len(res['Processes']), 1)
        self.assertEqual(res['Processes'][0][10], 'sleep 60')
        self.client.kill(id)


class RestartContainerTest(helpers.BaseTestCase):
    def test_restart(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        self.assertIn('State', info)
        self.assertIn('StartedAt', info['State'])
        start_time1 = info['State']['StartedAt']
        self.client.restart(id, timeout=2)
        info2 = self.client.inspect_container(id)
        self.assertIn('State', info2)
        self.assertIn('StartedAt', info2['State'])
        start_time2 = info2['State']['StartedAt']
        self.assertNotEqual(start_time1, start_time2)
        self.assertIn('Running', info2['State'])
        self.assertEqual(info2['State']['Running'], True)
        self.client.kill(id)

    def test_restart_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        self.assertIn('Id', container)
        id = container['Id']
        self.client.start(container)
        self.tmp_containers.append(id)
        info = self.client.inspect_container(id)
        self.assertIn('State', info)
        self.assertIn('StartedAt', info['State'])
        start_time1 = info['State']['StartedAt']
        self.client.restart(container, timeout=2)
        info2 = self.client.inspect_container(id)
        self.assertIn('State', info2)
        self.assertIn('StartedAt', info2['State'])
        start_time2 = info2['State']['StartedAt']
        self.assertNotEqual(start_time1, start_time2)
        self.assertIn('Running', info2['State'])
        self.assertEqual(info2['State']['Running'], True)
        self.client.kill(id)


class RemoveContainerTest(helpers.BaseTestCase):
    def test_remove(self):
        container = self.client.create_container(BUSYBOX, ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(id)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)

    def test_remove_with_dict_instead_of_id(self):
        container = self.client.create_container(BUSYBOX, ['true'])
        id = container['Id']
        self.client.start(id)
        self.client.wait(id)
        self.client.remove_container(container)
        containers = self.client.containers(all=True)
        res = [x for x in containers if 'Id' in x and x['Id'].startswith(id)]
        self.assertEqual(len(res), 0)


class AttachContainerTest(helpers.BaseTestCase):
    def test_run_container_streaming(self):
        container = self.client.create_container(BUSYBOX, '/bin/sh',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        sock = self.client.attach_socket(container, ws=False)
        self.assertTrue(sock.fileno() > -1)

    def test_run_container_reading_socket(self):
        line = 'hi there and stuff and things, words!'
        command = "echo '{0}'".format(line)
        container = self.client.create_container(BUSYBOX, command,
                                                 detach=True, tty=False)
        ident = container['Id']
        self.tmp_containers.append(ident)

        opts = {"stdout": 1, "stream": 1, "logs": 1}
        pty_stdout = self.client.attach_socket(ident, opts)
        self.client.start(ident)

        recoverable_errors = (errno.EINTR, errno.EDEADLK, errno.EWOULDBLOCK)

        def read(n=4096):
            """Code stolen from dockerpty to read the socket"""
            try:
                if hasattr(pty_stdout, 'recv'):
                    return pty_stdout.recv(n)
                return os.read(pty_stdout.fileno(), n)
            except EnvironmentError as e:
                if e.errno not in recoverable_errors:
                    raise

        def next_packet_size():
            """Code stolen from dockerpty to get the next packet size"""
            data = six.binary_type()
            while len(data) < 8:
                next_data = read(8 - len(data))
                if not next_data:
                    return 0
                data = data + next_data

            if data is None:
                return 0

            if len(data) == 8:
                _, actual = struct.unpack('>BxxxL', data)
                return actual

        next_size = next_packet_size()
        self.assertEqual(next_size, len(line) + 1)

        data = six.binary_type()
        while len(data) < next_size:
            next_data = read(next_size - len(data))
            if not next_data:
                assert False, "Failed trying to read in the dataz"
            data += next_data
        self.assertEqual(data.decode('utf-8'), "{0}\n".format(line))
        pty_stdout.close()

        # Prevent segfault at the end of the test run
        if hasattr(pty_stdout, "_response"):
            del pty_stdout._response


class PauseTest(helpers.BaseTestCase):
    def test_pause_unpause(self):
        container = self.client.create_container(BUSYBOX, ['sleep', '9999'])
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(container)
        self.client.pause(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], True)
        self.assertIn('Paused', state)
        self.assertEqual(state['Paused'], True)

        self.client.unpause(id)
        container_info = self.client.inspect_container(id)
        self.assertIn('State', container_info)
        state = container_info['State']
        self.assertIn('ExitCode', state)
        self.assertEqual(state['ExitCode'], 0)
        self.assertIn('Running', state)
        self.assertEqual(state['Running'], True)
        self.assertIn('Paused', state)
        self.assertEqual(state['Paused'], False)


class GetContainerStatsTest(helpers.BaseTestCase):
    @requires_api_version('1.19')
    def test_get_container_stats_no_stream(self):
        container = self.client.create_container(
            BUSYBOX, ['sleep', '60'],
        )
        self.tmp_containers.append(container)
        self.client.start(container)
        response = self.client.stats(container, stream=0)
        self.client.kill(container)

        self.assertEqual(type(response), dict)
        for key in ['read', 'networks', 'precpu_stats', 'cpu_stats',
                    'memory_stats', 'blkio_stats']:
            self.assertIn(key, response)

        @requires_api_version('1.17')
        def test_get_container_stats_stream(self):
            container = self.client.create_container(
                BUSYBOX, ['sleep', '60'],
            )
            self.tmp_containers.append(container)
            self.client.start(container)
            stream = self.client.stats(container)
            for chunk in stream:
                self.assertEqual(type(chunk), dict)
                for key in ['read', 'network', 'precpu_stats', 'cpu_stats',
                            'memory_stats', 'blkio_stats']:
                    self.assertIn(key, chunk)
