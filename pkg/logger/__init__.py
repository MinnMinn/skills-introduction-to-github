"""
Reusable structured logger.

Equivalent of pkg/logger/ in the standard Go layout.

Provides a pre-configured ``logging.Logger`` instance that all packages
can import.  Uses JSON-style formatting in production and a human-friendly
format during local development (controlled by the LOG_FORMAT env var).

Usage:
    from pkg.logger import get_logger

    log = get_logger(__name__)
    log.info("server started", extra={"port": 8000})
"""

from __future__ import annotations

import logging
import os
import sys

_LOG_FORMAT_ENV = os.getenv("LOG_FORMAT", "text").lower()


def _build_formatter() -> logging.Formatter:
    if _LOG_FORMAT_ENV == "json":
        # Minimal JSON formatter — swap for ``python-json-logger`` in production.
        return logging.Formatter(
            '{"time":"%(asctime)s","level":"%(levelname)s",'
            '"name":"%(name)s","msg":"%(message)s"}'
        )
    return logging.Formatter(
        fmt="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )


def get_logger(name: str) -> logging.Logger:
    """Return a module-level logger configured for the application.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A ``logging.Logger`` instance with a stream handler attached.
    """
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(_build_formatter())
        logger.addHandler(handler)

    log_level = os.getenv("LOG_LEVEL", "INFO").upper()
    logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger
