Containers
==========

.. py:module:: docker.models.containers

Run and manage containers on the server.

Methods available on ``client.containers``:

.. rst-class:: hide-signature
.. autoclass:: ContainerCollection

  .. automethod:: run(image, command=None, **kwargs)
  .. automethod:: create(image, command=None, **kwargs)
  .. automethod:: get(id_or_name)
  .. automethod:: list(**kwargs)

Container objects
-----------------

.. autoclass:: Container()

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. autoattribute:: name
  .. autoattribute:: status
  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. automethod:: attach
  .. automethod:: attach_socket
  .. automethod:: commit
  .. automethod:: diff
  .. automethod:: exec_run
  .. automethod:: export
  .. automethod:: get_archive
  .. automethod:: kill
  .. automethod:: logs
  .. automethod:: pause
  .. automethod:: put_archive
  .. automethod:: remove
  .. automethod:: rename
  .. automethod:: resize
  .. automethod:: restart
  .. automethod:: start
  .. automethod:: stats
  .. automethod:: stop
  .. automethod:: top
  .. automethod:: unpause
  .. automethod:: update
