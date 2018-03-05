import io
import os
import shutil
import tempfile

from docker import errors

import pytest
import six

from .base import BaseAPIIntegrationTest, BUSYBOX
from ..helpers import random_name, requires_api_version, requires_experimental


class BuildTest(BaseAPIIntegrationTest):
    def test_build_streaming(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]).encode('ascii'))
        stream = self.client.build(fileobj=script, decode=True)
        logs = []
        for chunk in stream:
            logs.append(chunk)
        assert len(logs) > 0

    def test_build_from_stringio(self):
        if six.PY3:
            return
        script = io.StringIO(six.text_type('\n').join([
            'FROM busybox',
            'RUN mkdir -p /tmp/test',
            'EXPOSE 8080',
            'ADD https://dl.dropboxusercontent.com/u/20637798/silence.tar.gz'
            ' /tmp/silence.tar.gz'
        ]))
        stream = self.client.build(fileobj=script)
        logs = ''
        for chunk in stream:
            if six.PY3:
                chunk = chunk.decode('utf-8')
            logs += chunk
        assert logs != ''

    def test_build_with_dockerignore(self):
        base_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_dir)

        with open(os.path.join(base_dir, 'Dockerfile'), 'w') as f:
            f.write("\n".join([
                'FROM busybox',
                'ADD . /test',
            ]))

        with open(os.path.join(base_dir, '.dockerignore'), 'w') as f:
            f.write("\n".join([
                'ignored',
                'Dockerfile',
                '.dockerignore',
                '!ignored/subdir/excepted-file',
                '',  # empty line,
                '#*',  # comment line
            ]))

        with open(os.path.join(base_dir, 'not-ignored'), 'w') as f:
            f.write("this file should not be ignored")

        with open(os.path.join(base_dir, '#file.txt'), 'w') as f:
            f.write('this file should not be ignored')

        subdir = os.path.join(base_dir, 'ignored', 'subdir')
        os.makedirs(subdir)
        with open(os.path.join(subdir, 'file'), 'w') as f:
            f.write("this file should be ignored")

        with open(os.path.join(subdir, 'excepted-file'), 'w') as f:
            f.write("this file should not be ignored")

        tag = 'docker-py-test-build-with-dockerignore'
        stream = self.client.build(
            path=base_dir,
            tag=tag,
        )
        for chunk in stream:
            pass

        c = self.client.create_container(tag, ['find', '/test', '-type', 'f'])
        self.client.start(c)
        self.client.wait(c)
        logs = self.client.logs(c)

        if six.PY3:
            logs = logs.decode('utf-8')

        assert sorted(list(filter(None, logs.split('\n')))) == sorted([
            '/test/#file.txt',
            '/test/ignored/subdir/excepted-file',
            '/test/not-ignored'
        ])

    def test_build_with_buildargs(self):
        script = io.BytesIO('\n'.join([
            'FROM scratch',
            'ARG test',
            'USER $test'
        ]).encode('ascii'))

        stream = self.client.build(
            fileobj=script, tag='buildargs', buildargs={'test': 'OK'}
        )
        self.tmp_imgs.append('buildargs')
        for chunk in stream:
            pass

        info = self.client.inspect_image('buildargs')
        assert info['Config']['User'] == 'OK'

    @requires_api_version('1.22')
    def test_build_shmsize(self):
        script = io.BytesIO('\n'.join([
            'FROM scratch',
            'CMD sh -c "echo \'Hello, World!\'"',
        ]).encode('ascii'))

        tag = 'shmsize'
        shmsize = 134217728

        stream = self.client.build(
            fileobj=script, tag=tag, shmsize=shmsize
        )
        self.tmp_imgs.append(tag)
        for chunk in stream:
            pass

        # There is currently no way to get the shmsize
        # that was used to build the image

    @requires_api_version('1.23')
    def test_build_labels(self):
        script = io.BytesIO('\n'.join([
            'FROM scratch',
        ]).encode('ascii'))

        labels = {'test': 'OK'}

        stream = self.client.build(
            fileobj=script, tag='labels', labels=labels
        )
        self.tmp_imgs.append('labels')
        for chunk in stream:
            pass

        info = self.client.inspect_image('labels')
        assert info['Config']['Labels'] == labels

    @requires_api_version('1.25')
    def test_build_with_cache_from(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'ENV FOO=bar',
            'RUN touch baz',
            'RUN touch bax',
        ]).encode('ascii'))

        stream = self.client.build(fileobj=script, tag='build1')
        self.tmp_imgs.append('build1')
        for chunk in stream:
            pass

        stream = self.client.build(
            fileobj=script, tag='build2', cache_from=['build1'],
            decode=True
        )
        self.tmp_imgs.append('build2')
        counter = 0
        for chunk in stream:
            if 'Using cache' in chunk.get('stream', ''):
                counter += 1
        assert counter == 3
        self.client.remove_image('build2')

        counter = 0
        stream = self.client.build(
            fileobj=script, tag='build2', cache_from=['nosuchtag'],
            decode=True
        )
        for chunk in stream:
            if 'Using cache' in chunk.get('stream', ''):
                counter += 1
        assert counter == 0

    @requires_api_version('1.29')
    def test_build_container_with_target(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox as first',
            'RUN mkdir -p /tmp/test',
            'RUN touch /tmp/silence.tar.gz',
            'FROM alpine:latest',
            'WORKDIR /root/'
            'COPY --from=first /tmp/silence.tar.gz .',
            'ONBUILD RUN echo "This should not be in the final image"'
        ]).encode('ascii'))

        stream = self.client.build(
            fileobj=script, target='first', tag='build1'
        )
        self.tmp_imgs.append('build1')
        for chunk in stream:
            pass

        info = self.client.inspect_image('build1')
        assert not info['Config']['OnBuild']

    @requires_api_version('1.25')
    def test_build_with_network_mode(self):
        # Set up pingable endpoint on custom network
        network = self.client.create_network(random_name())['Id']
        self.tmp_networks.append(network)
        container = self.client.create_container(BUSYBOX, 'top')
        self.tmp_containers.append(container)
        self.client.start(container)
        self.client.connect_container_to_network(
            container, network, aliases=['pingtarget.docker']
        )

        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN ping -c1 pingtarget.docker'
        ]).encode('ascii'))

        stream = self.client.build(
            fileobj=script, network_mode=network,
            tag='dockerpytest_customnetbuild'
        )

        self.tmp_imgs.append('dockerpytest_customnetbuild')
        for chunk in stream:
            pass

        assert self.client.inspect_image('dockerpytest_customnetbuild')

        script.seek(0)
        stream = self.client.build(
            fileobj=script, network_mode='none',
            tag='dockerpytest_nonebuild', nocache=True, decode=True
        )

        self.tmp_imgs.append('dockerpytest_nonebuild')
        logs = [chunk for chunk in stream]
        assert 'errorDetail' in logs[-1]
        assert logs[-1]['errorDetail']['code'] == 1

        with pytest.raises(errors.NotFound):
            self.client.inspect_image('dockerpytest_nonebuild')

    @requires_api_version('1.27')
    def test_build_with_extra_hosts(self):
        img_name = 'dockerpytest_extrahost_build'
        self.tmp_imgs.append(img_name)

        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN ping -c1 hello.world.test',
            'RUN ping -c1 extrahost.local.test',
            'RUN cp /etc/hosts /hosts-file'
        ]).encode('ascii'))

        stream = self.client.build(
            fileobj=script, tag=img_name,
            extra_hosts={
                'extrahost.local.test': '127.0.0.1',
                'hello.world.test': '127.0.0.1',
            }, decode=True
        )
        for chunk in stream:
            if 'errorDetail' in chunk:
                pytest.fail(chunk)

        assert self.client.inspect_image(img_name)
        ctnr = self.run_container(img_name, 'cat /hosts-file')
        self.tmp_containers.append(ctnr)
        logs = self.client.logs(ctnr)
        if six.PY3:
            logs = logs.decode('utf-8')
        assert '127.0.0.1\textrahost.local.test' in logs
        assert '127.0.0.1\thello.world.test' in logs

    @requires_experimental(until=None)
    @requires_api_version('1.25')
    def test_build_squash(self):
        script = io.BytesIO('\n'.join([
            'FROM busybox',
            'RUN echo blah > /file_1',
            'RUN echo blahblah > /file_2',
            'RUN echo blahblahblah > /file_3'
        ]).encode('ascii'))

        def build_squashed(squash):
            tag = 'squash' if squash else 'nosquash'
            stream = self.client.build(
                fileobj=script, tag=tag, squash=squash
            )
            self.tmp_imgs.append(tag)
            for chunk in stream:
                pass

            return self.client.inspect_image(tag)

        non_squashed = build_squashed(False)
        squashed = build_squashed(True)
        assert len(non_squashed['RootFS']['Layers']) == 4
        assert len(squashed['RootFS']['Layers']) == 2

    def test_build_stderr_data(self):
        control_chars = ['\x1b[91m', '\x1b[0m']
        snippet = 'Ancient Temple (Mystic Oriental Dream ~ Ancient Temple)'
        script = io.BytesIO(b'\n'.join([
            b'FROM busybox',
            'RUN sh -c ">&2 echo \'{0}\'"'.format(snippet).encode('utf-8')
        ]))

        stream = self.client.build(
            fileobj=script, decode=True, nocache=True
        )
        lines = []
        for chunk in stream:
            lines.append(chunk.get('stream'))
        expected = '{0}{2}\n{1}'.format(
            control_chars[0], control_chars[1], snippet
        )
        assert any([line == expected for line in lines])

    def test_build_gzip_encoding(self):
        base_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_dir)

        with open(os.path.join(base_dir, 'Dockerfile'), 'w') as f:
            f.write("\n".join([
                'FROM busybox',
                'ADD . /test',
            ]))

        stream = self.client.build(
            path=base_dir, decode=True, nocache=True,
            gzip=True
        )

        lines = []
        for chunk in stream:
            lines.append(chunk)

        assert 'Successfully built' in lines[-1]['stream']

    def test_build_with_dockerfile_empty_lines(self):
        base_dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base_dir)
        with open(os.path.join(base_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM busybox\n')
        with open(os.path.join(base_dir, '.dockerignore'), 'w') as f:
            f.write('\n'.join([
                '   ',
                '',
                '\t\t',
                '\t     ',
            ]))

        stream = self.client.build(
            path=base_dir, decode=True, nocache=True
        )

        lines = []
        for chunk in stream:
            lines.append(chunk)
        assert 'Successfully built' in lines[-1]['stream']

    def test_build_gzip_custom_encoding(self):
        with pytest.raises(errors.DockerException):
            self.client.build(path='.', gzip=True, encoding='text/html')

    @requires_api_version('1.32')
    @requires_experimental(until=None)
    def test_build_invalid_platform(self):
        script = io.BytesIO('FROM busybox\n'.encode('ascii'))

        with pytest.raises(errors.APIError) as excinfo:
            stream = self.client.build(fileobj=script, platform='foobar')
            for _ in stream:
                pass

        assert excinfo.value.status_code == 400
        assert 'invalid platform' in excinfo.exconly()
