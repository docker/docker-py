Docker SDK for Python
=====================

A Python library for the Docker Engine API. It lets you do anything the ``docker`` command does, but from within Python apps – run containers, manage containers, manage Swarms, etc.

For more information about the Engine API, `see its documentation <https://docs.docker.com/engine/reference/api/docker_remote_api/>`_.

Installation
------------

The latest stable version `is available on PyPI <https://pypi.python.org/pypi/docker/>`_. Either add ``docker`` to your ``requirements.txt`` file or install with pip::

    pip install docker

Getting started
---------------

To talk to a Docker daemon, you first need to instantiate a client. You can use :py:func:`~docker.client.from_env` to connect using the default socket or the configuration in your environment:

.. code-block:: python

  import docker
  client = docker.from_env()

You can now run containers:

.. code-block:: python

  >>> client.containers.run("ubuntu", "echo hello world")
  'hello world\n'

You can run containers in the background:

.. code-block:: python

  >>> client.containers.run("bfirsh/reticulate-splines", detach=True)
  <Container '45e6d2de7c54'>

You can manage containers:

.. code-block:: python

  >>> client.containers.list()
  [<Container '45e6d2de7c54'>, <Container 'db18e4f20eaa'>, ...]

  >>> container = client.containers.get('45e6d2de7c54')

  >>> container.attrs['Config']['Image']
  "bfirsh/reticulate-splines"

  >>> container.logs()
  "Reticulating spline 1...\n"

  >>> container.stop()

You can stream logs:

.. code-block:: python

  >>> for line in container.logs(stream=True):
  ...   print(line.strip())
  Reticulating spline 2...
  Reticulating spline 3...
  ...

You can manage images:

.. code-block:: python

  >>> client.images.pull('nginx')
  <Image 'nginx'>

  >>> client.images.list()
  [<Image 'ubuntu'>, <Image 'nginx'>, ...]

That's just a taste of what you can do with the Docker SDK for Python. For more, :doc:`take a look at the reference <client>`.

.. toctree::
  :hidden:
  :maxdepth: 2

  client
  configs
  containers
  images
  networks
  nodes
  plugins
  secrets
  services
  swarm
  volumes
  api
  tls
  user_guides/index
  change-log
