from typing import Any, Dict, Iterable, List, Optional, Union

import requests

from ..constants import DEFAULT_DOCKER_API_VERSION, DEFAULT_TIMEOUT_SECONDS

class BaseMixin(object):
    base_url: str = ''
    credstore_env: Optional[Dict[str, str]] = None
    timeout: int = DEFAULT_TIMEOUT_SECONDS
    _auth_configs: Dict[str, Dict]
    _general_configs: Dict[str, Dict]
    _version: str = DEFAULT_DOCKER_API_VERSION

    def _url(self, pathfmt: str, *args, **kwargs) -> str:
        raise NotImplemented

    def _post(self, url: str, **kwargs) -> requests.Response:
        raise NotImplemented

    def _get(self, url: str, **kwargs) -> requests.Response:
        raise NotImplemented

    def _put(self, url: str, **kwargs) -> requests.Response:
        raise NotImplemented

    def _delete(self, url: str, **kwargs) -> requests.Response:
        raise NotImplemented

    def _post_json(self, url: str, data: Optional[Union[Dict[str, Any], List[Any]]], **kwargs) -> requests.Response:
        raise NotImplemented

    def _raise_for_status(self, response: requests.Response) -> None:
        raise NotImplemented

    def _result(self, response: requests.Response, json: bool=False, binary: bool=False) -> Any:
        raise NotImplemented

    def _stream_helper(self, response: requests.Response, decode: bool = False) -> Iterable:
        raise NotImplemented

    def _get_raw_response_socket(self, response: requests.Response) -> Iterable:
        raise NotImplemented

    def _read_from_socket(
            self,
            response: requests.Response,
            stream: bool,
            tty: bool = False) -> Union[Iterable[bytes], bytes]:
        raise NotImplemented

    def _stream_raw_result(
            self,
            response: requests.Response,
            chunk_size: int = 1,
            decode: bool = True) -> Iterable[bytes]:
        raise NotImplemented
