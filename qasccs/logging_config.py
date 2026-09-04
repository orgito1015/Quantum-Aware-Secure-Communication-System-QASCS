"""Central logging setup for QASCS CLIs.

Production services should never rely on bare print() — it can't be filtered by
level, redirected independently of stdout data, or consumed by log aggregators
in a structured way. This module gives every entry point one consistent,
env-configurable logger.
"""
from __future__ import annotations
import logging
import os
import sys


def configure_logging(name: str) -> logging.Logger:
    """Configure and return a logger for a QASCS entry point.

    Level is controlled by the QASCS_LOG_LEVEL environment variable
    (default: INFO). Logs go to stderr so stdout stays free for any
    machine-readable output (e.g. the risk engine's JSON).
    """
    level_name = os.environ.get("QASCS_LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if not logger.handlers:
        handler = logging.StreamHandler(stream=sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S%z",
            )
        )
        logger.addHandler(handler)
        logger.propagate = False
    return logger
