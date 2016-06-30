from .. import utils
import logging
log = logging.getLogger(__name__)


class SwarmApiMixin(object):
    @utils.minimum_version('1.24')
    def swarm(self):
        url = self._url('/swarm')
        return self._result(self._get(url), True)

    @utils.minimum_version('1.24')
    def swarm_init(self, listen_addr, force_new_cluster=False,
                   swarm_opts=None):
        url = self._url('/swarm/init')
        if swarm_opts is not None and not isinstance(swarm_opts, dict):
            raise TypeError('swarm_opts must be a dictionary')
        data = {
            'ListenAddr': listen_addr,
            'ForceNewCluster': force_new_cluster,
            'Spec': swarm_opts
        }
        return self._result(self._post_json(url, data=data), True)

    @utils.minimum_version('1.24')
    def swarm_join(self, remote_address, listen_address=None,
                   secret=None, ca_cert_hash=None, manager=False):
        data = {
            "RemoteAddr": remote_address,
            "ListenAddr": listen_address,
            "Secret": secret,
            "CACertHash": ca_cert_hash,
            "Manager": manager
        }
        url = self._url('/swarm/join', )
        return self._result(self._post_json(url, data=data), True)

    @utils.minimum_version('1.24')
    def swarm_leave(self):
        url = self._url('/swarm/leave')
        return self._result(self._post(url))
