Low-level API
=============

The main object-orientated API is built on top of :py:class:`APIClient`. Each method on :py:class:`APIClient` maps one-to-one with a REST API endpoint, and returns the response that the API responds with.

It's possible to use :py:class:`APIClient` directly. Some basic things (e.g. running a container) consist of several API calls and are complex to do with the low-level API, but it's useful if you need extra flexibility and power.

.. py:module:: docker.api

.. autoclass:: docker.api.client.APIClient

Configs
-------

.. py:module:: docker.api.config

.. rst-class:: hide-signature
.. autoclass:: ConfigApiMixin
  :members:
  :undoc-members:

Containers
----------

.. py:module:: docker.api.container

.. rst-class:: hide-signature
.. autoclass:: ContainerApiMixin
  :members:
  :undoc-members:

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

Plugins
-------

.. py:module:: docker.api.plugin

.. rst-class:: hide-signature
.. autoclass:: PluginApiMixin
  :members:
  :undoc-members:

Secrets
-------

.. py:module:: docker.api.secret

.. rst-class:: hide-signature
.. autoclass:: SecretApiMixin
  :members:
  :undoc-members:

The Docker daemon
-----------------

.. py:module:: docker.api.daemon

.. rst-class:: hide-signature
.. autoclass:: DaemonApiMixin
  :members:
  :undoc-members:

Configuration types
-------------------

.. py:module:: docker.types

.. autoclass:: ConfigReference
.. autoclass:: ContainerSpec
.. autoclass:: DNSConfig
.. autoclass:: DriverConfig
.. autoclass:: EndpointSpec
.. autoclass:: Healthcheck
.. autoclass:: IPAMConfig
.. autoclass:: IPAMPool
.. autoclass:: LogConfig
.. autoclass:: Mount
.. autoclass:: NetworkAttachmentConfig
.. autoclass:: Placement
.. autoclass:: PlacementPreference
.. autoclass:: Privileges
.. autoclass:: Resources
.. autoclass:: RestartPolicy
.. autoclass:: RollbackConfig
.. autoclass:: SecretReference
.. autoclass:: ServiceMode
.. autoclass:: SwarmExternalCA
.. autoclass:: SwarmSpec(*args, **kwargs)
.. autoclass:: TaskTemplate
.. autoclass:: Ulimit
.. autoclass:: UpdateConfig
