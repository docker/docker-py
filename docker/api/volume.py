from .. import errors
from .. import utils


class VolumeApiMixin(object):
    @utils.minimum_version('1.21')
    def volumes(self, filters=None):
        params = {
            'filters': utils.convert_filters(filters) if filters else None
        }
        url = self._url('/volumes')
        return self._result(self._get(url, params=params), True)

    @utils.minimum_version('1.21')
    def create_volume(self, name, driver=None, driver_opts=None, labels=None):
        url = self._url('/volumes/create')
        if driver_opts is not None and not isinstance(driver_opts, dict):
            raise TypeError('driver_opts must be a dictionary')

        data = {
            'Name': name,
            'Driver': driver,
            'DriverOpts': driver_opts,
        }

        if labels is not None:
            if utils.compare_version('1.23', self._version) < 0:
                raise errors.InvalidVersion(
                    'volume labels were introduced in API 1.23'
                )
            if not isinstance(labels, dict):
                raise TypeError('labels must be a dictionary')
            data["Labels"] = labels

        return self._result(self._post_json(url, data=data), True)

    @utils.minimum_version('1.21')
    def inspect_volume(self, name):
        url = self._url('/volumes/{0}', name)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.21')
    def remove_volume(self, name):
        url = self._url('/volumes/{0}', name)
        resp = self._delete(url)
        self._raise_for_status(resp)
