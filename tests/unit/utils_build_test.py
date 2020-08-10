# -*- coding: utf-8 -*-

import os
import os.path
import shutil
import socket
import tarfile
import tempfile
import unittest


from docker.constants import IS_WINDOWS_PLATFORM
from docker.utils import exclude_paths, tar

import pytest

from ..helpers import make_tree


def convert_paths(collection):
    return set(map(convert_path, collection))


def convert_path(path):
    return path.replace('/', os.path.sep)


class ExcludePathsTest(unittest.TestCase):
    dirs = [
        'foo',
        'foo/bar',
        'bar',
        'target',
        'target/subdir',
        'subdir',
        'subdir/target',
        'subdir/target/subdir',
        'subdir/subdir2',
        'subdir/subdir2/target',
        'subdir/subdir2/target/subdir'
    ]

    files = [
        'Dockerfile',
        'Dockerfile.alt',
        '.dockerignore',
        'a.py',
        'a.go',
        'b.py',
        'cde.py',
        'foo/a.py',
        'foo/b.py',
        'foo/bar/a.py',
        'bar/a.py',
        'foo/Dockerfile3',
        'target/file.txt',
        'target/subdir/file.txt',
        'subdir/file.txt',
        'subdir/target/file.txt',
        'subdir/target/subdir/file.txt',
        'subdir/subdir2/file.txt',
        'subdir/subdir2/target/file.txt',
        'subdir/subdir2/target/subdir/file.txt',
    ]

    all_paths = set(dirs + files)

    def setUp(self):
        self.base = make_tree(self.dirs, self.files)

    def tearDown(self):
        shutil.rmtree(self.base)

    def exclude(self, patterns, dockerfile=None):
        return set(exclude_paths(self.base, patterns, dockerfile=dockerfile))

    def test_no_excludes(self):
        assert self.exclude(['']) == convert_paths(self.all_paths)

    def test_no_dupes(self):
        paths = exclude_paths(self.base, ['!a.py'])
        assert sorted(paths) == sorted(set(paths))

    def test_wildcard_exclude(self):
        assert self.exclude(['*']) == set(['Dockerfile', '.dockerignore'])

    def test_exclude_dockerfile_dockerignore(self):
        """
        Even if the .dockerignore file explicitly says to exclude
        Dockerfile and/or .dockerignore, don't exclude them from
        the actual tar file.
        """
        assert self.exclude(['Dockerfile', '.dockerignore']) == convert_paths(
            self.all_paths
        )

    def test_exclude_custom_dockerfile(self):
        """
        If we're using a custom Dockerfile, make sure that's not
        excluded.
        """
        assert self.exclude(['*'], dockerfile='Dockerfile.alt') == set(
            ['Dockerfile.alt', '.dockerignore']
        )

        assert self.exclude(
            ['*'], dockerfile='foo/Dockerfile3'
        ) == convert_paths(set(['foo/Dockerfile3', '.dockerignore']))

        # https://github.com/docker/docker-py/issues/1956
        assert self.exclude(
            ['*'], dockerfile='./foo/Dockerfile3'
        ) == convert_paths(set(['foo/Dockerfile3', '.dockerignore']))

    def test_exclude_dockerfile_child(self):
        includes = self.exclude(['foo/'], dockerfile='foo/Dockerfile3')
        assert convert_path('foo/Dockerfile3') in includes
        assert convert_path('foo/a.py') not in includes

    def test_single_filename(self):
        assert self.exclude(['a.py']) == convert_paths(
            self.all_paths - set(['a.py'])
        )

    def test_single_filename_leading_dot_slash(self):
        assert self.exclude(['./a.py']) == convert_paths(
            self.all_paths - set(['a.py'])
        )

    # As odd as it sounds, a filename pattern with a trailing slash on the
    # end *will* result in that file being excluded.
    def test_single_filename_trailing_slash(self):
        assert self.exclude(['a.py/']) == convert_paths(
            self.all_paths - set(['a.py'])
        )

    def test_wildcard_filename_start(self):
        assert self.exclude(['*.py']) == convert_paths(
            self.all_paths - set(['a.py', 'b.py', 'cde.py'])
        )

    def test_wildcard_with_exception(self):
        assert self.exclude(['*.py', '!b.py']) == convert_paths(
            self.all_paths - set(['a.py', 'cde.py'])
        )

    def test_wildcard_with_wildcard_exception(self):
        assert self.exclude(['*.*', '!*.go']) == convert_paths(
            self.all_paths - set([
                'a.py', 'b.py', 'cde.py', 'Dockerfile.alt',
            ])
        )

    def test_wildcard_filename_end(self):
        assert self.exclude(['a.*']) == convert_paths(
            self.all_paths - set(['a.py', 'a.go'])
        )

    def test_question_mark(self):
        assert self.exclude(['?.py']) == convert_paths(
            self.all_paths - set(['a.py', 'b.py'])
        )

    def test_single_subdir_single_filename(self):
        assert self.exclude(['foo/a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py'])
        )

    def test_single_subdir_single_filename_leading_slash(self):
        assert self.exclude(['/foo/a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py'])
        )

    def test_exclude_include_absolute_path(self):
        base = make_tree([], ['a.py', 'b.py'])
        assert exclude_paths(
            base,
            ['/*', '!/*.py']
        ) == set(['a.py', 'b.py'])

    def test_single_subdir_with_path_traversal(self):
        assert self.exclude(['foo/whoops/../a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py'])
        )

    def test_single_subdir_wildcard_filename(self):
        assert self.exclude(['foo/*.py']) == convert_paths(
            self.all_paths - set(['foo/a.py', 'foo/b.py'])
        )

    def test_wildcard_subdir_single_filename(self):
        assert self.exclude(['*/a.py']) == convert_paths(
            self.all_paths - set(['foo/a.py', 'bar/a.py'])
        )

    def test_wildcard_subdir_wildcard_filename(self):
        assert self.exclude(['*/*.py']) == convert_paths(
            self.all_paths - set(['foo/a.py', 'foo/b.py', 'bar/a.py'])
        )

    def test_directory(self):
        assert self.exclude(['foo']) == convert_paths(
            self.all_paths - set([
                'foo', 'foo/a.py', 'foo/b.py', 'foo/bar', 'foo/bar/a.py',
                'foo/Dockerfile3'
            ])
        )

    def test_directory_with_trailing_slash(self):
        assert self.exclude(['foo']) == convert_paths(
            self.all_paths - set([
                'foo', 'foo/a.py', 'foo/b.py',
                'foo/bar', 'foo/bar/a.py', 'foo/Dockerfile3'
            ])
        )

    def test_directory_with_single_exception(self):
        assert self.exclude(['foo', '!foo/bar/a.py']) == convert_paths(
            self.all_paths - set([
                'foo/a.py', 'foo/b.py', 'foo', 'foo/bar',
                'foo/Dockerfile3'
            ])
        )

    def test_directory_with_subdir_exception(self):
        assert self.exclude(['foo', '!foo/bar']) == convert_paths(
            self.all_paths - set([
                'foo/a.py', 'foo/b.py', 'foo', 'foo/Dockerfile3'
            ])
        )

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Backslash patterns only on Windows'
    )
    def test_directory_with_subdir_exception_win32_pathsep(self):
        assert self.exclude(['foo', '!foo\\bar']) == convert_paths(
            self.all_paths - set([
                'foo/a.py', 'foo/b.py', 'foo', 'foo/Dockerfile3'
            ])
        )

    def test_directory_with_wildcard_exception(self):
        assert self.exclude(['foo', '!foo/*.py']) == convert_paths(
            self.all_paths - set([
                'foo/bar', 'foo/bar/a.py', 'foo', 'foo/Dockerfile3'
            ])
        )

    def test_subdirectory(self):
        assert self.exclude(['foo/bar']) == convert_paths(
            self.all_paths - set(['foo/bar', 'foo/bar/a.py'])
        )

    @pytest.mark.skipif(
        not IS_WINDOWS_PLATFORM, reason='Backslash patterns only on Windows'
    )
    def test_subdirectory_win32_pathsep(self):
        assert self.exclude(['foo\\bar']) == convert_paths(
            self.all_paths - set(['foo/bar', 'foo/bar/a.py'])
        )

    def test_double_wildcard(self):
        assert self.exclude(['**/a.py']) == convert_paths(
            self.all_paths - set(
                ['a.py', 'foo/a.py', 'foo/bar/a.py', 'bar/a.py']
            )
        )

        assert self.exclude(['foo/**/bar']) == convert_paths(
            self.all_paths - set(['foo/bar', 'foo/bar/a.py'])
        )

    def test_single_and_double_wildcard(self):
        assert self.exclude(['**/target/*/*']) == convert_paths(
            self.all_paths - set(
                ['target/subdir/file.txt',
                 'subdir/target/subdir/file.txt',
                 'subdir/subdir2/target/subdir/file.txt']
            )
        )

    def test_trailing_double_wildcard(self):
        assert self.exclude(['subdir/**']) == convert_paths(
            self.all_paths - set(
                ['subdir/file.txt',
                 'subdir/target/file.txt',
                 'subdir/target/subdir/file.txt',
                 'subdir/subdir2/file.txt',
                 'subdir/subdir2/target/file.txt',
                 'subdir/subdir2/target/subdir/file.txt',
                 'subdir/target',
                 'subdir/target/subdir',
                 'subdir/subdir2',
                 'subdir/subdir2/target',
                 'subdir/subdir2/target/subdir']
            )
        )

    def test_double_wildcard_with_exception(self):
        assert self.exclude(['**', '!bar', '!foo/bar']) == convert_paths(
            set([
                'foo/bar', 'foo/bar/a.py', 'bar', 'bar/a.py', 'Dockerfile',
                '.dockerignore',
            ])
        )

    def test_include_wildcard(self):
        # This may be surprising but it matches the CLI's behavior
        # (tested with 18.05.0-ce on linux)
        base = make_tree(['a'], ['a/b.py'])
        assert exclude_paths(
            base,
            ['*', '!*/b.py']
        ) == set()

    def test_last_line_precedence(self):
        base = make_tree(
            [],
            ['garbage.md',
             'trash.md',
             'README.md',
             'README-bis.md',
             'README-secret.md'])
        assert exclude_paths(
            base,
            ['*.md', '!README*.md', 'README-secret.md']
        ) == set(['README.md', 'README-bis.md'])

    def test_parent_directory(self):
        base = make_tree(
            [],
            ['a.py',
             'b.py',
             'c.py'])
        # Dockerignore reference stipulates that absolute paths are
        # equivalent to relative paths, hence /../foo should be
        # equivalent to ../foo. It also stipulates that paths are run
        # through Go's filepath.Clean, which explicitly "replace
        # "/.."  by "/" at the beginning of a path".
        assert exclude_paths(
            base,
            ['../a.py', '/../b.py']
        ) == set(['c.py'])


