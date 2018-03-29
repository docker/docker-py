Client
======
.. py:module:: docker.client


Creating a client
-----------------

To communicate with the Docker daemon, you first need to instantiate a client. The easiest way to do that is by calling the function :py:func:`~docker.client.from_env`. It can also be configured manually by instantiating a :py:class:`~docker.client.DockerClient` class.

.. autofunction:: from_env()

Client reference
----------------

.. autoclass:: DockerClient()

  .. autoattribute:: configs
  .. autoattribute:: containers
  .. autoattribute:: images
  .. autoattribute:: networks
  .. autoattribute:: nodes
  .. autoattribute:: plugins
  .. autoattribute:: secrets
  .. autoattribute:: services
  .. autoattribute:: swarm
  .. autoattribute:: volumes

  .. automethod:: close()
  .. automethod:: df()
  .. automethod:: events()
  .. automethod:: info()
  .. automethod:: login()
  .. automethod:: ping()
  .. automethod:: version()
