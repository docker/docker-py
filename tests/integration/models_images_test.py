import io

import docker
import pytest

from .base import BaseIntegrationTest, TEST_API_VERSION


class ImageCollectionTest(BaseIntegrationTest):

    def test_build(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.build(fileobj=io.BytesIO(
            "FROM alpine\n"
            "CMD echo hello world".encode('ascii')
        ))
        self.tmp_imgs.append(image.id)
        assert client.containers.run(image) == b"hello world\n"

    @pytest.mark.xfail(reason='Engine 1.13 responds with status 500')
    def test_build_with_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with self.assertRaises(docker.errors.BuildError) as cm:
            client.images.build(fileobj=io.BytesIO(
                "FROM alpine\n"
                "NOTADOCKERFILECOMMAND".encode('ascii')
            ))
        assert str(cm.exception) == ("Unknown instruction: "
                                     "NOTADOCKERFILECOMMAND")

    def test_build_with_multiple_success(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.build(
            tag='some-tag', fileobj=io.BytesIO(
                "FROM alpine\n"
                "CMD echo hello world".encode('ascii')
            )
        )
        self.tmp_imgs.append(image.id)
        assert client.containers.run(image) == b"hello world\n"

    def test_build_with_success_build_output(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.build(
            tag='dup-txt-tag', fileobj=io.BytesIO(
                "FROM alpine\n"
                "CMD echo Successfully built abcd1234".encode('ascii')
            )
        )
        self.tmp_imgs.append(image.id)
        assert client.containers.run(image) == b"Successfully built abcd1234\n"

    def test_list(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.pull('alpine:latest')
        assert image.id in get_ids(client.images.list())

    def test_list_with_repository(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.pull('alpine:latest')
        assert image.id in get_ids(client.images.list('alpine'))
        assert image.id in get_ids(client.images.list('alpine:latest'))

    def test_pull(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.pull('alpine:latest')
        assert 'alpine:latest' in image.attrs['RepoTags']

    def test_pull_with_tag(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.pull('alpine', tag='3.3')
        assert 'alpine:3.3' in image.attrs['RepoTags']


class ImageTest(BaseIntegrationTest):

    def test_tag_and_remove(self):
        repo = 'dockersdk.tests.images.test_tag'
        tag = 'some-tag'
        identifier = '{}:{}'.format(repo, tag)

        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.pull('alpine:latest')

        result = image.tag(repo, tag)
        assert result is True
        self.tmp_imgs.append(identifier)
        assert image.id in get_ids(client.images.list(repo))
        assert image.id in get_ids(client.images.list(identifier))

        client.images.remove(identifier)
        assert image.id not in get_ids(client.images.list(repo))
        assert image.id not in get_ids(client.images.list(identifier))

        assert image.id in get_ids(client.images.list('alpine:latest'))


def get_ids(images):
    return [i.id for i in images]
