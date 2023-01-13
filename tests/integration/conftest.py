import sys
import warnings

import docker.errors
from docker.utils import kwargs_from_env
import pytest

from .base import TEST_IMG


@pytest.fixture(autouse=True, scope='session')
def setup_test_session():
    warnings.simplefilter('error')
    c = docker.APIClient(version='auto', **kwargs_from_env())
    try:
        c.inspect_image(TEST_IMG)
    except docker.errors.NotFound:
        print(f"\npulling {TEST_IMG}", file=sys.stderr)
        for data in c.pull(TEST_IMG, stream=True, decode=True):
            status = data.get("status")
            progress = data.get("progress")
            detail = f"{status} - {progress}"
            print(detail, file=sys.stderr)

        # Double make sure we now have busybox
        c.inspect_image(TEST_IMG)
    c.close()
