"""Application-wide logging configuration."""

from __future__ import annotations

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGING_INITIALIZED = False


def setup_logging() -> None:
    """Configure root logging once for console + file output."""

    global _LOGGING_INITIALIZED
    if _LOGGING_INITIALIZED:
        return

    log_dir = Path(__file__).resolve().parents[1] / "data" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / "moviebot.log"

    level_name = (os.getenv("LOG_LEVEL") or "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)

    handlers = [
        logging.StreamHandler(),
        RotatingFileHandler(
            filename=log_path,
            maxBytes=2 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
    ]

    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        handlers=handlers,
    )
    _LOGGING_INITIALIZED = True
