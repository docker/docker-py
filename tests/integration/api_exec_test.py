from ..helpers import assert_cat_socket_detached_with_keys
from ..helpers import ctrl_with
from ..helpers import requires_api_version
from .base import BaseAPIIntegrationTest
from .base import TEST_IMG
from docker.utils.proxy import ProxyConfig
from docker.utils.socket import next_frame_header
from docker.utils.socket import read_exactly


class ExecTest(BaseAPIIntegrationTest):
    def test_execute_command_with_proxy_env(self):
        # Set a custom proxy config on the client
        self.client._proxy_configs = ProxyConfig(
            ftp='a', https='b', http='c', no_proxy='d'
        )

        container = self.client.create_container(
            TEST_IMG, 'cat', detach=True, stdin_open=True,
        )
        self.client.start(container)
        self.tmp_containers.append(container)

        cmd = 'sh -c "env | grep -i proxy"'

        # First, just make sure the environment variables from the custom
        # config are set

        res = self.client.exec_create(container, cmd=cmd)
        output = self.client.exec_start(res).decode('utf-8').split('\n')
        expected = [
            'ftp_proxy=a', 'https_proxy=b', 'http_proxy=c', 'no_proxy=d',
            'FTP_PROXY=a', 'HTTPS_PROXY=b', 'HTTP_PROXY=c', 'NO_PROXY=d'
        ]
        for item in expected:
            assert item in output

        # Overwrite some variables with a custom environment
        env = {'https_proxy': 'xxx', 'HTTPS_PROXY': 'XXX'}

        res = self.client.exec_create(container, cmd=cmd, environment=env)
        output = self.client.exec_start(res).decode('utf-8').split('\n')
        expected = [
            'ftp_proxy=a', 'https_proxy=xxx', 'http_proxy=c', 'no_proxy=d',
            'FTP_PROXY=a', 'HTTPS_PROXY=XXX', 'HTTP_PROXY=c', 'NO_PROXY=d'
        ]
        for item in expected:
            assert item in output

    def test_execute_command(self):
        container = self.client.create_container(TEST_IMG, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, ['echo', 'hello'])
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'hello\n'

    def test_exec_command_string(self):
        container = self.client.create_container(TEST_IMG, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'echo hello world')
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'hello world\n'

    def test_exec_command_as_user(self):
        container = self.client.create_container(TEST_IMG, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'whoami', user='postgres')
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'postgres\n'

    def test_exec_command_as_root(self):
        container = self.client.create_container(TEST_IMG, 'cat',
                                                 detach=True, stdin_open=True)
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)

        res = self.client.exec_create(id, 'whoami')
        assert 'Id' in res

        exec_log = self.client.exec_start(res)
        assert exec_log == b'root\n'

    def test_exec_command_streaming(self):
        container = self.client.create_container(TEST_IMG, 'cat',
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
        container = self.client.create_container(TEST_IMG, 'cat',
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

        (stream, next_size) = next_frame_header(socket)
        assert stream == 1  # stdout (0 = stdin, 1 = stdout, 2 = stderr)
        assert next_size == len(line)
        data = read_exactly(socket, next_size)
        assert data.decode('utf-8') == line

    def test_exec_start_detached(self):
        container = self.client.create_container(TEST_IMG, 'cat',
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
        container = self.client.create_container(TEST_IMG, 'cat',
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
        container = self.client.create_container(TEST_IMG, 'cat',
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
            TEST_IMG, 'cat', detach=True, stdin_open=True
        )
        self.tmp_containers.append(container)
        self.client.start(container)

        res = self.client.exec_create(container, 'pwd', workdir='/var/opt')
        exec_log = self.client.exec_start(res)
        assert exec_log == b'/var/opt\n'

    def test_detach_with_default(self):
        container = self.client.create_container(
            TEST_IMG, 'cat', detach=True, stdin_open=True
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
            TEST_IMG, 'cat', detach=True, stdin_open=True
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


class ExecDemuxTest(BaseAPIIntegrationTest):
    cmd = 'sh -c "{}"'.format(' ; '.join([
        # Write something on stdout
        'echo hello out',
        # Busybox's sleep does not handle sub-second times.
        # This loops takes ~0.3 second to execute on my machine.
        'sleep 0.5',
        # Write something on stderr
        'echo hello err >&2'])
    )

    def setUp(self):
        super(ExecDemuxTest, self).setUp()
        self.container = self.client.create_container(
            TEST_IMG, 'cat', detach=True, stdin_open=True
        )
        self.client.start(self.container)
        self.tmp_containers.append(self.container)

    def test_exec_command_no_stream_no_demux(self):
        # tty=False, stream=False, demux=False
        res = self.client.exec_create(self.container, self.cmd)
        exec_log = self.client.exec_start(res)
        assert b'hello out\n' in exec_log
        assert b'hello err\n' in exec_log

    def test_exec_command_stream_no_demux(self):
        # tty=False, stream=True, demux=False
        res = self.client.exec_create(self.container, self.cmd)
        exec_log = list(self.client.exec_start(res, stream=True))
        assert len(exec_log) == 2
        assert b'hello out\n' in exec_log
        assert b'hello err\n' in exec_log

    def test_exec_command_no_stream_demux(self):
        # tty=False, stream=False, demux=True
        res = self.client.exec_create(self.container, self.cmd)
        exec_log = self.client.exec_start(res, demux=True)
        assert exec_log == (b'hello out\n', b'hello err\n')

    def test_exec_command_stream_demux(self):
        # tty=False, stream=True, demux=True
        res = self.client.exec_create(self.container, self.cmd)
        exec_log = list(self.client.exec_start(res, demux=True, stream=True))
        assert len(exec_log) == 2
        assert (b'hello out\n', None) in exec_log
        assert (None, b'hello err\n') in exec_log

    def test_exec_command_tty_no_stream_no_demux(self):
        # tty=True, stream=False, demux=False
        res = self.client.exec_create(self.container, self.cmd, tty=True)
        exec_log = self.client.exec_start(res)
        assert exec_log == b'hello out\r\nhello err\r\n'

    def test_exec_command_tty_stream_no_demux(self):
        # tty=True, stream=True, demux=False
        res = self.client.exec_create(self.container, self.cmd, tty=True)
        exec_log = list(self.client.exec_start(res, stream=True))
        assert b'hello out\r\n' in exec_log
        if len(exec_log) == 2:
            assert b'hello err\r\n' in exec_log
        else:
            assert len(exec_log) == 3
            assert b'hello err' in exec_log
            assert b'\r\n' in exec_log

    def test_exec_command_tty_no_stream_demux(self):
        # tty=True, stream=False, demux=True
        res = self.client.exec_create(self.container, self.cmd, tty=True)
        exec_log = self.client.exec_start(res, demux=True)
        assert exec_log == (b'hello out\r\nhello err\r\n', None)

    def test_exec_command_tty_stream_demux(self):
        # tty=True, stream=True, demux=True
        res = self.client.exec_create(self.container, self.cmd, tty=True)
        exec_log = list(self.client.exec_start(res, demux=True, stream=True))
        assert (b'hello out\r\n', None) in exec_log
        if len(exec_log) == 2:
            assert (b'hello err\r\n', None) in exec_log
        else:
            assert len(exec_log) == 3
            assert (b'hello err', None) in exec_log
            assert (b'\r\n', None) in exec_log
