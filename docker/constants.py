DEFAULT_DOCKER_API_VERSION = '1.20'
DEFAULT_TIMEOUT_SECONDS = 60
STREAM_HEADER_SIZE_BYTES = 8
CONTAINER_LIMITS_KEYS = [
    'memory', 'memswap', 'cpushares', 'cpusetcpus', 'cpusetmems'
]

INSECURE_REGISTRY_DEPRECATION_WARNING = \
    'The `insecure_registry` argument to {} ' \
    'is deprecated and non-functional. Please remove it.'
