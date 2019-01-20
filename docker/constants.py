import sys
from .version import version

DEFAULT_DOCKER_API_VERSION = '1.35'
MINIMUM_DOCKER_API_VERSION = '1.21'
DEFAULT_TIMEOUT_SECONDS = 60
STREAM_HEADER_SIZE_BYTES = 8
CONTAINER_LIMITS_KEYS = [
    'memory', 'memswap', 'cpushares', 'cpusetcpus'
]

INSECURE_REGISTRY_DEPRECATION_WARNING = \
    'The `insecure_registry` argument to {} ' \
    'is deprecated and non-functional. Please remove it.'

IS_WINDOWS_PLATFORM = (sys.platform == 'win32')
WINDOWS_LONGPATH_PREFIX = '\\\\?\\'

DEFAULT_USER_AGENT = "docker-sdk-python/{0}".format(version)
DEFAULT_NUM_POOLS = 25
DEFAULT_DATA_CHUNK_SIZE = 1024 * 2048
