import functools

from .. import errors
from ..utils import utils


def check_api_version(f):
    @functools.wraps(f)
    def wrapped(self, *args, **kwargs):
        if utils.compare_version('1.21', self._version) < 0:
            raise errors.InvalidVersion(
                'The volume API is not available for API version < 1.21'
            )
        return f(self, *args, **kwargs)
    return wrapped


class VolumeApiMixin(object):
    @check_api_version
    def volumes(self, filters=None):
        params = {
            'filter': utils.convert_filters(filters) if filters else None
        }
        url = self._url('/volumes')
        return self._result(self._get(url, params=params), True)

    @check_api_version
    def create_volume(self, name, driver=None, driver_opts=None):
        url = self._url('/volumes')
        if not isinstance(driver_opts, dict):
            raise TypeError('driver_opts must be a dictionary')

        data = {
            'Name': name,
            'Driver': driver,
            'DriverOpts': driver_opts,
        }
        return self._result(self._post(url, data=data), True)

    @check_api_version
    def inspect_volume(self, name):
        url = self._url('/volumes/{0}', name)
        return self._result(self._get(url), True)

    @check_api_version
    def remove_volume(self, name):
        url = self._url('/volumes/{0}', name)
        return self._result(self._delete(url), True)
