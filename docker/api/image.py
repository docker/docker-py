import logging
import six
import warnings

from ..auth import auth
from ..constants import INSECURE_REGISTRY_DEPRECATION_WARNING
from .. import utils
from .. import errors

log = logging.getLogger(__name__)


class ImageApiMixin(object):

    @utils.check_resource
    def get_image(self, image):
        res = self._get(self._url("/images/{0}/get", image), stream=True)
        self._raise_for_status(res)
        return res.raw

    @utils.check_resource
    def history(self, image):
        res = self._get(self._url("/images/{0}/history", image))
        return self._result(res, True)

    def images(self, name=None, quiet=False, all=False, viz=False,
               filters=None):
        if viz:
            if utils.compare_version('1.7', self._version) >= 0:
                raise Exception('Viz output is not supported in API >= 1.7!')
            return self._result(self._get(self._url("images/viz")))
        params = {
            'filter': name,
            'only_ids': 1 if quiet else 0,
            'all': 1 if all else 0,
        }
        if filters:
            params['filters'] = utils.convert_filters(filters)
        res = self._result(self._get(self._url("/images/json"), params=params),
                           True)
        if quiet:
            return [x['Id'] for x in res]
        return res

    def import_image(self, src=None, repository=None, tag=None, image=None):
        if src:
            if isinstance(src, six.string_types):
                try:
                    result = self.import_image_from_file(
                        src, repository=repository, tag=tag)
                except IOError:
                    result = self.import_image_from_url(
                        src, repository=repository, tag=tag)
            else:
                result = self.import_image_from_data(
                    src, repository=repository, tag=tag)
        elif image:
            result = self.import_image_from_image(
                image, repository=repository, tag=tag)
        else:
            raise Exception("Must specify a src or image")

        return result

    def import_image_from_data(self, data, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': '-',
            'repo': repository,
            'tag': tag
        }
        headers = {
            'Content-Type': 'application/tar',
        }
        return self._result(
            self._post(u, data=data, params=params, headers=headers))

    def import_image_from_file(self, filename, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': '-',
            'repo': repository,
            'tag': tag
        }
        headers = {
            'Content-Type': 'application/tar',
        }
        with open(filename, 'rb') as f:
            return self._result(
                self._post(u, data=f, params=params, headers=headers,
                           timeout=None))

    def import_image_from_stream(self, stream, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': '-',
            'repo': repository,
            'tag': tag
        }
        headers = {
            'Content-Type': 'application/tar',
            'Transfer-Encoding': 'chunked',
        }
        return self._result(
            self._post(u, data=stream, params=params, headers=headers))

    def import_image_from_url(self, url, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromSrc': url,
            'repo': repository,
            'tag': tag
        }
        return self._result(
            self._post(u, data=None, params=params))

    def import_image_from_image(self, image, repository=None, tag=None):
        u = self._url("/images/create")
        params = {
            'fromImage': image,
            'repo': repository,
            'tag': tag
        }
        return self._result(
            self._post(u, data=None, params=params))

    @utils.check_resource
    def insert(self, image, url, path):
        if utils.compare_version('1.12', self._version) >= 0:
            raise errors.DeprecatedMethod(
                'insert is not available for API version >=1.12'
            )
        api_url = self._url("/images/{0}/insert", image)
        params = {
            'url': url,
            'path': path
        }
        return self._result(self._post(api_url, params=params))

    @utils.check_resource
    def inspect_image(self, image):
        return self._result(
            self._get(self._url("/images/{0}/json", image)), True
        )

    def load_image(self, data):
        res = self._post(self._url("/images/load"), data=data)
        self._raise_for_status(res)

    def pull(self, repository, tag=None, stream=False,
             insecure_registry=False, auth_config=None, decode=False):
        if insecure_registry:
            warnings.warn(
                INSECURE_REGISTRY_DEPRECATION_WARNING.format('pull()'),
                DeprecationWarning
            )

        if not tag:
            repository, tag = utils.parse_repository_tag(repository)
        registry, repo_name = auth.resolve_repository_name(repository)

        params = {
            'tag': tag,
            'fromImage': repository
        }
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if auth_config is None:
                log.debug('Looking for auth config')
                if not self._auth_configs:
                    log.debug(
                        "No auth config in memory - loading from filesystem"
                    )
                    self._auth_configs = auth.load_config()
                authcfg = auth.resolve_authconfig(self._auth_configs, registry)
                # Do not fail here if no authentication exists for this
                # specific registry as we can have a readonly pull. Just
                # put the header if we can.
                if authcfg:
                    log.debug('Found auth config')
                    # auth_config needs to be a dict in the format used by
                    # auth.py username , password, serveraddress, email
                    headers['X-Registry-Auth'] = auth.encode_header(
                        authcfg
                    )
                else:
                    log.debug('No auth config found')
            else:
                log.debug('Sending supplied auth config')
                headers['X-Registry-Auth'] = auth.encode_header(auth_config)

        response = self._post(
            self._url('/images/create'), params=params, headers=headers,
            stream=stream, timeout=None
        )

        self._raise_for_status(response)

        if stream:
            return self._stream_helper(response, decode=decode)

        return self._result(response)

    def push(self, repository, tag=None, stream=False,
             insecure_registry=False, decode=False):
        if insecure_registry:
            warnings.warn(
                INSECURE_REGISTRY_DEPRECATION_WARNING.format('push()'),
                DeprecationWarning
            )

        if not tag:
            repository, tag = utils.parse_repository_tag(repository)
        registry, repo_name = auth.resolve_repository_name(repository)
        u = self._url("/images/{0}/push", repository)
        params = {
            'tag': tag
        }
        headers = {}

        if utils.compare_version('1.5', self._version) >= 0:
            # If we don't have any auth data so far, try reloading the config
            # file one more time in case anything showed up in there.
            if not self._auth_configs:
                self._auth_configs = auth.load_config()
            authcfg = auth.resolve_authconfig(self._auth_configs, registry)

            # Do not fail here if no authentication exists for this specific
            # registry as we can have a readonly pull. Just put the header if
            # we can.
            if authcfg:
                headers['X-Registry-Auth'] = auth.encode_header(authcfg)

        response = self._post_json(
            u, None, headers=headers, stream=stream, params=params
        )

        self._raise_for_status(response)

        if stream:
            return self._stream_helper(response, decode=decode)

        return self._result(response)

    @utils.check_resource
    def remove_image(self, image, force=False, noprune=False):
        params = {'force': force, 'noprune': noprune}
        res = self._delete(self._url("/images/{0}", image), params=params)
        self._raise_for_status(res)

    def search(self, term):
        return self._result(
            self._get(self._url("/images/search"), params={'term': term}),
            True
        )

    @utils.check_resource
    def tag(self, image, repository, tag=None, force=False):
        params = {
            'tag': tag,
            'repo': repository,
            'force': 1 if force else 0
        }
        url = self._url("/images/{0}/tag", image)
        res = self._post(url, params=params)
        self._raise_for_status(res)
        return res.status_code == 201
