Images
======

.. py:module:: docker.models.images

Manage images on the server.

Methods available on ``client.images``:

.. rst-class:: hide-signature
.. py:class:: ImageCollection

  .. automethod:: build
  .. automethod:: get
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

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. autoattribute:: tags
  .. py:attribute:: attrs

    The raw representation of this object from the server.


  .. automethod:: history
  .. automethod:: reload
  .. automethod:: save
  .. automethod:: tag
