import sys
from .version import version

DEFAULT_DOCKER_API_VERSION = '1.24'
DEFAULT_TIMEOUT_SECONDS = 60
STREAM_HEADER_SIZE_BYTES = 8
CONTAINER_LIMITS_KEYS = [
    'memory', 'memswap', 'cpushares', 'cpusetcpus'
]

INSECURE_REGISTRY_DEPRECATION_WARNING = \
    'The `insecure_registry` argument to {} ' \
    'is deprecated and non-functional. Please remove it.'

IS_WINDOWS_PLATFORM = (sys.platform == 'win32')

DEFAULT_USER_AGENT = "docker-py/{0}".format(version)
DEFAULT_NUM_POOLS = 25
