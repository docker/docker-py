import json

from ..utils import check_resource, minimum_version


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
    def create_network(self, name, driver=None):
        data = {
            'name': name,
            'driver': driver,
        }
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
    def connect_container_to_network(self, container, net_id):
        data = {"container": container}
        url = self._url("/networks/{0}/connect", net_id)
        self._post_json(url, data=data)

    @check_resource
    @minimum_version('1.21')
    def disconnect_container_from_network(self, container, net_id):
        data = {"container": container}
        url = self._url("/networks/{0}/disconnect", net_id)
        self._post_json(url, data=data)
