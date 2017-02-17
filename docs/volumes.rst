Volumes
=======

.. py:module:: docker.models.volumes

Manage volumes on the server.

Methods available on ``client.volumes``:

.. rst-class:: hide-signature
.. py:class:: VolumeCollection

  .. automethod:: create
  .. automethod:: get
  .. automethod:: list
  .. automethod:: prune

Volume objects
--------------

.. autoclass:: Volume()

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. autoattribute:: name
  .. py:attribute:: attrs

    The raw representation of this object from the server.


  .. automethod:: reload
  .. automethod:: remove
