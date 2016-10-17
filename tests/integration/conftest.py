from __future__ import print_function

import sys
import warnings

import docker.errors
import pytest

from ..helpers import BUSYBOX
from ..helpers import docker_client


@pytest.fixture(autouse=True, scope='session')
def setup_test_session():
    warnings.simplefilter('error')
    c = docker_client()
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
