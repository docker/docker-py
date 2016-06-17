import json

from ..errors import InvalidVersion
from ..utils import check_resource, minimum_version
from ..utils import version_lt


class NetworkApiMixin(object):
    @minimum_version('1.21')
    def networks(self, names=None, ids=None):
        filters = {}
        if names:
            filters['name'] = names
        if ids:
            filters['id'] = ids

        params = {'filters': json.dumps(filters)}

        url = self._url("/networks")
        res = self._get(url, params=params)
        return self._result(res, json=True)

    @minimum_version('1.21')
    def create_network(self, name, driver=None, options=None, ipam=None,
                       check_duplicate=None, internal=False):
        if options is not None and not isinstance(options, dict):
            raise TypeError('options must be a dictionary')

        data = {
            'Name': name,
            'Driver': driver,
            'Options': options,
            'IPAM': ipam,
            'CheckDuplicate': check_duplicate
        }

        if internal:
            if version_lt(self._version, '1.22'):
                raise InvalidVersion('Internal networks are not '
                                     'supported in API version < 1.22')
            data['Internal'] = True

        url = self._url("/networks/create")
        res = self._post_json(url, data=data)
        return self._result(res, json=True)

    @minimum_version('1.21')
    def remove_network(self, net_id):
        url = self._url("/networks/{0}", net_id)
        res = self._delete(url)
        self._raise_for_status(res)

    @minimum_version('1.21')
    def inspect_network(self, net_id):
        url = self._url("/networks/{0}", net_id)
        res = self._get(url)
        return self._result(res, json=True)

    @check_resource
    @minimum_version('1.21')
    def connect_container_to_network(self, container, net_id,
                                     ipv4_address=None, ipv6_address=None,
                                     aliases=None, links=None):
        data = {
            "Container": container,
            "EndpointConfig": self.create_endpoint_config(
                aliases=aliases, links=links, ipv4_address=ipv4_address,
                ipv6_address=ipv6_address
            ),
        }

        url = self._url("/networks/{0}/connect", net_id)
        res = self._post_json(url, data=data)
        self._raise_for_status(res)

    @check_resource
    @minimum_version('1.21')
    def disconnect_container_from_network(self, container, net_id):
        data = {"container": container}
        url = self._url("/networks/{0}/disconnect", net_id)
        res = self._post_json(url, data=data)
        self._raise_for_status(res)
