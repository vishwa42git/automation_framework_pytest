import pytest

from framework.api_client import ApiClient
from framework.config import Settings
from lib.logging_config import configure_logging


def pytest_configure(config: pytest.Config) -> None:
	configure_logging()


@pytest.fixture(scope="session")
def settings() -> Settings:
	"""Load shared test settings once for the test session."""
	return Settings.from_environment()


@pytest.fixture
def api_client(settings: Settings) -> ApiClient:
	"""Provide a fresh API client for each test."""
	return ApiClient(settings)
