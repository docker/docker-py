Low-level API
=============

The main object-orientated API is built on top of :py:class:`APIClient`. Each method on :py:class:`APIClient` maps one-to-one with a REST API endpoint, and returns the response that the API responds with.

It's possible to use :py:class:`APIClient` directly. Some basic things (e.g. running a container) consist of several API calls and are complex to do with the low-level API, but it's useful if you need extra flexibility and power.

.. py:module:: docker.api

.. autoclass:: docker.api.client.APIClient

Containers
----------

.. py:module:: docker.api.container

.. rst-class:: hide-signature
.. autoclass:: ContainerApiMixin
  :members:
  :undoc-members:

.. py:module:: docker.api.image

Images
------

.. py:module:: docker.api.image

.. rst-class:: hide-signature
.. autoclass:: ImageApiMixin
  :members:
  :undoc-members:

Building images
---------------

.. py:module:: docker.api.build

.. rst-class:: hide-signature
.. autoclass:: BuildApiMixin
  :members:
  :undoc-members:

Networks
--------

.. rst-class:: hide-signature
.. autoclass:: docker.api.network.NetworkApiMixin
  :members:
  :undoc-members:

Utilities
~~~~~~~~~

These functions are available under ``docker.utils`` to create arguments
for :py:meth:`create_network`:

.. autofunction:: docker.utils.create_ipam_config
.. autofunction:: docker.utils.create_ipam_pool

Volumes
-------

.. py:module:: docker.api.volume

.. rst-class:: hide-signature
.. autoclass:: VolumeApiMixin
  :members:
  :undoc-members:

Executing commands in containers
--------------------------------

.. py:module:: docker.api.exec_api

.. rst-class:: hide-signature
.. autoclass:: ExecApiMixin
  :members:
  :undoc-members:

Swarms
------

.. py:module:: docker.api.swarm

.. rst-class:: hide-signature
.. autoclass:: SwarmApiMixin
  :members:
  :undoc-members:

Services
--------

.. py:module:: docker.api.service

.. rst-class:: hide-signature
.. autoclass:: ServiceApiMixin
  :members:
  :undoc-members:

The Docker daemon
-----------------

.. py:module:: docker.api.daemon

.. rst-class:: hide-signature
.. autoclass:: DaemonApiMixin
  :members:
  :undoc-members:
