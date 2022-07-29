import unittest
import warnings

from docker.constants import DEFAULT_DATA_CHUNK_SIZE
from docker.models.images import Image

from .fake_api import FAKE_IMAGE_ID
from .fake_api_client import make_fake_client


class ImageCollectionTest(unittest.TestCase):
    def test_build(self):
        client = make_fake_client()
        image = client.images.build()
        client.api.build.assert_called_with()
        client.api.inspect_image.assert_called_with(FAKE_IMAGE_ID)
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID

    def test_get(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        client.api.inspect_image.assert_called_with(FAKE_IMAGE_ID)
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID

    def test_labels(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        assert image.labels == {'bar': 'foo'}

    def test_list(self):
        client = make_fake_client()
        images = client.images.list(all=True)
        client.api.images.assert_called_with(all=True, name=None, filters=None)
        assert len(images) == 1
        assert isinstance(images[0], Image)
        assert images[0].id == FAKE_IMAGE_ID

    def test_load(self):
        client = make_fake_client()
        client.images.load('byte stream')
        client.api.load_image.assert_called_with('byte stream')

    def test_pull(self):
        client = make_fake_client()
        image = client.images.pull('test_image:test')
        client.api.pull.assert_called_with(
            'test_image', tag='test', all_tags=False, stream=True
        )
        client.api.inspect_image.assert_called_with('test_image:test')
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID

    def test_pull_tag_precedence(self):
        client = make_fake_client()
        image = client.images.pull('test_image:latest', tag='test')
        client.api.pull.assert_called_with(
            'test_image', tag='test', all_tags=False, stream=True
        )
        client.api.inspect_image.assert_called_with('test_image:test')

        image = client.images.pull('test_image')
        client.api.pull.assert_called_with(
            'test_image', tag='latest', all_tags=False, stream=True
        )
        client.api.inspect_image.assert_called_with('test_image:latest')
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID

    def test_pull_multiple(self):
        client = make_fake_client()
        images = client.images.pull('test_image', all_tags=True)
        client.api.pull.assert_called_with(
            'test_image', tag='latest', all_tags=True, stream=True
        )
        client.api.images.assert_called_with(
            all=False, name='test_image', filters=None
        )
        client.api.inspect_image.assert_called_with(FAKE_IMAGE_ID)
        assert len(images) == 1
        image = images[0]
        assert isinstance(image, Image)
        assert image.id == FAKE_IMAGE_ID

    def test_pull_with_stream_param(self):
        client = make_fake_client()
        with warnings.catch_warnings(record=True) as w:
            client.images.pull('test_image', stream=True)

        assert len(w) == 1
        assert str(w[0].message).startswith(
            '`stream` is not a valid parameter'
        )

    def test_push(self):
        client = make_fake_client()
        client.images.push('foobar', insecure_registry=True)
        client.api.push.assert_called_with(
            'foobar',
            tag=None,
            insecure_registry=True
        )

    def test_remove(self):
        client = make_fake_client()
        client.images.remove('test_image')
        client.api.remove_image.assert_called_with('test_image')

    def test_search(self):
        client = make_fake_client()
        client.images.search('test')
        client.api.search.assert_called_with('test')

    def test_search_limit(self):
        client = make_fake_client()
        client.images.search('test', limit=5)
        client.api.search.assert_called_with('test', limit=5)


class ImageTest(unittest.TestCase):
    def test_short_id(self):
        image = Image(attrs={'Id': 'sha256:b6846070672ce4e8f1f91564ea6782bd675'
                                   'f69d65a6f73ef6262057ad0a15dcd'})
        assert image.short_id == 'sha256:b6846070672c'

        image = Image(attrs={'Id': 'b6846070672ce4e8f1f91564ea6782bd675'
                                   'f69d65a6f73ef6262057ad0a15dcd'})
        assert image.short_id == 'b6846070672c'

    def test_tags(self):
        image = Image(attrs={
            'RepoTags': ['test_image:latest']
        })
        assert image.tags == ['test_image:latest']

        image = Image(attrs={
            'RepoTags': ['<none>:<none>']
        })
        assert image.tags == []

        image = Image(attrs={
            'RepoTags': None
        })
        assert image.tags == []

    def test_history(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        image.history()
        client.api.history.assert_called_with(FAKE_IMAGE_ID)

    def test_remove(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        image.remove()
        client.api.remove_image.assert_called_with(
            FAKE_IMAGE_ID,
            force=False,
            noprune=False,
        )

    def test_save(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        image.save()
        client.api.get_image.assert_called_with(
            FAKE_IMAGE_ID, DEFAULT_DATA_CHUNK_SIZE
        )

    def test_tag(self):
        client = make_fake_client()
        image = client.images.get(FAKE_IMAGE_ID)
        image.tag('foo')
        client.api.tag.assert_called_with(FAKE_IMAGE_ID, 'foo', tag=None)
