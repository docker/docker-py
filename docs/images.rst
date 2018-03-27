Images
======

.. py:module:: docker.models.images

Manage images on the server.

Methods available on ``client.images``:

.. rst-class:: hide-signature
.. py:class:: ImageCollection

  .. automethod:: build
  .. automethod:: get
  .. automethod:: get_registry_data
  .. automethod:: list(**kwargs)
  .. automethod:: load
  .. automethod:: prune
  .. automethod:: pull
  .. automethod:: push
  .. automethod:: remove
  .. automethod:: search


Image objects
-------------

.. autoclass:: Image()

  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. autoattribute:: id
  .. autoattribute:: labels
  .. autoattribute:: short_id
  .. autoattribute:: tags



  .. automethod:: history
  .. automethod:: reload
  .. automethod:: save
  .. automethod:: tag

RegistryData objects
--------------------

.. autoclass:: RegistryData()

  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. autoattribute:: id
  .. autoattribute:: short_id



  .. automethod:: has_platform
  .. automethod:: pull
  .. automethod:: reload
