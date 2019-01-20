Configs
=======

.. py:module:: docker.models.configs

Manage configs on the server.

Methods available on ``client.configs``:

.. rst-class:: hide-signature
.. py:class:: ConfigCollection

  .. automethod:: create
  .. automethod:: get
  .. automethod:: list


Config objects
--------------

.. autoclass:: Config()

  .. autoattribute:: id
  .. autoattribute:: name
  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. automethod:: reload
  .. automethod:: remove
