from .. import utils
import logging
log = logging.getLogger(__name__)


class SwarmApiMixin(object):

    def create_swarm_spec(self, *args, **kwargs):
        return utils.SwarmSpec(*args, **kwargs)

    @utils.minimum_version('1.24')
    def init_swarm(self, advertise_addr=None, listen_addr='0.0.0.0:2377',
                   force_new_cluster=False, swarm_spec=None):
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
        url = self._url('/swarm')
        return self._result(self._get(url), True)

    @utils.check_resource
    @utils.minimum_version('1.24')
    def inspect_node(self, node_id):
        url = self._url('/nodes/{0}', node_id)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.24')
    def join_swarm(self, remote_addrs, join_token, listen_addr=None,
                   advertise_addr=None):
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
        url = self._url('/swarm/leave')
        response = self._post(url, params={'force': force})
        self._raise_for_status(response)
        return True

    @utils.minimum_version('1.24')
    def nodes(self, filters=None):
        url = self._url('/nodes')
        params = {}
        if filters:
            params['filters'] = utils.convert_filters(filters)

        return self._result(self._get(url, params=params), True)

    @utils.minimum_version('1.24')
    def update_swarm(self, version, swarm_spec=None, rotate_worker_token=False,
                     rotate_manager_token=False):
        url = self._url('/swarm/update')
        response = self._post_json(url, data=swarm_spec, params={
            'rotateWorkerToken': rotate_worker_token,
            'rotateManagerToken': rotate_manager_token,
            'version': version
        })
        self._raise_for_status(response)
        return True
