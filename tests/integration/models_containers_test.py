import docker
import tempfile
from .base import BaseIntegrationTest, TEST_API_VERSION
from ..helpers import random_name


class ContainerCollectionTest(BaseIntegrationTest):

    def test_run(self):
        client = docker.from_env(version=TEST_API_VERSION)
        self.assertEqual(
            client.containers.run("alpine", "echo hello world", remove=True),
            b'hello world\n'
        )

    def test_run_detach(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "sleep 300", detach=True)
        self.tmp_containers.append(container.id)
        assert container.attrs['Config']['Image'] == "alpine"
        assert container.attrs['Config']['Cmd'] == ['sleep', '300']

    def test_run_with_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with self.assertRaises(docker.errors.ContainerError) as cm:
            client.containers.run("alpine", "cat /test", remove=True)
        assert cm.exception.exit_status == 1
        assert "cat /test" in str(cm.exception)
        assert "alpine" in str(cm.exception)
        assert "No such file or directory" in str(cm.exception)

    def test_run_with_image_that_does_not_exist(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with self.assertRaises(docker.errors.ImageNotFound):
            client.containers.run("dockerpytest_does_not_exist")

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

        out = client.containers.run(
            "alpine", "cat /insidecontainer/test",
            volumes=["%s:/insidecontainer" % path]
        )
        self.assertEqual(out, b'hello\n')

    def test_run_with_named_volume(self):
        client = docker.from_env(version=TEST_API_VERSION)
        client.volumes.create(name="somevolume")

        container = client.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /insidecontainer/test'",
            volumes=["somevolume:/insidecontainer"],
            detach=True
        )
        self.tmp_containers.append(container.id)
        container.wait()

        out = client.containers.run(
            "alpine", "cat /insidecontainer/test",
            volumes=["somevolume:/insidecontainer"]
        )
        self.assertEqual(out, b'hello\n')

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
        self.assertEqual(out, None)

    def test_run_with_json_file_driver(self):
        client = docker.from_env(version=TEST_API_VERSION)

        out = client.containers.run(
            "alpine", "echo hello",
            log_config=dict(type='json-file')
        )
        self.assertEqual(out, b'hello\n')

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
        self.assertEqual(
            client.containers.run(image.id, "cat /test", remove=True),
            b"hello\n"
        )

    def test_diff(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run("alpine", "touch /test", detach=True)
        self.tmp_containers.append(container.id)
        container.wait()
        assert container.diff() == [{'Path': '/test', 'Kind': 1}]

    def test_exec_run(self):
        client = docker.from_env(version=TEST_API_VERSION)
        container = client.containers.run(
            "alpine", "sh -c 'echo \"hello\" > /test; sleep 60'", detach=True
        )
        self.tmp_containers.append(container.id)
        assert container.exec_run("cat /test") == b"hello\n"

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
        assert container.wait() == 0
        container = client.containers.run("alpine", "sh -c 'exit 1'",
                                          detach=True)
        self.tmp_containers.append(container.id)
        assert container.wait() == 1
