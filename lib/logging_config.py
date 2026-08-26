import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

DEFAULT_LOG_FILE = Path("logs") / "test.log"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_HANDLER_NAME = "pytest_automation_file"


def configure_logging() -> Path:
    """Configure one rotating file handler for the test run."""
    log_file = Path(os.getenv("LOG_FILE", str(DEFAULT_LOG_FILE)))
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