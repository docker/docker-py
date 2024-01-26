import requests.adapters


class BaseHTTPAdapter(requests.adapters.HTTPAdapter):
    def close(self) -> None:
        super().close()
        if hasattr(self, 'pools'):
            self.pools.clear()
