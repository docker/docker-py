Swarm
=====

.. py:module:: docker.models.swarm

Manage `Docker Engine's swarm mode <https://docs.docker.com/engine/swarm/>`_.

To use any swarm methods, you first need to make the Engine part of a swarm. This can be done by either initializing a new swarm with :py:meth:`~Swarm.init`, or joining an existing swarm with :py:meth:`~Swarm.join`.

These methods are available on ``client.swarm``:

.. rst-class:: hide-signature
.. py:class:: Swarm

  .. automethod:: get_unlock_key()
  .. automethod:: init()
  .. automethod:: join()
  .. automethod:: leave()
  .. automethod:: unlock()
  .. automethod:: update()
  .. automethod:: reload()

  .. autoattribute:: version
  .. py:attribute:: attrs

    The raw representation of this object from the server.
