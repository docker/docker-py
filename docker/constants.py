DEFAULT_DOCKER_API_VERSION = '1.21'
DEFAULT_TIMEOUT_SECONDS = 60
ATTACHED_OUTPUT_STREAM_HEADER_FORMAT = '>BxxxL'
CONTAINER_LIMITS_KEYS = [
    'memory', 'memswap', 'cpushares', 'cpusetcpus'
]

INSECURE_REGISTRY_DEPRECATION_WARNING = \
    'The `insecure_registry` argument to {} ' \
    'is deprecated and non-functional. Please remove it.'
