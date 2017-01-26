from __future__ import print_function

import sys
import warnings

import docker.errors
from docker.utils import kwargs_from_env
import pytest

from .base import BUSYBOX


@pytest.fixture(autouse=True, scope='session')
def setup_test_session():
    warnings.simplefilter('error')
    c = docker.APIClient(version='auto', **kwargs_from_env())
    try:
        c.inspect_image(BUSYBOX)
    except docker.errors.NotFound:
        print("\npulling {0}".format(BUSYBOX), file=sys.stderr)
        for data in c.pull(BUSYBOX, stream=True, decode=True):
            status = data.get("status")
            progress = data.get("progress")
            detail = "{0} - {1}".format(status, progress)
            print(detail, file=sys.stderr)

        # Double make sure we now have busybox
        c.inspect_image(BUSYBOX)
    c.close()
