"""Structured JSON logging.

Every log line is a single JSON object on stdout, which is exactly
what a log shipper (Fluent Bit, Promtail, etc.) expects in production.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone

# Allow-list for `extra=` fields so sensitive data can't accidentally leak
# into logs.
_ALLOWED_EXTRA_FIELDS = (
    "service",
    "target_address",
    "http_status_code",
    "request_id",
    "latency_ms",
    "path",
    "client_ip",
)


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key in _ALLOWED_EXTRA_FIELDS:
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


class JsonLoggerAdapter(logging.LoggerAdapter):
    """LoggerAdapter that merges per-call `extra=` with the adapter's own
    defaults (plain logging.LoggerAdapter drops per-call extras)."""

    def process(self, msg, kwargs):  # type: ignore[override]
        extra = kwargs.get("extra", {})
        kwargs["extra"] = {**self.extra, **extra}
        return msg, kwargs


def configure_logging(service_name: str, level: str = "INFO") -> JsonLoggerAdapter:
    base_logger = logging.getLogger(service_name)
    base_logger.setLevel(level.upper())

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    base_logger.handlers = [handler]
    base_logger.propagate = False

    return JsonLoggerAdapter(base_logger, extra={"service": service_name})
