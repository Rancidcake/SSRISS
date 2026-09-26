"""
Central logging setup. Every module logs through the "monitor" logger so the
format, level and destinations are decided in exactly one place.

Log lines are key=value so they can be grepped (e.g. `grep "stage=fetch"`).
"""

import logging
import os
from typing import Optional

LOGGER_NAME = "monitor"
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(message)s"


def setup_logging(level: str = "INFO", log_file: Optional[str] = None) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level.upper())
    logger.handlers.clear()
    logger.propagate = False

    formatter = logging.Formatter(LOG_FORMAT)

    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    if log_file:
        os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger() -> logging.Logger:
    return logging.getLogger(LOGGER_NAME)
