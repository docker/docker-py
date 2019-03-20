import requests.adapters


class BaseHTTPAdapter(requests.adapters.HTTPAdapter):
    def close(self):
        super(BaseHTTPAdapter, self).close()
        if hasattr(self, 'pools'):
            self.pools.clear()
