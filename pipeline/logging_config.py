"""Configure pipeline console and rotating file logs."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging():
    """Configure timestamped INFO logs for console and file output."""
    log_path = Path(__file__).resolve().parents[1] / "logs" / "pipeline.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logging.basicConfig(
        level=logging.INFO,
        handlers=(console_handler, file_handler),
        force=True,
    )
