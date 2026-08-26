import logging


def get_logger(name: str) -> logging.Logger:
    """Return a named logger that uses the project's logging configuration."""
    return logging.getLogger(name)