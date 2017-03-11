from .base import BaseAPIIntegrationTest
import os
import tempfile
import shutil

from docker.utils import make_git_build_context
from docker.utils import git


class GitBuildTest(BaseAPIIntegrationTest):

    def setUp(self):
        super(GitBuildTest, self).setUp()

        root_dir = tempfile.mkdtemp(prefix='docker-test-git-checkout')
        self.addCleanup(shutil.rmtree, root_dir)

        repo_dir = os.path.join(root_dir, 'repo')
        git.git('init', repo_dir)
        git.git_within_dir(repo_dir, 'config', 'user.email', 'test@docker.com')
        git.git_within_dir(repo_dir, 'config', 'user.name', 'Test')

        with open(os.path.join(repo_dir, 'Dockerfile'), 'w') as f:
            f.write('FROM busybox')

        git.git_within_dir(repo_dir, 'add', '-A')
        git.git_within_dir(repo_dir, 'commit', '-am', 'initial commit')

        self.repo_dir = repo_dir

    def test_build_git_repo(self):
        fileobj = make_git_build_context('file://' + self.repo_dir)

        stream = self.client.build(fileobj=fileobj, custom_context=True,
                                   decode=True)

        lines = []
        for chunk in stream:
            lines.append(chunk)

        assert 'Successfully built' in lines[-1]['stream']
