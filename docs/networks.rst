Networks
========

.. py:module:: docker.models.networks

Create and manage networks on the server. For more information about networks, `see the Engine documentation <https://docs.docker.com/engine/userguide/networking/>`_.

Methods available on ``client.networks``:

.. rst-class:: hide-signature
.. py:class:: NetworkCollection

  .. automethod:: create
  .. automethod:: get
  .. automethod:: list
  .. automethod:: prune

Network objects
-----------------

.. autoclass:: Network()

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. autoattribute:: name
  .. autoattribute:: containers
  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. automethod:: connect
  .. automethod:: disconnect
  .. automethod:: reload
  .. automethod:: remove
