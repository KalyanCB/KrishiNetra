"""Structured JSON logging (E-00-S07, TDS-013 §5.1)."""

from __future__ import annotations

import json
import logging
import os
from datetime import UTC, datetime
from typing import Any


class JsonLogFormatter(logging.Formatter):
    """Emit one JSON object per log line with trace_id when present."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "trace_id": getattr(record, "trace_id", None),
            "message": record.getMessage(),
            "module": record.module,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    level_name = os.environ.get("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    root = logging.getLogger()
    root.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    root.addHandler(handler)
    root.setLevel(level)
