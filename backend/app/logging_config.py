import logging
import os
from logging.handlers import RotatingFileHandler

from .config import settings


def _ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)


def configure_logging(service_name: str) -> None:
    _ensure_dir(settings.log_dir)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    fmt = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S%z",
    )

    file_path = os.path.join(settings.log_dir, f"{service_name}.log")
    file_handler = RotatingFileHandler(file_path, maxBytes=10_000_000, backupCount=5)
    file_handler.setFormatter(fmt)
    file_handler.setLevel(logging.INFO)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(fmt)
    stream_handler.setLevel(logging.INFO)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
