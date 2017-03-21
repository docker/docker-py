Plugins
=======

.. py:module:: docker.models.plugins

Manage plugins on the server.

Methods available on ``client.plugins``:

.. rst-class:: hide-signature
.. py:class:: PluginCollection

  .. automethod:: get
  .. automethod:: install
  .. automethod:: list


Plugin objects
--------------

.. autoclass:: Plugin()

  .. autoattribute:: id
  .. autoattribute:: short_id
  .. autoattribute:: name
  .. autoattribute:: enabled
  .. autoattribute:: settings
  .. py:attribute:: attrs

    The raw representation of this object from the server.

  .. automethod:: configure
  .. automethod:: disable
  .. automethod:: enable
  .. automethod:: reload
  .. automethod:: push
  .. automethod:: remove
  .. automethod:: upgrade
