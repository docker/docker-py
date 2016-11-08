from .. import errors
from .. import utils


class VolumeApiMixin(object):
    @utils.minimum_version('1.21')
    def volumes(self, filters=None):
        """
        List volumes currently registered by the docker daemon. Similar to the
        ``docker volume ls`` command.

        Args:
            filters (dict): Server-side list filtering options.

        Returns:
            (dict): Dictionary with list of volume objects as value of the
            ``Volumes`` key.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.

        Example:

            >>> cli.volumes()
            {u'Volumes': [{u'Driver': u'local',
               u'Mountpoint': u'/var/lib/docker/volumes/foobar/_data',
               u'Name': u'foobar'},
              {u'Driver': u'local',
               u'Mountpoint': u'/var/lib/docker/volumes/baz/_data',
               u'Name': u'baz'}]}
        """

        params = {
            'filters': utils.convert_filters(filters) if filters else None
        }
        url = self._url('/volumes')
        return self._result(self._get(url, params=params), True)

    @utils.minimum_version('1.21')
    def create_volume(self, name, driver=None, driver_opts=None, labels=None):
        """
        Create and register a named volume

        Args:
            name (str): Name of the volume
            driver (str): Name of the driver used to create the volume
            driver_opts (dict): Driver options as a key-value dictionary
            labels (dict): Labels to set on the volume

        Returns:
            (dict): The created volume reference object

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.

        Example:

            >>> volume = cli.create_volume(name='foobar', driver='local',
                    driver_opts={'foo': 'bar', 'baz': 'false'},
                    labels={"key": "value"})
            >>> print(volume)
            {u'Driver': u'local',
             u'Labels': {u'key': u'value'},
             u'Mountpoint': u'/var/lib/docker/volumes/foobar/_data',
             u'Name': u'foobar'}

        """
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
        """
        Retrieve volume info by name.

        Args:
            name (str): volume name

        Returns:
            (dict): Volume information dictionary

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.

        Example:

            >>> cli.inspect_volume('foobar')
            {u'Driver': u'local',
             u'Mountpoint': u'/var/lib/docker/volumes/foobar/_data',
             u'Name': u'foobar'}

        """
        url = self._url('/volumes/{0}', name)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.21')
    def remove_volume(self, name):
        """
        Remove a volume. Similar to the ``docker volume rm`` command.

        Args:
            name (str): The volume's name

        Raises:

        ``docker.errors.APIError``: If volume failed to remove.
        """
        url = self._url('/volumes/{0}', name)
        resp = self._delete(url)
        self._raise_for_status(resp)
