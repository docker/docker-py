import sys
import unittest

import pytest
import six

import docker


class BaseTestCase(unittest.TestCase):
    def assertIn(self, object, collection):
        if six.PY2 and sys.version_info[1] <= 6:
            return self.assertTrue(object in collection)
        return super(BaseTestCase, self).assertIn(object, collection)


def requires_api_version(version):
    return pytest.mark.skipif(
        docker.utils.version_lt(
            docker.constants.DEFAULT_DOCKER_API_VERSION, version
        ),
        reason="API version is too low (< {0})".format(version)
    )
