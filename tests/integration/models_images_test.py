import io
import tempfile

import docker
import pytest

from .base import BaseIntegrationTest, TEST_IMG, TEST_API_VERSION
from ..helpers import random_name


class ImageCollectionTest(BaseIntegrationTest):

    def test_build(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image, _ = client.images.build(fileobj=io.BytesIO(
            "FROM alpine\n"
            "CMD echo hello world".encode('ascii')
        ))
        self.tmp_imgs.append(image.id)
        assert client.containers.run(image) == b"hello world\n"

    # @pytest.mark.xfail(reason='Engine 1.13 responds with status 500')
    def test_build_with_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with pytest.raises(docker.errors.BuildError) as cm:
            client.images.build(fileobj=io.BytesIO(
                "FROM alpine\n"
                "RUN exit 1".encode('ascii')
            ))
        assert (
            "The command '/bin/sh -c exit 1' returned a non-zero code: 1"
        ) in cm.exconly()
        assert cm.value.build_log

    def test_build_with_multiple_success(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image, _ = client.images.build(
            tag='some-tag', fileobj=io.BytesIO(
                "FROM alpine\n"
                "CMD echo hello world".encode('ascii')
            )
        )
        self.tmp_imgs.append(image.id)
        assert client.containers.run(image) == b"hello world\n"

    def test_build_with_success_build_output(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image, _ = client.images.build(
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
        image = client.images.pull('alpine', tag='3.10')
        assert 'alpine:3.10' in image.attrs['RepoTags']

    def test_pull_with_sha(self):
        image_ref = (
            'hello-world@sha256:083de497cff944f969d8499ab94f07134c50bcf5e6b95'
            '59b27182d3fa80ce3f7'
        )
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.pull(image_ref)
        assert image_ref in image.attrs['RepoDigests']

    def test_pull_multiple(self):
        client = docker.from_env(version=TEST_API_VERSION)
        images = client.images.pull('hello-world')
        assert len(images) >= 1
        assert any([
            'hello-world:latest' in img.attrs['RepoTags'] for img in images
        ])

    def test_load_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        with pytest.raises(docker.errors.ImageLoadError):
            client.images.load('abc')

    def test_save_and_load(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.get(TEST_IMG)
        with tempfile.TemporaryFile() as f:
            stream = image.save()
            for chunk in stream:
                f.write(chunk)

            f.seek(0)
            result = client.images.load(f.read())

        assert len(result) == 1
        assert result[0].id == image.id

    def test_save_and_load_repo_name(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.get(TEST_IMG)
        additional_tag = random_name()
        image.tag(additional_tag)
        self.tmp_imgs.append(additional_tag)
        image.reload()
        with tempfile.TemporaryFile() as f:
            stream = image.save(named='{}:latest'.format(additional_tag))
            for chunk in stream:
                f.write(chunk)

            f.seek(0)
            client.images.remove(additional_tag, force=True)
            result = client.images.load(f.read())

        assert len(result) == 1
        assert result[0].id == image.id
        assert '{}:latest'.format(additional_tag) in result[0].tags

    def test_save_name_error(self):
        client = docker.from_env(version=TEST_API_VERSION)
        image = client.images.get(TEST_IMG)
        with pytest.raises(docker.errors.InvalidArgument):
            image.save(named='sakuya/izayoi')


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
