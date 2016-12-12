Nodes
=====

.. py:module:: docker.models.nodes

Get and list nodes in a swarm. Before you can use these methods, you first need to :doc:`join or initialize a swarm <swarm>`.

Methods available on ``client.nodes``:

.. rst-class:: hide-signature
.. py:class:: NodeCollection

  .. automethod:: get(id_or_name)
  .. automethod:: list(**kwargs)

Node objects
------------

.. autoclass:: Node()

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. autoattribute:: version

  .. automethod:: reload
  .. automethod:: update
