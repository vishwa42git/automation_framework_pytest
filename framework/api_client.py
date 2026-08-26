from typing import Any

import requests

from framework.config import Settings
from lib.logger import get_logger

logger = get_logger(__name__)


class ApiClient:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.session = requests.Session()

    def request(self, method: str, path: str, **kwargs: Any) -> requests.Response:
        url = f"{self.settings.base_url}/{path.lstrip('/')}"
        kwargs.setdefault("timeout", self.settings.timeout)
        logger.info("Sending %s request to %s", method, url)
        response = self.session.request(method, url, **kwargs)
        logger.info("Received %s response from %s", response.status_code, url)
        response.raise_for_status()
        return response

    def get(self, path: str, **kwargs: Any) -> requests.Response:
        return self.request("GET", path, **kwargs)