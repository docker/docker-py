from .. import utils
import logging
log = logging.getLogger(__name__)


class SwarmApiMixin(object):

    def create_swarm_spec(self, *args, **kwargs):
        return utils.SwarmSpec(*args, **kwargs)

    @utils.minimum_version('1.24')
    def init_swarm(self, advertise_addr, listen_addr='0.0.0.0:2377',
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

    @utils.minimum_version('1.24')
    def join_swarm(self, remote_addresses, listen_address=None,
                   secret=None, ca_cert_hash=None, manager=False):
        data = {
            "RemoteAddrs": remote_addresses,
            "ListenAddr": listen_address,
            "Secret": secret,
            "CACertHash": ca_cert_hash,
            "Manager": manager
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
