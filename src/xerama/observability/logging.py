"""Structured logging + correlation IDs (MODULE-050).

"An operator can determine where and why a production is stuck" starts
with every log line during one request/job carrying the same correlation
ID, and being machine-parseable JSON rather than free text. Deliberately
never logs prompt/payload content or secrets - only the fixed structured
fields below - "do not expose secrets or full private prompts by
default" is satisfied by the formatter's field set, not a redaction pass
over free-form text.
"""

import contextvars
import json
import logging
import uuid
from datetime import datetime, timezone

_correlation_id: contextvars.ContextVar[str] = contextvars.ContextVar("correlation_id", default="-")

# Standard `logging.LogRecord` attributes - anything else on a record is
# caller-supplied via `extra={...}` and safe to surface as structured
# context (the caller controls what it passes, same trust boundary as
# every %-style log call already in this codebase).
_STANDARD_RECORD_ATTRS = frozenset(logging.makeLogRecord({}).__dict__.keys()) | {"message", "asctime"}


def new_correlation_id() -> str:
    return uuid.uuid4().hex


def set_correlation_id(correlation_id: str) -> contextvars.Token:
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: contextvars.Token) -> None:
    _correlation_id.reset(token)


def get_correlation_id() -> str:
    return _correlation_id.get()


class CorrelationIdFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = get_correlation_id()
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", "-"),
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_ATTRS and key != "correlation_id":
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_structured_logging(level: str = "INFO") -> None:
    root = logging.getLogger()
    root.setLevel(level)
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(CorrelationIdFilter())
    root.handlers = [handler]
