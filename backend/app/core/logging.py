"""
Structured logging configuration for MicroGridX backend.

Produces JSON-formatted log records so logs can be aggregated and queried
in downstream observability tooling. Kept dependency-free (uses the
standard library `logging` module only).
"""
import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        # Allow callers to attach structured context via `extra={"context": {...}}`
        context = getattr(record, "context", None)
        if context:
            payload["context"] = context

        return json.dumps(payload)


def configure_logging(log_level: str = "INFO") -> None:
    """Configure root logging handlers. Safe to call once at startup."""
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level.upper())

    # Avoid duplicate handlers if configure_logging is called more than once
    # (e.g. during tests).
    root_logger.handlers.clear()

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    root_logger.addHandler(handler)

    # Keep third-party loggers reasonably quiet by default.
    logging.getLogger("uvicorn.access").setLevel(log_level.upper())


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
