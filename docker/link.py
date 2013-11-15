import os
from urlparse import urlparse

def require(alias):
    """ Return the ip and port for an alias using the default port that is linked into the container """
    raw = os.environ.get('%s_PORT' % alias.upper(), None)
    return _parse_var(raw)

def require_port(alias, port, proto='tcp'):
    """ Return the ip and port for an alias that is linked into the container """
    raw = os.environ.get('%s_PORT_%s_%s' % (alias.upper(), port, proto.upper()), None)
    return _parse_var(raw)
    
def require_env(alias, env_key):
    """ Return the linked containers environment var for an alias """
    return os.environ.get('%s_ENV_%s' % (alias.upper(), env_key.upper()), None)

def _parse_var(raw):
    if raw is None:
        return None
    p = urlparse(raw)
    parts = p.netloc.split(':')
    return (p.scheme, parts[0], parts[1],)

