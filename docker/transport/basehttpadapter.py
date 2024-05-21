import requests.adapters


class BaseHTTPAdapter(requests.adapters.HTTPAdapter):
    def close(self):
        super().close()
        if hasattr(self, 'pools'):
            self.pools.clear()

    # Hotfix for requests 2.32.0: its commit
    # https://github.com/psf/requests/commit/c0813a2d910ea6b4f8438b91d315b8d181302356
    # changes requests.adapters.HTTPAdapter to no longer call get_connection() from
    # send(), but instead call _get_connection().
    def _get_connection(self, request, *args, proxies=None, **kwargs):
        return self.get_connection(request.url, proxies)         
