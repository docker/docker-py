Services
========

.. py:module:: docker.models.services

Manage services on a swarm. For more information about services, `see the Engine documentation <https://docs.docker.com/engine/swarm/services/>`_.

Before you can use any of these methods, you first need to :doc:`join or initialize a swarm <swarm>`.

Methods available on ``client.services``:

.. rst-class:: hide-signature
.. py:class:: ServiceCollection

  .. automethod:: create
  .. automethod:: get
  .. automethod:: list

Service objects
---------------

.. autoclass:: Service()

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. autoattribute:: name
  .. autoattribute:: version
  .. py:attribute:: attrs

    The raw representation of this object from the server.


  .. automethod:: force_update
  .. automethod:: logs
  .. automethod:: reload
  .. automethod:: remove
  .. automethod:: scale
  .. automethod:: tasks
  .. automethod:: update
