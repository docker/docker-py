from docker.utils.socket import next_frame_size
from docker.utils.socket import read_exactly

from .base import BaseAPIIntegrationTest, BUSYBOX
from ..helpers import (
    requires_api_version, ctrl_with, assert_cat_socket_detached_with_keys
)


class ExecTest(BaseAPIIntegrationTest):
    def test_execute_command(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, ['echo', 'hello'])
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'hello\n'

    def test_exec_command_string(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'echo hello world')
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'hello world\n'

    def test_exec_command_as_user(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'whoami', user='default')
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'default\n'

    def test_exec_command_as_root(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'whoami')
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'root\n'

    def test_exec_command_streaming(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.tmp_containers.append(id)
        self.client.start(id)

        exec_id = self.client.exec_create(id, ['echo', 'hello\nworld'])
        assert 'Id' in exec_id

        res = b''
        for chunk in self.client.exec_start(exec_id, stream=True):
            res += chunk
        assert res == b'hello\nworld\n'

    def test_exec_start_socket(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        container_id = container['Id']
        self.client.start(container_id)
        self.tmp_containers.append(container_id)

        line = 'yay, interactive exec!'
        # `echo` appends CRLF, `printf` doesn't
        exec_id = self.client.exec_create(
            container_id, ['printf', line], tty=True)
        assert 'Id' in exec_id

        socket = self.client.exec_start(exec_id, socket=True)
        self.addCleanup(socket.close)

        next_size = next_frame_size(socket)
        assert next_size == len(line)
        data = read_exactly(socket, next_size)
        assert data.decode('utf-8') == line

    def test_exec_start_detached(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        container_id = container['Id']
        self.client.start(container_id)
        self.tmp_containers.append(container_id)

        exec_id = self.client.exec_create(
            container_id, ['printf', "asdqwe"])
        assert 'Id' in exec_id

        response = self.client.exec_start(exec_id, detach=True)

        assert response == ""

    def test_exec_inspect(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(id, ['mkdir', '/does/not/exist'])
        assert 'Id' in exec_id
        self.client.exec_start(exec_id)
        exec_info = self.client.exec_inspect(exec_id)
        assert 'ExitCode' in exec_info
        assert exec_info['ExitCode'] != 0

    @requires_api_version('1.25')
    def test_exec_command_with_env(self):
        container = self.client.create_container(BUSYBOX, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'env', environment=["X=Y"])
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert b'X=Y\n' in exec_log

    @requires_api_version('1.35')
    def test_exec_command_with_workdir(self):
        container = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        res = self.client.exec_create(container, 'pwd', workdir='/var/www')
        exec_log = self.client.exec_start(res)
        assert exec_log == b'/var/www\n'

    def test_detach_with_default(self):
        container = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(
            id, 'cat', stdin=True, tty=True, stdout=True
        )
        sock = self.client.exec_start(exec_id, tty=True, socket=True)
        self.addCleanup(sock.close)

        assert_cat_socket_detached_with_keys(
            sock, [ctrl_with('p'), ctrl_with('q')]
        )

    def test_detach_with_config_file(self):
        self.client._general_configs['detachKeys'] = 'ctrl-p'
        container = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(
            id, 'cat', stdin=True, tty=True, stdout=True
        )
        sock = self.client.exec_start(exec_id, tty=True, socket=True)
        self.addCleanup(sock.close)

        assert_cat_socket_detached_with_keys(sock, [ctrl_with('p')])

    def test_detach_with_arg(self):
        self.client._general_configs['detachKeys'] = 'ctrl-p'
        container = self.client.create_container(
            BUSYBOX, 'cat', detach=True, stdin_open=True
        )
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        exec_id = self.client.exec_create(
            id, 'cat',
            stdin=True, tty=True, detach_keys='ctrl-x', stdout=True
        )
        sock = self.client.exec_start(exec_id, tty=True, socket=True)
        self.addCleanup(sock.close)

        assert_cat_socket_detached_with_keys(sock, [ctrl_with('x')])
