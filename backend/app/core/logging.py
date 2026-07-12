"""F4.1 (MI-21): JSON structured logging with request_id correlation, so
logs from a single request can be grepped/joined across every module that
logs during it (repositories, services, engines) without passing a logger
argument through every call. The request_id itself is set by
RequestIDMiddleware (app/core/middleware.py) at the start of each request."""
from __future__ import annotations

import contextvars
import json
import logging
import sys

request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "timestamp": self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


def configure_logging(log_level: str) -> None:
    """Replaces the root logger's handlers with a single stdout JSON
    handler. Called once at app startup (app/main.py) -- never per-request."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(log_level)
