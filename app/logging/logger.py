"""
Structured logging configuration.

Emits JSON lines in production (easy to ship to ELK / CloudWatch / etc.)
and human-readable colored lines in development.
"""
from __future__ import annotations

import logging
import sys
import time
from typing import Any

from app.config.settings import get_settings

try:
    import orjson

    def _dumps(obj: dict[str, Any]) -> str:
        return orjson.dumps(obj).decode()
except ImportError:  # pragma: no cover
    import json

    def _dumps(obj: dict[str, Any]) -> str:
        return json.dumps(obj, default=str)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        extra = getattr(record, "extra_fields", None)
        if extra:
            payload.update(extra)
        return _dumps(payload)


def configure_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.setLevel(settings.LOG_LEVEL)

    handler = logging.StreamHandler(sys.stdout)
    if settings.LOG_JSON:
        handler.setFormatter(JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-8s | %(name)s | %(message)s")
        )

    root.handlers = [handler]

    # Quiet down noisy third-party loggers.
    for noisy in ("uvicorn.access", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


def log_event(logger: logging.Logger, level: int, message: str, **fields: Any) -> None:
    """Log with structured extra fields, e.g. log_event(log, INFO, 'upload', brochure_id=1)."""
    logger.log(level, message, extra={"extra_fields": fields})
