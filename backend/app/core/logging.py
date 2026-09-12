"""Minimal JSON logging without user payloads or secrets."""

import json
import logging
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_context: ContextVar[str] = ContextVar("request_id", default="-")

_STRUCTURED_FIELDS = (
    "event",
    "request_id",
    "method",
    "path",
    "status_code",
    "duration_ms",
    "user_id",
    "exception_type",
    "response_completed",
)


class JsonFormatter(logging.Formatter):
    """Render a conservative, machine-readable log record."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", request_id_context.get()),
        }
        for field in _STRUCTURED_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_logging(level: str) -> None:
    """Configure exactly one project JSON handler while preserving test handlers."""

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    project_handler = next(
        (
            handler
            for handler in root_logger.handlers
            if getattr(handler, "_legalmind_json_handler", False)
        ),
        None,
    )
    if project_handler is None:
        project_handler = logging.StreamHandler()
        project_handler._legalmind_json_handler = True  # type: ignore[attr-defined]
        root_logger.addHandler(project_handler)

    project_handler.setLevel(level)
    project_handler.setFormatter(JsonFormatter())

    # These libraries log full request URLs at INFO. URLs may contain case or
    # user identifiers, so route access logging is owned by our safe middleware.
    for noisy_logger in (
        "httpx",
        "httpcore",
        "uvicorn.access",
        "sqlalchemy.engine",
        "sqlalchemy.pool",
    ):
        logging.getLogger(noisy_logger).setLevel(logging.WARNING)
