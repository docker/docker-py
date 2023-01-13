import os
import tempfile
import threading

import pytest

import docker
from ..helpers import random_name
from ..helpers import requires_api_version
from .base import BaseIntegrationTest
from .base import TEST_API_VERSION


class ContainerCollectionTest(BaseIntegrationTest):

    def test_run(self):
        client = docker.from_env(version=TEST_API_VERSION)
        assert client.containers.run(
            "alpine", "echo hello world", remove=True
        ) == b'hello world\n'

    def test_run_detach(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 300", detach=True)
        self.tmp_containers.append(container.id)
        assert container.attrs['Config']['Image'] == "alpine"
        assert container.attrs['Config']['Cmd'] == ['sleep', '300']

    def test_run_with_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with pytest.raises(docker.errors.ContainerError) as cm:
            client.containers.run("alpine", "cat /test", remove=True)
        assert cm.value.exit_status == 1
        assert "cat /test" in cm.exconly()
        assert "alpine" in cm.exconly()
        assert "No such file or directory" in cm.exconly()

    def test_run_with_image_that_does_not_exist(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with pytest.raises(docker.errors.ImageNotFound):
            client.containers.run("dockerpytest_does_not_exist")

    @pytest.mark.skipif(
        docker.constants.IS_WINDOWS_PLATFORM, reason="host mounts on Windows"
    )
    def test_run_with_volume(self):
        client = docker.from_env(version=TEST_API_VERSION)
        path = tempfile.mkdtemp()

        container = client.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /insidecontainer/test'",
            volumes=["%s:/insidecontainer" % path],
            detach=True
        )
        self.tmp_containers.append(container.id)
        container.wait()

        name = "container_volume_test"
        out = client.containers.run(
            "alpine", "cat /insidecontainer/test",
            volumes=["%s:/insidecontainer" % path],
            name=name
        )
        self.tmp_containers.append(name)
        assert out == b'hello\n'

    def test_run_with_named_volume(self):
        client = docker.from_env(version=TEST_API_VERSION)
        volume = client.volumes.create(name="somevolume")
        self.tmp_volumes.append(volume.id)

        container = client.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /insidecontainer/test'",
            volumes=["somevolume:/insidecontainer"],
            detach=True
        )
        self.tmp_containers.append(container.id)
        container.wait()

        name = "container_volume_test"
        out = client.containers.run(
            "alpine", "cat /insidecontainer/test",
            volumes=["somevolume:/insidecontainer"],
            name=name
        )
        self.tmp_containers.append(name)
        assert out == b'hello\n'

    def test_run_with_network(self):
        net_name = random_name()
        client = docker.from_env(version=TEST_API_VERSION)
        client.networks.create(net_name)
        self.tmp_networks.append(net_name)

        container = client.containers.run(
            'alpine', 'echo hello world', network=net_name,
            detach=True
        )
        self.tmp_containers.append(container.id)

        attrs = container.attrs

        assert 'NetworkSettings' in attrs
        assert 'Networks' in attrs['NetworkSettings']
        assert list(attrs['NetworkSettings']['Networks'].keys()) == [net_name]

    def test_run_with_none_driver(self):
        client = docker.from_env(version=TEST_API_VERSION)

        out = client.containers.run(
            "alpine", "echo hello",
            log_config=dict(type='none')
        )
        assert out is None

    def test_run_with_json_file_driver(self):
        client = docker.from_env(version=TEST_API_VERSION)

        out = client.containers.run(
            "alpine", "echo hello",
            log_config=dict(type='json-file')
        )
        assert out == b'hello\n'

    @requires_api_version('1.25')
    def test_run_with_auto_remove(self):
        client = docker.from_env(version=TEST_API_VERSION)
        out = client.containers.run(
            # sleep(2) to allow any communication with the container
            # before it gets removed by the host.
            'alpine', 'sh -c "echo hello && sleep 2"', auto_remove=True
        )
        assert out == b'hello\n'

    @requires_api_version('1.25')
    def test_run_with_auto_remove_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with pytest.raises(docker.errors.ContainerError) as e:
            client.containers.run(
                # sleep(2) to allow any communication with the container
                # before it gets removed by the host.
                'alpine', 'sh -c ">&2 echo error && sleep 2 && exit 1"',
                auto_remove=True
            )
        assert e.value.exit_status == 1
        assert e.value.stderr is None

    def test_run_with_streamed_logs(self):
        client = docker.from_env(version=TEST_API_VERSION)
        out = client.containers.run(
            'alpine', 'sh -c "echo hello && echo world"', stream=True
        )
        logs = [line for line in out]
        assert logs[0] == b'hello\n'
        assert logs[1] == b'world\n'

    @pytest.mark.timeout(5)
    @pytest.mark.skipif(os.environ.get('DOCKER_HOST', '').startswith('ssh://'),
                        reason='No cancellable streams over SSH')
    def test_run_with_streamed_logs_and_cancel(self):
        client = docker.from_env(version=TEST_API_VERSION)
        out = client.containers.run(
            'alpine', 'sh -c "echo hello && echo world"', stream=True
        )

        threading.Timer(1, out.close).start()

        logs = [line for line in out]

        assert len(logs) == 2
        assert logs[0] == b'hello\n'
        assert logs[1] == b'world\n'

    def test_run_with_proxy_config(self):
        client = docker.from_env(version=TEST_API_VERSION)
        client.api._proxy_configs = docker.utils.proxy.ProxyConfig(
            ftp='sakuya.jp:4967'
        )

        out = client.containers.run('alpine', 'sh -c "env"')

        assert b'FTP_PROXY=sakuya.jp:4967\n' in out
        assert b'ftp_proxy=sakuya.jp:4967\n' in out

    def test_get(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 300", detach=True)
        self.tmp_containers.append(container.id)
        assert client.containers.get(container.id).attrs[
            'Config']['Image'] == "alpine"

    def test_list(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container_id = client.containers.run(
            "alpine", "sleep 300", detach=True).id
        self.tmp_containers.append(container_id)
        containers = [c for c in client.containers.list() if c.id ==
                      container_id]
        assert len(containers) == 1

        container = containers[0]
        assert container.attrs['Config']['Image'] == 'alpine'
        assert container.status == 'running'
        assert container.image == client.images.get('alpine')

        container.kill()
        container.remove()
        assert container_id not in [c.id for c in client.containers.list()]

    def test_list_sparse(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container_id = client.containers.run(
            "alpine", "sleep 300", detach=True).id
        self.tmp_containers.append(container_id)
        containers = [c for c in client.containers.list(sparse=True) if c.id ==
                      container_id]
        assert len(containers) == 1

        container = containers[0]
        assert container.attrs['Image'] == 'alpine'
        assert container.status == 'running'
        assert container.image == client.images.get('alpine')
        with pytest.raises(docker.errors.DockerException):
            container.labels

        container.kill()
        container.remove()
        assert container_id not in [c.id for c in client.containers.list()]


class ContainerTest(BaseIntegrationTest):

    def test_commit(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /test'",
            detach=True
        )
        self.tmp_containers.append(container.id)
        container.wait()
        image = container.commit()
        assert client.containers.run(
            image.id, "cat /test", remove=True
        ) == b"hello\n"

    def test_diff(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "touch /test", detach=True)
        self.tmp_containers.append(container.id)
        container.wait()
        assert container.diff() == [{'Path': '/test', 'Kind': 1}]

    def test_exec_run_success(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /test; sleep 60'", detach=True
        )
        self.tmp_containers.append(container.id)
        exec_output = container.exec_run("cat /test")
        assert exec_output[0] == 0
        assert exec_output[1] == b"hello\n"

    def test_exec_run_failed(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run(
            "alpine", "sh -c 'sleep 60'", detach=True
        )
        self.tmp_containers.append(container.id)
        exec_output = container.exec_run("docker ps")
        assert exec_output[0] == 126

    def test_kill(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 300", detach=True)
        self.tmp_containers.append(container.id)
        while container.status != 'running':
            container.reload()
        assert container.status == 'running'
        container.kill()
        container.reload()
        assert container.status == 'exited'

    def test_logs(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "echo hello world",
                                          detach=True)
        self.tmp_containers.append(container.id)
        container.wait()
        assert container.logs() == b"hello world\n"

    def test_pause(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 300", detach=True)
        self.tmp_containers.append(container.id)
        container.pause()
        container.reload()
        assert container.status == "paused"
        container.unpause()
        container.reload()
        assert container.status == "running"

    def test_remove(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "echo hello", detach=True)
        self.tmp_containers.append(container.id)
        assert container.id in [c.id for c in client.containers.list(all=True)]
        container.wait()
        container.remove()
        containers = client.containers.list(all=True)
        assert container.id not in [c.id for c in containers]

    def test_rename(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "echo hello", name="test1",
                                          detach=True)
        self.tmp_containers.append(container.id)
        assert container.name == "test1"
        container.rename("test2")
        container.reload()
        assert container.name == "test2"

    def test_restart(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 100", detach=True)
        self.tmp_containers.append(container.id)
        first_started_at = container.attrs['State']['StartedAt']
        container.restart()
        container.reload()
        second_started_at = container.attrs['State']['StartedAt']
        assert first_started_at != second_started_at

    def test_start(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.create("alpine", "sleep 50", detach=True)
        self.tmp_containers.append(container.id)
        assert container.status == "created"
        container.start()
        container.reload()
        assert container.status == "running"

    def test_stats(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 100", detach=True)
        self.tmp_containers.append(container.id)
        stats = container.stats(stream=False)
        for key in ['read', 'networks', 'precpu_stats', 'cpu_stats',
                    'memory_stats', 'blkio_stats']:
            assert key in stats

    def test_ports_target_none(self):
        client = docker.from_env(version=TEST_API_VERSION)
        ports = None
        target_ports = {'2222/tcp': ports}
        container = client.containers.run(
            "alpine", "sleep 100", detach=True,
            ports=target_ports
        )
        self.tmp_containers.append(container.id)
        container.reload()  # required to get auto-assigned ports
        actual_ports = container.ports
        assert sorted(target_ports.keys()) == sorted(actual_ports.keys())
        for target_client, target_host in target_ports.items():
            for actual_port in actual_ports[target_client]:
                actual_keys = sorted(actual_port.keys())
                assert sorted(['HostIp', 'HostPort']) == actual_keys
                assert target_host is ports
                assert int(actual_port['HostPort']) > 0
        client.close()

    def test_ports_target_tuple(self):
        client = docker.from_env(version=TEST_API_VERSION)
        ports = ('127.0.0.1', 1111)
        target_ports = {'2222/tcp': ports}
        container = client.containers.run(
            "alpine", "sleep 100", detach=True,
            ports=target_ports
        )
        self.tmp_containers.append(container.id)
        container.reload()  # required to get auto-assigned ports
        actual_ports = container.ports
        assert sorted(target_ports.keys()) == sorted(actual_ports.keys())
        for target_client, target_host in target_ports.items():
            for actual_port in actual_ports[target_client]:
                actual_keys = sorted(actual_port.keys())
                assert sorted(['HostIp', 'HostPort']) == actual_keys
                assert target_host == ports
                assert int(actual_port['HostPort']) > 0
        client.close()

    def test_ports_target_list(self):
        client = docker.from_env(version=TEST_API_VERSION)
        ports = [1234, 4567]
        target_ports = {'2222/tcp': ports}
        container = client.containers.run(
            "alpine", "sleep 100", detach=True,
            ports=target_ports
        )
        self.tmp_containers.append(container.id)
        container.reload()  # required to get auto-assigned ports
        actual_ports = container.ports
        assert sorted(target_ports.keys()) == sorted(actual_ports.keys())
        for target_client, target_host in target_ports.items():
            for actual_port in actual_ports[target_client]:
                actual_keys = sorted(actual_port.keys())
                assert sorted(['HostIp', 'HostPort']) == actual_keys
                assert target_host == ports
                assert int(actual_port['HostPort']) > 0
        client.close()

    def test_stop(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "top", detach=True)
        self.tmp_containers.append(container.id)
        assert container.status in ("running", "created")
        container.stop(timeout=2)
        container.reload()
        assert container.status == "exited"

    def test_top(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 60", detach=True)
        self.tmp_containers.append(container.id)
        top = container.top()
        assert len(top['Processes']) == 1
        assert 'sleep 60' in top['Processes'][0]

    def test_update(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 60", detach=True,
                                          cpu_shares=2)
        self.tmp_containers.append(container.id)
        assert container.attrs['HostConfig']['CpuShares'] == 2
        container.update(cpu_shares=3)
        container.reload()
        assert container.attrs['HostConfig']['CpuShares'] == 3

    def test_wait(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sh -c 'exit 0'",
                                          detach=True)
        self.tmp_containers.append(container.id)
        assert container.wait()['StatusCode'] == 0
        container = client.containers.run("alpine", "sh -c 'exit 1'",
                                          detach=True)
        self.tmp_containers.append(container.id)
        assert container.wait()['StatusCode'] == 1

    def test_create_with_volume_driver(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.create(
            'alpine',
            'sleep 300',
            volume_driver='foo'
        )
        self.tmp_containers.append(container.id)
        assert container.attrs['HostConfig']['VolumeDriver'] == 'foo'
