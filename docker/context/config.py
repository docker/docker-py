import hashlib
import json
import os

from docker import utils
from docker.constants import DEFAULT_UNIX_SOCKET, IS_WINDOWS_PLATFORM
from docker.utils.config import (
    DOCKER_CONFIG_FILENAME,
    config_path_from_environment,
    find_config_file,
    home_dir,
)

METAFILE = "meta.json"


def _default_docker_config_path():
    return (
        config_path_from_environment()
        or os.path.join(home_dir(), DOCKER_CONFIG_FILENAME)
    )


def get_current_context_name():
    name = "default"
    docker_cfg_path = find_config_file()
    if docker_cfg_path:
        try:
            with open(docker_cfg_path) as f:
                name = json.load(f).get("currentContext", "default")
        except Exception:
            return "default"
    return name


def write_context_name_to_docker_config(name=None):
    if name == 'default':
        name = None
    docker_cfg_path = find_config_file() or _default_docker_config_path()
    config = {}
    if os.path.exists(docker_cfg_path):
        try:
            with open(docker_cfg_path) as f:
                config = json.load(f)
        except Exception as e:
            return e
    current_context = config.get("currentContext", None)
    if current_context and not name:
        del config["currentContext"]
    elif name:
        config["currentContext"] = name
    else:
        return
    try:
        os.makedirs(os.path.dirname(docker_cfg_path), exist_ok=True)
        with open(docker_cfg_path, "w") as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        return e


def get_context_id(name):
    return hashlib.sha256(name.encode('utf-8')).hexdigest()


def get_context_dir():
    return os.path.join(
        os.path.dirname(find_config_file() or _default_docker_config_path()),
        "contexts",
    )


def get_meta_dir(name=None):
    meta_dir = os.path.join(get_context_dir(), "meta")
    if name:
        return os.path.join(meta_dir, get_context_id(name))
    return meta_dir


def get_meta_file(name):
    return os.path.join(get_meta_dir(name), METAFILE)


def get_tls_dir(name=None, endpoint=""):
    context_dir = get_context_dir()
    if name:
        return os.path.join(context_dir, "tls", get_context_id(name), endpoint)
    return os.path.join(context_dir, "tls")


def get_context_host(path=None, tls=False):
    host = utils.parse_host(path, IS_WINDOWS_PLATFORM, tls)
    if host == DEFAULT_UNIX_SOCKET:
        # remove http+ from default docker socket url
        if host.startswith("http+"):
            host = host[5:]
    return host
