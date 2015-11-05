import io
import json
import os
import shutil
import tempfile

import six

from . import api_test
from ..base import requires_api_version


class BuildTest(api_test.BaseTestCase):
    def test_build_streaming(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            json.loads(chunk)  # ensure chunk is a single, valid JSON blob
            logs += chunk
        self.assertNotEqual(logs, '')

    def test_build_from_stringio(self):
        if six.PY3:
            return
        script = io.StringIO(six.text_type('\n').join([
            'FROM busybox',
            'MAINTAINER docker-py',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]))
        stream = self.client.build(fileobj=script, stream=True)
        logs = ''
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            logs += chunk
        self.assertNotEqual(logs, '')

    @requires_api_version('1.8')
    def test_build_with_dockerignore(self):
        base_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_dir)

        with open(os.path.join(base_dir, 'Dockerfile'), 'w') as f:
            f.write("\n".join([
                'FROM busybox',
                'MAINTAINER docker-py',
                'ADD . /test',
            ]))

        with open(os.path.join(base_dir, '.dockerignore'), 'w') as f:
            f.write("\n".join([
                'ignored',
                'Dockerfile',
                '.dockerignore',
                '',  # empty line
            ]))

        with open(os.path.join(base_dir, 'not-ignored'), 'w') as f:
            f.write("this file should not be ignored")

        subdir = os.path.join(base_dir, 'ignored', 'subdir')
        os.makedirs(subdir)
        with open(os.path.join(subdir, 'file'), 'w') as f:
            f.write("this file should be ignored")

        tag = 'docker-py-test-build-with-dockerignore'
        stream = self.client.build(
            path=base_dir,
            tag=tag,
        )
        for chunk in stream:
            pass

        c = self.client.create_container(tag, ['ls', '-1A', '/test'])
        self.client.start(c)
        self.client.wait(c)
        logs = self.client.logs(c)

        if six.PY3:
            logs = logs.decode('utf-8')

        self.assertEqual(
            list(filter(None, logs.split('\n'))),
            ['not-ignored'],
        )
