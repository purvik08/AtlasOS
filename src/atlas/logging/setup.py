"""Logging configuration for Atlas OS.

Provides a single ``configure_logging`` entry point so every subsystem gets
consistent formatting, and to avoid the common bug of accumulating duplicate
handlers when logging is configured more than once (e.g. once in tests, once
at application startup).
"""

from __future__ import annotations

import json
import logging
import sys
import time
from typing import Any

_CONFIGURED_MARKER = "_atlas_configured"

_STANDARD_LOG_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "taskName",
    "message",
}


class _JsonFormatter(logging.Formatter):
    """Renders log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": time.strftime(
                "%Y-%m-%dT%H:%M:%S", time.localtime(record.created)
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        extras = {
            key: value
            for key, value in record.__dict__.items()
            if key not in _STANDARD_LOG_RECORD_FIELDS and not key.startswith("_")
        }
        if extras:
            payload["extra"] = extras

        return json.dumps(payload, default=str)


def configure_logging(level: str = "INFO", *, json_format: bool = False) -> None:
    """Configure the root logger. Idempotent: safe to call multiple times.

    Args:
        level: Logging level name, e.g. ``"DEBUG"``, ``"INFO"``, ``"WARNING"``.
        json_format: If ``True``, emit structured JSON lines instead of
            human-readable text. Useful when logs are shipped to a collector.
    """

    root = logging.getLogger()

    if getattr(root, _CONFIGURED_MARKER, False):
        root.setLevel(level.upper())
        return

    handler = logging.StreamHandler(stream=sys.stdout)
    if json_format:
        handler.setFormatter(_JsonFormatter())
    else:
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())
    setattr(root, _CONFIGURED_MARKER, True)
