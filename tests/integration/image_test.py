import contextlib
import json
import shutil
import socket
import tarfile
import tempfile
import threading

import pytest
import six
from six.moves import BaseHTTPServer
from six.moves import socketserver


import docker

from .. import helpers

BUSYBOX = helpers.BUSYBOX


class ListImagesTest(helpers.BaseTestCase):
    def test_images(self):
        res1 = self.client.images(all=True)
        self.assertIn('Id', res1[0])
        res10 = res1[0]
        self.assertIn('Created', res10)
        self.assertIn('RepoTags', res10)
        distinct = []
        for img in res1:
            if img['Id'] not in distinct:
                distinct.append(img['Id'])
        self.assertEqual(len(distinct), self.client.info()['Images'])

    def test_images_quiet(self):
        res1 = self.client.images(quiet=True)
        self.assertEqual(type(res1[0]), six.text_type)


class PullImageTest(helpers.BaseTestCase):
    def test_pull(self):
        try:
            self.client.remove_image('hello-world')
        except docker.errors.APIError:
            pass
        res = self.client.pull('hello-world')
        self.tmp_imgs.append('hello-world')
        self.assertEqual(type(res), six.text_type)
        self.assertGreaterEqual(
            len(self.client.images('hello-world')), 1
        )
        img_info = self.client.inspect_image('hello-world')
        self.assertIn('Id', img_info)

    def test_pull_streaming(self):
        try:
            self.client.remove_image('hello-world')
        except docker.errors.APIError:
            pass
        stream = self.client.pull('hello-world', stream=True, decode=True)
        self.tmp_imgs.append('hello-world')
        for chunk in stream:
            assert isinstance(chunk, dict)
        self.assertGreaterEqual(
            len(self.client.images('hello-world')), 1
        )
        img_info = self.client.inspect_image('hello-world')
        self.assertIn('Id', img_info)


