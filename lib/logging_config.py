import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_DIRECTORY = Path("logs")
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_HANDLER_NAME = "pytest_automation_file"


def _get_log_file() -> Path:
    configured_log_file = os.getenv("LOG_FILE")
    if configured_log_file:
        return Path(configured_log_file)

    run_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    return DEFAULT_LOG_DIRECTORY / f"test_{run_id}_{os.getpid()}.log"


def configure_logging() -> Path:
    """Configure one rotating file handler for the test run."""
    log_file = _get_log_file()
    if not log_file.is_absolute():
        log_file = Path.cwd() / log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)

    root_logger = logging.getLogger()
    root_logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

    if any(getattr(handler, "name", None) == FILE_HANDLER_NAME for handler in root_logger.handlers):
        return log_file

    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.name = FILE_HANDLER_NAME
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT, DATE_FORMAT))
    root_logger.addHandler(file_handler)
    return log_file