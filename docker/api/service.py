from .. import errors
from .. import utils
from ..auth import auth


class ServiceApiMixin(object):
    @utils.minimum_version('1.24')
    def create_service(
            self, task_template, name=None, labels=None, mode=None,
            update_config=None, networks=None, endpoint_config=None
    ):
        url = self._url('/services/create')
        headers = {}
        image = task_template.get('ContainerSpec', {}).get('Image', None)
        if image is None:
            raise errors.DockerException(
                'Missing mandatory Image key in ContainerSpec'
            )
        registry, repo_name = auth.resolve_repository_name(image)
        auth_header = auth.get_config_header(self, registry)
        if auth_header:
            headers['X-Registry-Auth'] = auth_header
        data = {
            'Name': name,
            'Labels': labels,
            'TaskTemplate': task_template,
            'Mode': mode,
            'UpdateConfig': update_config,
            'Networks': networks,
            'Endpoint': endpoint_config
        }
        return self._result(
            self._post_json(url, data=data, headers=headers), True
        )

    @utils.minimum_version('1.24')
    @utils.check_resource
    def inspect_service(self, service):
        url = self._url('/services/{0}', service)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.24')
    @utils.check_resource
    def inspect_task(self, task):
        url = self._url('/tasks/{0}', task)
        return self._result(self._get(url), True)

    @utils.minimum_version('1.24')
    @utils.check_resource
    def remove_service(self, service):
        url = self._url('/services/{0}', service)
        resp = self._delete(url)
        self._raise_for_status(resp)
        return True

    @utils.minimum_version('1.24')
    def services(self, filters=None):
        params = {
            'filters': utils.convert_filters(filters) if filters else None
        }
        url = self._url('/services')
        return self._result(self._get(url, params=params), True)

    @utils.minimum_version('1.24')
    def tasks(self, filters=None):
        params = {
            'filters': utils.convert_filters(filters) if filters else None
        }
        url = self._url('/tasks')
        return self._result(self._get(url, params=params), True)

    @utils.minimum_version('1.24')
    @utils.check_resource
    def update_service(self, service, version, task_template=None, name=None,
                       labels=None, mode=None, update_config=None,
                       networks=None, endpoint_config=None):
        url = self._url('/services/{0}/update', service)
        data = {}
        headers = {}
        if name is not None:
            data['Name'] = name
        if labels is not None:
            data['Labels'] = labels
        if mode is not None:
            data['Mode'] = mode
        if task_template is not None:
            image = task_template.get('ContainerSpec', {}).get('Image', None)
            if image is not None:
                registry, repo_name = auth.resolve_repository_name(image)
                auth_header = auth.get_config_header(self, registry)
                if auth_header:
                    headers['X-Registry-Auth'] = auth_header
            data['TaskTemplate'] = task_template
        if update_config is not None:
            data['UpdateConfig'] = update_config
        if networks is not None:
            data['Networks'] = networks
        if endpoint_config is not None:
            data['Endpoint'] = endpoint_config

        resp = self._post_json(
            url, data=data, params={'version': version}, headers=headers
        )
        self._raise_for_status(resp)
        return True
