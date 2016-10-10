import functools

from .. import errors
from . import utils


def check_resource(f):
    @functools.wraps(f)
    def wrapped(self, resource_id=None, *args, **kwargs):
        if resource_id is None:
            if kwargs.get('container'):
                resource_id = kwargs.pop('container')
            elif kwargs.get('image'):
                resource_id = kwargs.pop('image')
        if isinstance(resource_id, dict):
            resource_id = resource_id.get('Id', resource_id.get('ID'))
        if not resource_id:
            raise errors.NullResource(
                'image or container param is undefined'
            )
        return f(self, resource_id, *args, **kwargs)
    return wrapped


def minimum_version(version):
    def decorator(f):
        @functools.wraps(f)
        def wrapper(self, *args, **kwargs):
            if utils.version_lt(self._version, version):
                raise errors.InvalidVersion(
                    '{0} is not available for version < {1}'.format(
                        f.__name__, version
                    )
                )
            return f(self, *args, **kwargs)
        return wrapper
    return decorator


def update_headers(f):
    def inner(self, *args, **kwargs):
        if 'HttpHeaders' in self._auth_configs:
            if not kwargs.get('headers'):
                kwargs['headers'] = self._auth_configs['HttpHeaders']
            else:
                kwargs['headers'].update(self._auth_configs['HttpHeaders'])
        return f(self, *args, **kwargs)
    return inner
