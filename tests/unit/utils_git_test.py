import unittest
import tempfile
import shutil
import os

from docker.utils import git
from docker.errors import GitError

try:
    from unittest import mock
except ImportError:
    import mock

try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse


class GitTest(unittest.TestCase):

    def test_is_git_url(self):
        self.assertTrue(git.is_git_url("https://github.com/repo/root.git"))
        self.assertTrue(git.is_git_url(
            "https://github.com/repo/root.git#branch"
        ))
        self.assertTrue(git.is_git_url(
            "https://github.com/repo/root.git#branch:folder"
        ))

        self.assertTrue(git.is_git_url("http://github.com/repo/root.git"))
        self.assertTrue(git.is_git_url(
            "http://github.com/repo/root.git#branch"
        ))
        self.assertTrue(git.is_git_url(
            "http://github.com/repo/root.git#branch:folder"
        ))

        self.assertTrue(git.is_git_url("git://github.com/repo/root"))
        self.assertTrue(git.is_git_url("git://github.com/repo/root.git"))
        self.assertTrue(git.is_git_url(
            "git://github.com/repo/root.git#branch"
        ))
        self.assertTrue(git.is_git_url(
            "git://github.com/repo/root.git#branch:folder"
        ))

        self.assertTrue(git.is_git_url("github.com/repo/root"))
        self.assertTrue(git.is_git_url("github.com/repo/root.git"))
        self.assertTrue(git.is_git_url("github.com/repo/root.git#branch"))
        self.assertTrue(git.is_git_url(
            "github.com/repo/root.git#branch:folder"
        ))

        self.assertFalse(git.is_git_url("https://server/root"))
        self.assertTrue(git.is_git_url("https://server/root.git"))
        self.assertTrue(git.is_git_url("https://server/root.git#branch"))
        self.assertTrue(git.is_git_url(
            "https://server/root.git#branch:folder"
        ))

        self.assertFalse(git.is_git_url("http://server/context.tar.gz"))
        self.assertFalse(git.is_git_url("https://server/context.tar.gz"))

    @mock.patch('docker.utils.git.tar')
    def test_make_git_context_with_dockerignore(self, mock_tar):
        root_dir = tempfile.mkdtemp(prefix='docker-test-make-git-context')
        self.addCleanup(shutil.rmtree, root_dir)

        with open(os.path.join(root_dir, '.dockerignore'), 'w') as f:
            f.write('\n'.join([
                'ignored',
                'Dockerfile',
                '.dockerignore',
                '!ignored/subdir/excepted-file',
                '',  # empty line
            ]))

        mock_clone = mock.Mock(return_value=root_dir)
        with mock.patch('docker.utils.git.clone', mock_clone):
            git.make_git_build_context('https://github.com/user/repo.git')

        mock_tar.assert_called_once_with(root_dir, exclude=[
            'ignored',
            'Dockerfile',
            '.dockerignore',
            '!ignored/subdir/excepted-file'
        ])

    @mock.patch('docker.utils.git.tar')
    def test_make_git_context_with_kwargs(self, mock_tar):
        mock_clone = mock.Mock(return_value='/tmp')
        with mock.patch('docker.utils.git.clone', mock_clone):
            git.make_git_build_context('https://github.com/user/repo.git',
                                       dockerfile='Dockerfile-test')

        mock_tar.assert_called_once_with('/tmp', exclude=None,
                                         dockerfile='Dockerfile-test')

    def test_clone_args_smart_http(self):
        mock_requests = mock.Mock(
            get=mock.Mock(return_value=mock.Mock(headers={
                "Content-Type": "application/x-git-upload-pack-advertisement"
            }))
        )

        repo_url = 'https://github.com/user/repo.git'
        parsed_url = urlparse(repo_url)

        with mock.patch('docker.utils.git.requests', mock_requests):
            args = git.get_clone_args(parsed_url, '/tmp')
            self.assertListEqual(args, ['clone', '--recursive', '--depth', '1',
                                        repo_url, '/tmp'])

    def test_clone_args_dumb_http(self):
        mock_requests = mock.Mock(
            get=mock.Mock(return_value=mock.Mock(headers={
                "Content-Type": "text/plain"
            }))
        )

        repo_url = 'https://github.com/user/repo.git'
        parsed_url = urlparse(repo_url)

        with mock.patch('docker.utils.git.requests', mock_requests):
            args = git.get_clone_args(parsed_url, '/tmp')
            self.assertListEqual(args,
                                 ['clone', '--recursive', repo_url, '/tmp'])

    def test_clone_args_git(self):
        repo_url = 'git://github.com/user/repo'
        parsed_url = urlparse(repo_url)

        args = git.get_clone_args(parsed_url, '/tmp')
        self.assertListEqual(args, ['clone', '--recursive', '--depth', '1',
                                    repo_url, '/tmp'])

    def test_clone_args_fragment_stripped(self):
        repo_url = 'git://github.com/user/repo#fragment'
        parsed_url = urlparse(repo_url)

        args = git.get_clone_args(parsed_url, '/tmp')
        self.assertListEqual(args, ['clone', '--recursive',
                                    'git://github.com/user/repo', '/tmp'])

    def test_clone_args_git_ssh(self):
        repo_url = 'git@github.com:user/repo.git'
        parsed_url = urlparse(repo_url)

        args = git.get_clone_args(parsed_url, '/tmp')
        self.assertListEqual(args, ['clone', '--recursive', '--depth', '1',
                                    repo_url, '/tmp'])

    def test_git_checkout(self):
        root_dir = tempfile.mkdtemp(prefix='docker-test-git-checkout')
        self.addCleanup(shutil.rmtree, root_dir)

        repo_dir = os.path.join(root_dir, 'repo')
        git.git('init', repo_dir)
        git.git_within_dir(repo_dir, 'config', 'user.email', 'test@docker.com')
        git.git_within_dir(repo_dir, 'config', 'user.name', 'Test')

        with open(os.path.join(repo_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM scratch')

        sub_dir = os.path.join(repo_dir, 'subdir')
        os.mkdir(sub_dir)

        with open(os.path.join(sub_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM scratch\nEXPOSE 5000')

        git.git_within_dir(repo_dir, 'add', '-A')
        git.git_within_dir(repo_dir, 'commit', '-am', 'initial commit')
        git.git_within_dir(repo_dir, 'checkout', '-b', 'test-branch')

        with open(os.path.join(repo_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM scratch\nEXPOSE 6000')

        with open(os.path.join(sub_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM scratch\nEXPOSE 7000')

        git.git_within_dir(repo_dir, 'add', '-A')
        git.git_within_dir(repo_dir, 'commit', '-am', 'branch commit')
        git.git_within_dir(repo_dir, 'checkout', 'master')

        test_cases = (
            ('', ['FROM scratch'], False),
            ('master', ['FROM scratch'], False),
            (':subdir', ['FROM scratch', 'EXPOSE 5000'], False),
            (':nosubdir', '', True),
            (':Dockerfile', '', True),
            ('master:nosubdir', '', True),
            ('master:subdir', ['FROM scratch', 'EXPOSE 5000'], False),
            ('test-branch', ['FROM scratch', 'EXPOSE 6000'], False),
            ('test-branch:', ['FROM scratch', 'EXPOSE 6000'], False),
            ('test-branch:subdir', ['FROM scratch', 'EXPOSE 7000'], False),
        )

        for frag, expected, should_fail in test_cases:
            print('Fragment Test: %s' % frag)
            if should_fail:
                with self.assertRaises(GitError):
                    git.checkout(frag, repo_dir)
                continue
            else:
                context_path = git.checkout(frag, repo_dir)

            with open(os.path.join(context_path, 'Dockerfile'), 'r') as f:
                dockerfile = f.read().splitlines()

            self.assertListEqual(expected, dockerfile)
