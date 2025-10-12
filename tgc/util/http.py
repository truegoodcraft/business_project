from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def http_client(timeout: int = 15) -> Session:
    s = Session()
    retry = Retry(total=3, backoff_factor=0.5, status_forcelist=[429, 500, 502, 503, 504])
    s.mount("https://", HTTPAdapter(max_retries=retry))
    orig = s.request

    def _request(method, url, **kwargs):
        if "timeout" not in kwargs:
            kwargs["timeout"] = timeout
        return orig(method, url, **kwargs)

    s.request = _request
    return s


default_client = http_client()
