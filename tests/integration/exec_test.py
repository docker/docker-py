import pytest

from .. import helpers

BUSYBOX = helpers.BUSYBOX


class ExecTest(helpers.BaseTestCase):
    def test_execute_command(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, ['echo', 'hello'])
        self.assertIn('Id', res)

        exec_log = self.client.exec_start(res)
        self.assertEqual(exec_log, b'hello\n')

    def test_exec_command_string(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'echo hello world')
        self.assertIn('Id', res)

        exec_log = self.client.exec_start(res)
        self.assertEqual(exec_log, b'hello world\n')

    def test_exec_command_as_user(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'whoami', user='default')
        self.assertIn('Id', res)

        exec_log = self.client.exec_start(res)
        self.assertEqual(exec_log, b'default\n')

    def test_exec_command_as_root(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'whoami')
        self.assertIn('Id', res)

        exec_log = self.client.exec_start(res)
        self.assertEqual(exec_log, b'root\n')

    def test_exec_command_streaming(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(id, ['echo', 'hello\nworld'])
        self.assertIn('Id', exec_id)

        res = b''
        for chunk in self.client.exec_start(exec_id, stream=True):
            res += chunk
        self.assertEqual(res, b'hello\nworld\n')

    def test_exec_inspect(self):
        if not helpers.exec_driver_is_native():
            pytest.skip('Exec driver not native')

        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(id, ['mkdir', '/does/not/exist'])
        self.assertIn('Id', exec_id)
        self.client.exec_start(exec_id)
        exec_info = self.client.exec_inspect(exec_id)
        self.assertIn('ExitCode', exec_info)
        self.assertNotEqual(exec_info['ExitCode'], 0)
