import docker
from docker.constants import DEFAULT_DATA_CHUNK_SIZE
from docker.models.containers import Container, _create_container_args
from docker.models.images import Image
import unittest

from .fake_api import FAKE_CONTAINER_ID, FAKE_IMAGE_ID, FAKE_EXEC_ID
from .fake_api_client import make_fake_client
import pytest


class ContainerCollectionTest(unittest.TestCase):
    def test_run(self):
        client = make_fake_client()
        out = client.containers.run("alpine", "echo hello world")

        assert out == b'hello world\n'

        client.api.create_container.assert_called_with(
            image="alpine",
            command="echo hello world",
            detach=False,
            host_config={'NetworkMode': 'default'}
        )
        client.api.inspect_container.assert_called_with(FAKE_CONTAINER_ID)
        client.api.start.assert_called_with(FAKE_CONTAINER_ID)
        client.api.wait.assert_called_with(FAKE_CONTAINER_ID)
        client.api.logs.assert_called_with(
            FAKE_CONTAINER_ID, stderr=False, stdout=True, stream=True,
            follow=True
        )

    def test_create_container_args(self):
        create_kwargs = _create_container_args(dict(
            image='alpine',
            command='echo hello world',
            blkio_weight_device=[{'Path': 'foo', 'Weight': 3}],
            blkio_weight=2,
            cap_add=['foo'],
            cap_drop=['bar'],
            cgroup_parent='foobar',
            cpu_period=1,
            cpu_quota=2,
            cpu_shares=5,
            cpuset_cpus='0-3',
            detach=False,
            device_read_bps=[{'Path': 'foo', 'Rate': 3}],
            device_read_iops=[{'Path': 'foo', 'Rate': 3}],
            device_write_bps=[{'Path': 'foo', 'Rate': 3}],
            device_write_iops=[{'Path': 'foo', 'Rate': 3}],
            devices=['/dev/sda:/dev/xvda:rwm'],
            dns=['8.8.8.8'],
            domainname='example.com',
            dns_opt=['foo'],
            dns_search=['example.com'],
            entrypoint='/bin/sh',
            environment={'FOO': 'BAR'},
            extra_hosts={'foo': '1.2.3.4'},
            group_add=['blah'],
            ipc_mode='foo',
            kernel_memory=123,
            labels={'key': 'value'},
            links={'foo': 'bar'},
            log_config={'Type': 'json-file', 'Config': {}},
            lxc_conf={'foo': 'bar'},
            healthcheck={'test': 'true'},
            hostname='somehost',
            mac_address='abc123',
            mem_limit=123,
            mem_reservation=123,
            mem_swappiness=2,
            memswap_limit=456,
            name='somename',
            network_disabled=False,
            network='foo',
            oom_kill_disable=True,
            oom_score_adj=5,
            pid_mode='host',
            pids_limit=500,
            ports={
                1111: 4567,
                2222: None
            },
            privileged=True,
            publish_all_ports=True,
            read_only=True,
            restart_policy={'Name': 'always'},
            security_opt=['blah'],
            shm_size=123,
            stdin_open=True,
            stop_signal=9,
            sysctls={'foo': 'bar'},
            tmpfs={'/blah': ''},
            tty=True,
            ulimits=[{"Name": "nofile", "Soft": 1024, "Hard": 2048}],
            user='bob',
            userns_mode='host',
            version='1.23',
            volume_driver='some_driver',
            volumes=[
                '/home/user1/:/mnt/vol2',
                '/var/www:/mnt/vol1:ro',
                'volumename:/mnt/vol3',
                '/volumewithnohostpath',
                '/anothervolumewithnohostpath:ro',
                'C:\\windows\\path:D:\\hello\\world:rw'
            ],
            volumes_from=['container'],
            working_dir='/code'
        ))

        expected = dict(
            image='alpine',
            command='echo hello world',
            domainname='example.com',
            detach=False,
            entrypoint='/bin/sh',
            environment={'FOO': 'BAR'},
            host_config={
                'Binds': [
                    '/home/user1/:/mnt/vol2',
                    '/var/www:/mnt/vol1:ro',
                    'volumename:/mnt/vol3',
                    '/volumewithnohostpath',
                    '/anothervolumewithnohostpath:ro',
                    'C:\\windows\\path:D:\\hello\\world:rw'
                ],
                'BlkioDeviceReadBps': [{'Path': 'foo', 'Rate': 3}],
                'BlkioDeviceReadIOps': [{'Path': 'foo', 'Rate': 3}],
                'BlkioDeviceWriteBps': [{'Path': 'foo', 'Rate': 3}],
                'BlkioDeviceWriteIOps': [{'Path': 'foo', 'Rate': 3}],
                'BlkioWeightDevice': [{'Path': 'foo', 'Weight': 3}],
                'BlkioWeight': 2,
                'CapAdd': ['foo'],
                'CapDrop': ['bar'],
                'CgroupParent': 'foobar',
                'CpuPeriod': 1,
                'CpuQuota': 2,
                'CpuShares': 5,
                'CpusetCpus': '0-3',
                'Devices': [{'PathOnHost': '/dev/sda',
                             'CgroupPermissions': 'rwm',
                             'PathInContainer': '/dev/xvda'}],
                'Dns': ['8.8.8.8'],
                'DnsOptions': ['foo'],
                'DnsSearch': ['example.com'],
                'ExtraHosts': ['foo:1.2.3.4'],
                'GroupAdd': ['blah'],
                'IpcMode': 'foo',
                'KernelMemory': 123,
                'Links': ['foo:bar'],
                'LogConfig': {'Type': 'json-file', 'Config': {}},
                'LxcConf': [{'Key': 'foo', 'Value': 'bar'}],
                'Memory': 123,
                'MemoryReservation': 123,
                'MemorySwap': 456,
                'MemorySwappiness': 2,
                'NetworkMode': 'foo',
                'OomKillDisable': True,
                'OomScoreAdj': 5,
                'PidMode': 'host',
                'PidsLimit': 500,
                'PortBindings': {
                    '1111/tcp': [{'HostIp': '', 'HostPort': '4567'}],
                    '2222/tcp': [{'HostIp': '', 'HostPort': ''}]
                },
                'Privileged': True,
                'PublishAllPorts': True,
                'ReadonlyRootfs': True,
                'RestartPolicy': {'Name': 'always'},
                'SecurityOpt': ['blah'],
                'ShmSize': 123,
                'Sysctls': {'foo': 'bar'},
                'Tmpfs': {'/blah': ''},
                'Ulimits': [{"Name": "nofile", "Soft": 1024, "Hard": 2048}],
                'UsernsMode': 'host',
                'VolumesFrom': ['container'],
            },
            healthcheck={'test': 'true'},
            hostname='somehost',
            labels={'key': 'value'},
            mac_address='abc123',
            name='somename',
            network_disabled=False,
            networking_config={'foo': None},
            ports=[('1111', 'tcp'), ('2222', 'tcp')],
            stdin_open=True,
            stop_signal=9,
            tty=True,
            user='bob',
            volume_driver='some_driver',
            volumes=[
                '/mnt/vol2',
                '/mnt/vol1',
                '/mnt/vol3',
                '/volumewithnohostpath',
                '/anothervolumewithnohostpath',
                'D:\\hello\\world'
            ],
            working_dir='/code'
        )

        assert create_kwargs == expected

    def test_run_detach(self):
        client = make_fake_client()
        container = client.containers.run('alpine', 'sleep 300', detach=True)
        assert isinstance(container, Container)
        assert container.id == FAKE_CONTAINER_ID
        client.api.create_container.assert_called_with(
            image='alpine',
            command='sleep 300',
            detach=True,
            host_config={
                'NetworkMode': 'default',
            }
        )
        client.api.inspect_container.assert_called_with(FAKE_CONTAINER_ID)
        client.api.start.assert_called_with(FAKE_CONTAINER_ID)

    def test_run_pull(self):
        client = make_fake_client()

        # raise exception on first call, then return normal value
        client.api.create_container.side_effect = [
            docker.errors.ImageNotFound(""),
            client.api.create_container.return_value
        ]

        container = client.containers.run('alpine', 'sleep 300', detach=True)

        assert container.id == FAKE_CONTAINER_ID
        client.api.pull.assert_called_with('alpine', platform=None, tag=None)

    def test_run_with_error(self):
        client = make_fake_client()
        client.api.logs.return_value = "some error"
        client.api.wait.return_value = {'StatusCode': 1}

        with pytest.raises(docker.errors.ContainerError) as cm:
            client.containers.run('alpine', 'echo hello world')
        assert cm.value.exit_status == 1
        assert "some error" in cm.exconly()

    def test_run_with_image_object(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        client.containers.run(image)
        client.api.create_container.assert_called_with(
            image=image.id,
            command=None,
            detach=False,
            host_config={
                'NetworkMode': 'default',
            }
        )

    def test_run_remove(self):
        client = make_fake_client()
        client.containers.run("alpine")
        client.api.remove_container.assert_not_called()

        client = make_fake_client()
        client.api.wait.return_value = {'StatusCode': 1}
        with pytest.raises(docker.errors.ContainerError):
            client.containers.run("alpine")
        client.api.remove_container.assert_not_called()

        client = make_fake_client()
        client.containers.run("alpine", remove=True)
        client.api.remove_container.assert_called_with(FAKE_CONTAINER_ID)

        client = make_fake_client()
        client.api.wait.return_value = {'StatusCode': 1}
        with pytest.raises(docker.errors.ContainerError):
            client.containers.run("alpine", remove=True)
        client.api.remove_container.assert_called_with(FAKE_CONTAINER_ID)

        client = make_fake_client()
        client.api._version = '1.24'
        with pytest.raises(RuntimeError):
            client.containers.run("alpine", detach=True, remove=True)

        client = make_fake_client()
        client.api._version = '1.23'
        with pytest.raises(RuntimeError):
            client.containers.run("alpine", detach=True, remove=True)

        client = make_fake_client()
        client.api._version = '1.25'
        client.containers.run("alpine", detach=True, remove=True)
        client.api.remove_container.assert_not_called()
        client.api.create_container.assert_called_with(
            command=None,
            image='alpine',
            detach=True,
            host_config={'AutoRemove': True,
                         'NetworkMode': 'default'}
        )

        client = make_fake_client()
        client.api._version = '1.26'
        client.containers.run("alpine", detach=True, remove=True)
        client.api.remove_container.assert_not_called()
        client.api.create_container.assert_called_with(
            command=None,
            image='alpine',
            detach=True,
            host_config={'AutoRemove': True,
                         'NetworkMode': 'default'}
        )

    def test_create(self):
        client = make_fake_client()
        container = client.containers.create(
            'alpine',
            'echo hello world',
            environment={'FOO': 'BAR'}
        )
        assert isinstance(container, Container)
        assert container.id == FAKE_CONTAINER_ID
        client.api.create_container.assert_called_with(
            image='alpine',
            command='echo hello world',
            environment={'FOO': 'BAR'},
            host_config={'NetworkMode': 'default'}
        )
        client.api.inspect_container.assert_called_with(FAKE_CONTAINER_ID)

    def test_create_with_image_object(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        client.containers.create(image)
        client.api.create_container.assert_called_with(
            image=image.id,
            command=None,
            host_config={'NetworkMode': 'default'}
        )

    def test_get(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        assert isinstance(container, Container)
        assert container.id == FAKE_CONTAINER_ID
        client.api.inspect_container.assert_called_with(FAKE_CONTAINER_ID)

    def test_list(self):
        client = make_fake_client()
        containers = client.containers.list(all=True)
        client.api.containers.assert_called_with(
            all=True,
            before=None,
            filters=None,
            limit=-1,
            since=None
        )
        client.api.inspect_container.assert_called_with(FAKE_CONTAINER_ID)
        assert len(containers) == 1
        assert isinstance(containers[0], Container)
        assert containers[0].id == FAKE_CONTAINER_ID


class ContainerTest(unittest.TestCase):
    def test_name(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        assert container.name == 'foobar'

    def test_status(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        assert container.status == "running"

    def test_attach(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.attach(stream=True)
        client.api.attach.assert_called_with(FAKE_CONTAINER_ID, stream=True)

    def test_commit(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        image = container.commit()
        client.api.commit.assert_called_with(FAKE_CONTAINER_ID,
                                             repository=None,
                                             tag=None)
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID

    def test_diff(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.diff()
        client.api.diff.assert_called_with(FAKE_CONTAINER_ID)

    def test_exec_run(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.exec_run("echo hello world", privileged=True, stream=True)
        client.api.exec_create.assert_called_with(
            FAKE_CONTAINER_ID, "echo hello world", stdout=True, stderr=True,
            stdin=False, tty=False, privileged=True, user='', environment=None,
            workdir=None
        )
        client.api.exec_start.assert_called_with(
            FAKE_EXEC_ID, detach=False, tty=False, stream=True, socket=False
        )

    def test_exec_run_failure(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.exec_run("docker ps", privileged=True, stream=False)
        client.api.exec_create.assert_called_with(
            FAKE_CONTAINER_ID, "docker ps", stdout=True, stderr=True,
            stdin=False, tty=False, privileged=True, user='', environment=None,
            workdir=None
        )
        client.api.exec_start.assert_called_with(
            FAKE_EXEC_ID, detach=False, tty=False, stream=False, socket=False
        )

    def test_export(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.export()
        client.api.export.assert_called_with(
            FAKE_CONTAINER_ID, DEFAULT_DATA_CHUNK_SIZE
        )

    def test_get_archive(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.get_archive('foo')
        client.api.get_archive.assert_called_with(
            FAKE_CONTAINER_ID, 'foo', DEFAULT_DATA_CHUNK_SIZE
        )

    def test_image(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        assert container.image.id == FAKE_IMAGE_ID

    def test_kill(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.kill(signal=5)
        client.api.kill.assert_called_with(FAKE_CONTAINER_ID, signal=5)

    def test_labels(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        assert container.labels == {'foo': 'bar'}

    def test_logs(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.logs()
        client.api.logs.assert_called_with(FAKE_CONTAINER_ID)

    def test_pause(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.pause()
        client.api.pause.assert_called_with(FAKE_CONTAINER_ID)

    def test_put_archive(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.put_archive('path', 'foo')
        client.api.put_archive.assert_called_with(FAKE_CONTAINER_ID,
                                                  'path', 'foo')

    def test_remove(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.remove()
        client.api.remove_container.assert_called_with(FAKE_CONTAINER_ID)

    def test_rename(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.rename("foo")
        client.api.rename.assert_called_with(FAKE_CONTAINER_ID, "foo")

    def test_resize(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.resize(1, 2)
        client.api.resize.assert_called_with(FAKE_CONTAINER_ID, 1, 2)

    def test_restart(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.restart()
        client.api.restart.assert_called_with(FAKE_CONTAINER_ID)

    def test_start(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.start()
        client.api.start.assert_called_with(FAKE_CONTAINER_ID)

    def test_stats(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.stats()
        client.api.stats.assert_called_with(FAKE_CONTAINER_ID)

    def test_stop(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.stop()
        client.api.stop.assert_called_with(FAKE_CONTAINER_ID)

    def test_top(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.top()
        client.api.top.assert_called_with(FAKE_CONTAINER_ID)

    def test_unpause(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.unpause()
        client.api.unpause.assert_called_with(FAKE_CONTAINER_ID)

    def test_update(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.update(cpu_shares=2)
        client.api.update_container.assert_called_with(FAKE_CONTAINER_ID,
                                                       cpu_shares=2)

    def test_wait(self):
        client = make_fake_client()
        container = client.containers.get(FAKE_CONTAINER_ID)
        container.wait()
        client.api.wait.assert_called_with(FAKE_CONTAINER_ID)
