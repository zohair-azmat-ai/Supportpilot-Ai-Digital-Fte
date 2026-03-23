"""Centralised logging configuration for SupportPilot."""

from __future__ import annotations

import logging
import sys
from typing import Optional


_LOG_FORMAT = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"

_configured = False


def _configure_root_logger() -> None:
    """Configure the root logger once."""
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(fmt=_LOG_FORMAT, datefmt=_DATE_FORMAT))

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    # Avoid duplicate handlers if called more than once (e.g., in tests)
    if not root.handlers:
        root.addHandler(handler)

    # Reduce noise from third-party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """Return a configured logger for the given module name.

    Usage::

        from app.utils.logging import get_logger
        logger = get_logger(__name__)
    """
    _configure_root_logger()
    return logging.getLogger(name)


# Convenience module-level logger
logger = get_logger(__name__)