class CommitTest(helpers.BaseTestCase):
    def test_commit(self):
        container = self.client.create_container(BUSYBOX, ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res = self.client.commit(id)
        self.assertIn('Id', res)
        img_id = res['Id']
        self.tmp_imgs.append(img_id)
        img = self.client.inspect_image(img_id)
        self.assertIn('Container', img)
        self.assertTrue(img['Container'].startswith(id))
        self.assertIn('ContainerConfig', img)
        self.assertIn('Image', img['ContainerConfig'])
        self.assertEqual(BUSYBOX, img['ContainerConfig']['Image'])
        busybox_id = self.client.inspect_image(BUSYBOX)['Id']
        self.assertIn('Parent', img)
        self.assertEqual(img['Parent'], busybox_id)

    def test_commit_with_changes(self):
        cid = self.client.create_container(BUSYBOX, ['touch', '/test'])
        self.tmp_containers.append(cid)
        self.client.start(cid)
        img_id = self.client.commit(
            cid, changes=['EXPOSE 8000', 'CMD ["bash"]']
        )
        self.tmp_imgs.append(img_id)
        img = self.client.inspect_image(img_id)
        assert 'Container' in img
        assert img['Container'].startswith(cid['Id'])
        assert '8000/tcp' in img['Config']['ExposedPorts']
        assert img['Config']['Cmd'] == ['bash']


class RemoveImageTest(helpers.BaseTestCase):
    def test_remove(self):
        container = self.client.create_container(BUSYBOX, ['touch', '/test'])
        id = container['Id']
        self.client.start(id)
        self.tmp_containers.append(id)
        res = self.client.commit(id)
        self.assertIn('Id', res)
        img_id = res['Id']
        self.tmp_imgs.append(img_id)
        self.client.remove_image(img_id, force=True)
        images = self.client.images(all=True)
        res = [x for x in images if x['Id'].startswith(img_id)]
        self.assertEqual(len(res), 0)


class ImportImageTest(helpers.BaseTestCase):
    '''Base class for `docker import` test cases.'''

    TAR_SIZE = 512 * 1024

    def write_dummy_tar_content(self, n_bytes, tar_fd):
        def extend_file(f, n_bytes):
            f.seek(n_bytes - 1)
            f.write(bytearray([65]))
            f.seek(0)

        tar = tarfile.TarFile(fileobj=tar_fd, mode='w')

        with tempfile.NamedTemporaryFile() as f:
            extend_file(f, n_bytes)
            tarinfo = tar.gettarinfo(name=f.name, arcname='testdata')
            tar.addfile(tarinfo, fileobj=f)

        tar.close()

    @contextlib.contextmanager
    def dummy_tar_stream(self, n_bytes):
        '''Yields a stream that is valid tar data of size n_bytes.'''
        with tempfile.NamedTemporaryFile() as tar_file:
            self.write_dummy_tar_content(n_bytes, tar_file)
            tar_file.seek(0)
            yield tar_file

    @contextlib.contextmanager
    def dummy_tar_file(self, n_bytes):
        '''Yields the name of a valid tar file of size n_bytes.'''
        with tempfile.NamedTemporaryFile(delete=False) as tar_file:
            self.write_dummy_tar_content(n_bytes, tar_file)
            tar_file.seek(0)
            yield tar_file.name

    def test_import_from_bytes(self):
        with self.dummy_tar_stream(n_bytes=500) as f:
            content = f.read()

        # The generic import_image() function cannot import in-memory bytes
        # data that happens to be represented as a string type, because
        # import_image() will try to use it as a filename and usually then
        # trigger an exception. So we test the import_image_from_data()
        # function instead.
        statuses = self.client.import_image_from_data(
            content, repository='test/import-from-bytes')

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        img_id = result['status']
        self.tmp_imgs.append(img_id)

    def test_import_from_file(self):
        with self.dummy_tar_file(n_bytes=self.TAR_SIZE) as tar_filename:
            # statuses = self.client.import_image(
            #     src=tar_filename, repository='test/import-from-file')
            statuses = self.client.import_image_from_file(
                tar_filename, repository='test/import-from-file')

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        self.assertIn('status', result)
        img_id = result['status']
        self.tmp_imgs.append(img_id)

    def test_import_from_stream(self):
        with self.dummy_tar_stream(n_bytes=self.TAR_SIZE) as tar_stream:
            statuses = self.client.import_image(
                src=tar_stream, repository='test/import-from-stream')
            # statuses = self.client.import_image_from_stream(
            #     tar_stream, repository='test/import-from-stream')
        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        self.assertIn('status', result)
        img_id = result['status']
        self.tmp_imgs.append(img_id)

    def test_import_image_from_data_with_changes(self):
        with self.dummy_tar_stream(n_bytes=500) as f:
            content = f.read()

        statuses = self.client.import_image_from_data(
            content, repository='test/import-from-bytes',
            changes=['USER foobar', 'CMD ["echo"]']
        )

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        assert 'error' not in result

        img_id = result['status']
        self.tmp_imgs.append(img_id)

        img_data = self.client.inspect_image(img_id)
        assert img_data is not None
        assert img_data['Config']['Cmd'] == ['echo']
        assert img_data['Config']['User'] == 'foobar'

    def test_import_image_with_changes(self):
        with self.dummy_tar_file(n_bytes=self.TAR_SIZE) as tar_filename:
            statuses = self.client.import_image(
                src=tar_filename, repository='test/import-from-file',
                changes=['USER foobar', 'CMD ["echo"]']
            )

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        assert 'error' not in result

        img_id = result['status']
        self.tmp_imgs.append(img_id)

        img_data = self.client.inspect_image(img_id)
        assert img_data is not None
        assert img_data['Config']['Cmd'] == ['echo']
        assert img_data['Config']['User'] == 'foobar'

    @contextlib.contextmanager
    def temporary_http_file_server(self, stream):
        '''Serve data from an IO stream over HTTP.'''

        class Handler(BaseHTTPServer.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.send_header('Content-Type', 'application/x-tar')
                self.end_headers()
                shutil.copyfileobj(stream, self.wfile)

        server = socketserver.TCPServer(('', 0), Handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.setDaemon(True)
        thread.start()

        yield 'http://%s:%s' % (socket.gethostname(), server.server_address[1])

        server.shutdown()

    @pytest.mark.skipif(True, reason="Doesn't work inside a container - FIXME")
    def test_import_from_url(self):
        # The crappy test HTTP server doesn't handle large files well, so use
        # a small file.
        tar_size = 10240

        with self.dummy_tar_stream(n_bytes=tar_size) as tar_data:
            with self.temporary_http_file_server(tar_data) as url:
                statuses = self.client.import_image(
                    src=url, repository='test/import-from-url')

        result_text = statuses.splitlines()[-1]
        result = json.loads(result_text)

        self.assertNotIn('error', result)

        self.assertIn('status', result)
        img_id = result['status']
        self.tmp_imgs.append(img_id)
