import logging
from six.moves import http_client
from .. import types
from .. import utils
log = logging.getLogger(__name__)


class SwarmApiMixin(object):

    def create_swarm_spec(self, *args, **kwargs):
        """
        Create a ``docker.types.SwarmSpec`` instance that can be used as the
        ``swarm_spec`` argument in
        :py:meth:`~docker.api.swarm.SwarmApiMixin.init_swarm`.

        Args:
            task_history_retention_limit (int): Maximum number of tasks
                history stored.
            snapshot_interval (int): Number of logs entries between snapshot.
            keep_old_snapshots (int): Number of snapshots to keep beyond the
                current snapshot.
            log_entries_for_slow_followers (int): Number of log entries to
                keep around to sync up slow followers after a snapshot is
                created.
            heartbeat_tick (int): Amount of ticks (in seconds) between each
                heartbeat.
            election_tick (int): Amount of ticks (in seconds) needed without a
                leader to trigger a new election.
            dispatcher_heartbeat_period (int):  The delay for an agent to send
                a heartbeat to the dispatcher.
            node_cert_expiry (int): Automatic expiry for nodes certificates.
            external_ca (dict): Configuration for forwarding signing requests
                to an external certificate authority. Use
                ``docker.types.SwarmExternalCA``.
            name (string): Swarm's name

        Returns:
            ``docker.types.SwarmSpec`` instance.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.

        Example:

            >>> spec = client.create_swarm_spec(
              snapshot_interval=5000, log_entries_for_slow_followers=1200
            )
            >>> client.init_swarm(
              advertise_addr='eth0', listen_addr='0.0.0.0:5000',
              force_new_cluster=False, swarm_spec=spec
            )
        """
        return types.SwarmSpec(*args, **kwargs)

    @utils.minimum_version('1.24')
    def init_swarm(self, advertise_addr=None, listen_addr='0.0.0.0:2377',
                   force_new_cluster=False, swarm_spec=None):
        """
        Initialize a new Swarm using the current connected engine as the first
        node.

        Args:
            advertise_addr (string): Externally reachable address advertised
                to other nodes. This can either be an address/port combination
                in the form ``192.168.1.1:4567``, or an interface followed by a
                port number, like ``eth0:4567``. If the port number is omitted,
                the port number from the listen address is used. If
                ``advertise_addr`` is not specified, it will be automatically
                detected when possible. Default: None
            listen_addr (string): Listen address used for inter-manager
                communication, as well as determining the networking interface
                used for the VXLAN Tunnel Endpoint (VTEP). This can either be
                an address/port combination in the form ``192.168.1.1:4567``,
                or an interface followed by a port number, like ``eth0:4567``.
                If the port number is omitted, the default swarm listening port
                is used. Default: '0.0.0.0:2377'
            force_new_cluster (bool): Force creating a new Swarm, even if
                already part of one. Default: False
            swarm_spec (dict): Configuration settings of the new Swarm. Use
                ``APIClient.create_swarm_spec`` to generate a valid
                configuration. Default: None

        Returns:
            ``True`` if successful.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """

        url = self._url('/swarm/init')
        if swarm_spec is not None and not isinstance(swarm_spec, dict):
            raise TypeError('swarm_spec must be a dictionary')
        data = {
            'AdvertiseAddr': advertise_addr,
            'ListenAddr': listen_addr,
            'ForceNewCluster': force_new_cluster,
            'Spec': swarm_spec,
        }
        response = self._post_json(url, data=data)
        self._raise_for_status(response)
        return True

    @utils.minimum_version('1.24')
    def inspect_swarm(self):
        """
        Retrieve low-level information about the current swarm.

        Returns:
            A dictionary containing data about the swarm.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        url = self._url('/swarm')
        return self._result(self._get(url), True)

    @utils.check_resource('node_id')
    @utils.minimum_version('1.24')
    def inspect_node(self, node_id):
        """
        Retrieve low-level information about a swarm node

        Args:
            node_id (string): ID of the node to be inspected.

        Returns:
            A dictionary containing data about this node.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        url = self._url('/nodes/{0}', node_id)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.24')
    def join_swarm(self, remote_addrs, join_token, listen_addr=None,
                   advertise_addr=None):
        """
        Make this Engine join a swarm that has already been created.

        Args:
            remote_addrs (:py:class:`list`): Addresses of one or more manager
                nodes already participating in the Swarm to join.
            join_token (string): Secret token for joining this Swarm.
            listen_addr (string): Listen address used for inter-manager
                communication if the node gets promoted to manager, as well as
                determining the networking interface used for the VXLAN Tunnel
                Endpoint (VTEP). Default: ``None``
            advertise_addr (string): Externally reachable address advertised
                to other nodes. This can either be an address/port combination
                in the form ``192.168.1.1:4567``, or an interface followed by a
                port number, like ``eth0:4567``. If the port number is omitted,
                the port number from the listen address is used. If
                AdvertiseAddr is not specified, it will be automatically
                detected when possible. Default: ``None``

        Returns:
            ``True`` if the request went through.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        data = {
            "RemoteAddrs": remote_addrs,
            "ListenAddr": listen_addr,
            "JoinToken": join_token,
            "AdvertiseAddr": advertise_addr,
        }
        url = self._url('/swarm/join')
        response = self._post_json(url, data=data)
        self._raise_for_status(response)
        return True

    @utils.minimum_version('1.24')
    def leave_swarm(self, force=False):
        """
        Leave a swarm.

        Args:
            force (bool): Leave the swarm even if this node is a manager.
                Default: ``False``

        Returns:
            ``True`` if the request went through.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        url = self._url('/swarm/leave')
        response = self._post(url, params={'force': force})
        # Ignore "this node is not part of a swarm" error
        if force and response.status_code == http_client.NOT_ACCEPTABLE:
            return True
        # FIXME: Temporary workaround for 1.13.0-rc bug
        # https://github.com/docker/docker/issues/29192
        if force and response.status_code == http_client.SERVICE_UNAVAILABLE:
            return True
        self._raise_for_status(response)
        return True

    @utils.minimum_version('1.24')
    def nodes(self, filters=None):
        """
        List swarm nodes.

        Args:
            filters (dict): Filters to process on the nodes list. Valid
                filters: ``id``, ``name``, ``membership`` and ``role``.
                Default: ``None``

        Returns:
            A list of dictionaries containing data about each swarm node.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """
        url = self._url('/nodes')
        params = {}
        if filters:
            params['filters'] = utils.convert_filters(filters)

        return self._result(self._get(url, params=params), True)

    @utils.check_resource('node_id')
    @utils.minimum_version('1.24')
    def remove_node(self, node_id, force=False):
        """
        Remove a node from the swarm.

        Args:
            node_id (string): ID of the node to be removed.
            force (bool): Force remove an active node. Default: `False`

        Raises:
            :py:class:`docker.errors.NotFound`
                If the node referenced doesn't exist in the swarm.

            :py:class:`docker.errors.APIError`
                If the server returns an error.
        Returns:
            `True` if the request was successful.
        """
        url = self._url('/nodes/{0}', node_id)
        params = {
            'force': force
        }
        res = self._delete(url, params=params)
        self._raise_for_status(res)
        return True

    @utils.minimum_version('1.24')
    def update_node(self, node_id, version, node_spec=None):
        """
        Update the Node's configuration

        Args:

            node_id (string): ID of the node to be updated.
            version (int): The version number of the node object being
                updated. This is required to avoid conflicting writes.
            node_spec (dict): Configuration settings to update. Any values
                not provided will be removed. Default: ``None``

        Returns:
            `True` if the request went through.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.

        Example:

            >>> node_spec = {'Availability': 'active',
                         'Name': 'node-name',
                         'Role': 'manager',
                         'Labels': {'foo': 'bar'}
                        }
            >>> client.update_node(node_id='24ifsmvkjbyhk', version=8,
                node_spec=node_spec)

        """
        url = self._url('/nodes/{0}/update?version={1}', node_id, str(version))
        res = self._post_json(url, data=node_spec)
        self._raise_for_status(res)
        return True

    @utils.minimum_version('1.24')
    def update_swarm(self, version, swarm_spec=None, rotate_worker_token=False,
                     rotate_manager_token=False):
        """
        Update the Swarm's configuration

        Args:
            version (int): The version number of the swarm object being
                updated. This is required to avoid conflicting writes.
            swarm_spec (dict): Configuration settings to update. Use
                :py:meth:`~docker.api.swarm.SwarmApiMixin.create_swarm_spec` to
                generate a valid configuration. Default: ``None``.
            rotate_worker_token (bool): Rotate the worker join token. Default:
                ``False``.
            rotate_manager_token (bool): Rotate the manager join token.
                Default: ``False``.

        Returns:
            ``True`` if the request went through.

        Raises:
            :py:class:`docker.errors.APIError`
                If the server returns an error.
        """

        url = self._url('/swarm/update')
        response = self._post_json(url, data=swarm_spec, params={
            'rotateWorkerToken': rotate_worker_token,
            'rotateManagerToken': rotate_manager_token,
            'version': version
        })
        self._raise_for_status(response)
        return True
