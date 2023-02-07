from ..errors import CheckpointNotFound
from .resource import Collection
from .resource import Model


class Checkpoint(Model):
    """ (Experimental) Local representation of a checkpoint object. Detailed
        configuration may be accessed through the :py:attr:`attrs` attribute.
        Note that local attributes are cached; users may call :py:meth:`reload`
        to query the Docker daemon for the current properties, causing
        :py:attr:`attrs` to be refreshed.
    """
    id_attribute = 'Name'

    @property
    def short_id(self):
        """
        The ID of the object.
        """
        return self.id

    def remove(self):
        """
        Remove this checkpoint. Similar to the
        ``docker checkpoint rm`` command.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        return self.client.api.container_remove_checkpoint(
            self.collection.container_id,
            checkpoint=self.id,
            checkpoint_dir=self.collection.checkpoint_dir,
        )
    
    def __eq__(self, other):
        if isinstance(other, Checkpoint):
            return self.id == other.id
        return self.id == other

class CheckpointCollection(Collection):
    """(Experimental)."""
    model = Checkpoint

    def __init__(self, container_id, checkpoint_dir=None, **kwargs):
        #: The client pointing at the server that this collection of objects
        #: is on.
        super().__init__(**kwargs)
        self.container_id = container_id
        self.checkpoint_dir = checkpoint_dir

    def create(self, checkpoint_id, **kwargs):
        """
        Create a new container checkpoint. Similar to
        ``docker checkpoint create``.

        Args:
            checkpoint_id (str): The id (name) of the checkpoint
            leave_running (bool): Determines if the container should be left
                running after the checkpoint is created

        Returns:
            A :py:class:`Checkpoint` object.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        self.client.api.container_create_checkpoint(
            self.container_id,
            checkpoint=checkpoint_id,
            checkpoint_dir=self.checkpoint_dir,
            **kwargs,
        )
        return Checkpoint(
            attrs={"Name": checkpoint_id},
            client=self.client,
            collection=self
        )

    def get(self, id):
        """
        Get a container checkpoint by id (name).

        Args:
            id (str): The checkpoint id (name)

        Returns:
            A :py:class:`Checkpoint` object.

        Raises:
            :py:class:`docker.errors.NotFound`
                If the checkpoint does not exist.
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        checkpoints = self.list()

        for checkpoint in checkpoints:
            if checkpoint == id:
                return checkpoint

        raise CheckpointNotFound(
            f"Checkpoint with id={id} does not exist"
            f" in checkpoint_dir={self.checkpoint_dir}"
        )

    def list(self):
        """
        List checkpoints. Similar to the ``docker checkpoint ls`` command.

        Returns:
            (list of :py:class:`Checkpoint`)

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        resp = self.client.api.container_checkpoints(
            self.container_id, checkpoint_dir=self.checkpoint_dir
        )
        return [self.prepare_model(checkpoint) for checkpoint in resp or []]

    def prune(self):
        """
        Remove all checkpoints in this collection.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        for checkpoint in self.list():
            checkpoint.remove()
