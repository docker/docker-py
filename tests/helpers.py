import os
import os.path
import tarfile
import tempfile

import docker
import pytest


def make_tree(dirs, files):
    base = tempfile.mkdtemp()

    for path in dirs:
        os.makedirs(os.path.join(base, path))

    for path in files:
        with open(os.path.join(base, path), 'w') as f:
            f.write("content")

    return base


def simple_tar(path):
    f = tempfile.NamedTemporaryFile()
    t = tarfile.open(mode='w', fileobj=f)

    abs_path = os.path.abspath(path)
    t.add(abs_path, arcname=os.path.basename(path), recursive=False)

    t.close()
    f.seek(0)
    return f


def untar_file(tardata, filename):
    with tarfile.open(mode='r', fileobj=tardata) as t:
        f = t.extractfile(filename)
        result = f.read()
        f.close()
    return result


def requires_api_version(version):
    return pytest.mark.skipif(
        docker.utils.version_lt(
            docker.constants.DEFAULT_DOCKER_API_VERSION, version
        ),
        reason="API version is too low (< {0})".format(version)
    )