class TarTest(unittest.TestCase):
    def test_tar_with_excludes(self):
        dirs = [
            'foo',
            'foo/bar',
            'bar',
        ]

        files = [
            'Dockerfile',
            'Dockerfile.alt',
            '.dockerignore',
            'a.py',
            'a.go',
            'b.py',
            'cde.py',
            'foo/a.py',
            'foo/b.py',
            'foo/bar/a.py',
            'bar/a.py',
        ]

        exclude = [
            '*.py',
            '!b.py',
            '!a.go',
            'foo',
            'Dockerfile*',
            '.dockerignore',
        ]

        expected_names = set([
            'Dockerfile',
            '.dockerignore',
            'a.go',
            'b.py',
            'bar',
            'bar/a.py',
        ])

        base = make_tree(dirs, files)
        self.addCleanup(shutil.rmtree, base)

        with tar(base, exclude=exclude) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == sorted(expected_names)

    def test_tar_with_empty_directory(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'foo']

    @pytest.mark.skipif(
        IS_WINDOWS_PLATFORM or os.geteuid() == 0,
        reason='root user always has access ; no chmod on Windows'
    )
    def test_tar_with_inaccessible_file(self):
        base = tempfile.mkdtemp()
        full_path = os.path.join(base, 'foo')
        self.addCleanup(shutil.rmtree, base)
        with open(full_path, 'w') as f:
            f.write('content')
        os.chmod(full_path, 0o222)
        with pytest.raises(IOError) as ei:
            tar(base)

        assert 'Can not read file in context: {}'.format(full_path) in (
            ei.exconly()
        )

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_file_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        with open(os.path.join(base, 'foo'), 'w') as f:
            f.write("content")
        os.makedirs(os.path.join(base, 'bar'))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'bar/foo', 'foo']

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_directory_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        os.symlink('../foo', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'bar/foo', 'foo']

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_with_broken_symlinks(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))

        os.symlink('../baz', os.path.join(base, 'bar/foo'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'bar/foo', 'foo']

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No UNIX sockets on Win32')
    def test_tar_socket_file(self):
        base = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, base)
        for d in ['foo', 'bar']:
            os.makedirs(os.path.join(base, d))
        sock = socket.socket(socket.AF_UNIX)
        self.addCleanup(sock.close)
        sock.bind(os.path.join(base, 'test.sock'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert sorted(tar_data.getnames()) == ['bar', 'foo']

    def tar_test_negative_mtime_bug(self):
        base = tempfile.mkdtemp()
        filename = os.path.join(base, 'th.txt')
        self.addCleanup(shutil.rmtree, base)
        with open(filename, 'w') as f:
            f.write('Invisible Full Moon')
        os.utime(filename, (12345, -3600.0))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            assert tar_data.getnames() == ['th.txt']
            assert tar_data.getmember('th.txt').mtime == -3600

    @pytest.mark.skipif(IS_WINDOWS_PLATFORM, reason='No symlinks on Windows')
    def test_tar_directory_link(self):
        dirs = ['a', 'b', 'a/c']
        files = ['a/hello.py', 'b/utils.py', 'a/c/descend.py']
        base = make_tree(dirs, files)
        self.addCleanup(shutil.rmtree, base)
        os.symlink(os.path.join(base, 'b'), os.path.join(base, 'a/c/b'))
        with tar(base) as archive:
            tar_data = tarfile.open(fileobj=archive)
            names = tar_data.getnames()
            for member in dirs + files:
                assert member in names
            assert 'a/c/b' in names
            assert 'a/c/b/utils.py' not in names
