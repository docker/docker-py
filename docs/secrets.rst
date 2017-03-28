Secrets
=======

.. py:module:: docker.models.secrets

Manage secrets on the server.

Methods available on ``client.secrets``:

.. rst-class:: hide-signature
.. py:class:: SecretCollection

  .. automethod:: create
  .. automethod:: get
  .. automethod:: list


Secret objects
--------------

.. autoclass:: Secret()

  .. autoattribute:: id
  .. autoattribute:: name
  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. automethod:: reload
  .. automethod:: remove
