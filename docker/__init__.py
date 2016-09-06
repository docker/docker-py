from .version import version, version_info

__version__ = version
__title__ = 'docker-py'

from .client import Client, AutoVersionClient, from_env # flake8: noqa
