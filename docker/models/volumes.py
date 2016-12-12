from .resource import Model, Collection


class Volume(Model):
    """A volume."""
    id_attribute = 'Name'

    @property
    def name(self):
        """The name of the volume."""
        return self.attrs['Name']

    def remove(self):
        """Remove this volume."""
        return self.client.api.remove_volume(self.id)


class VolumeCollection(Collection):
    """Volumes on the Docker server."""
    model = Volume

    def create(self, name, **kwargs):
        """
        Create a volume.

        Args:
            name (str): Name of the volume
            driver (str): Name of the driver used to create the volume
            driver_opts (dict): Driver options as a key-value dictionary
            labels (dict): Labels to set on the volume

        Returns:
            (:py:class:`Volume`): The volume created.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.

        Example:

            >>> volume = client.volumes.create(name='foobar', driver='local',
                    driver_opts={'foo': 'bar', 'baz': 'false'},
                    labels={"key": "value"})

        """
        obj = self.client.api.create_volume(name, **kwargs)
        return self.prepare_model(obj)

    def get(self, volume_id):
        """
        Get a volume.

        Args:
            volume_id (str): Volume name.

        Returns:
            (:py:class:`Volume`): The volume.

        Raises:
            :py:class:`docker.errors.NotFound`
                If the volume does not exist.
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        return self.prepare_model(self.client.api.inspect_volume(volume_id))

    def list(self, **kwargs):
        """
        List volumes. Similar to the ``docker volume ls`` command.

        Args:
            filters (dict): Server-side list filtering options.

        Returns:
            (list of :py:class:`Volume`): The volumes.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        resp = self.client.api.volumes(**kwargs)
        if not resp.get('Volumes'):
            return []
        return [self.prepare_model(obj) for obj in resp['Volumes']]
