"""Correlation-ID request middleware (MODULE-050) + the unhandled-
exception catch-all (MODULE-070 "error surfaces").

Every request gets a correlation ID (from an incoming `X-Correlation-ID`
header, or a freshly generated one) bound for the duration of the
request - every log line emitted while handling it, including inside
pipeline/provider code several calls deep, carries the same ID without
threading it through every function signature.

The unhandled-exception logging/response lives *here*, not as a
`@app.exception_handler(Exception)` registration in `app.py` - Starlette
has a documented limitation where a `BaseHTTPMiddleware`-based
middleware ahead of the router (this one, registered via
`app.middleware("http")`) intercepts the exception via its own
`call_next` before a generic exception handler ever gets a chance to
run, so that handler silently never fires. Catching it in this
middleware's own try/except is the interception point that actually
works with this middleware stack - verified by
`tests/test_error_handling.py`.
"""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from xerama.observability.logging import new_correlation_id, reset_correlation_id, set_correlation_id

CORRELATION_ID_HEADER = "X-Correlation-ID"

_logger = logging.getLogger("xerama.api")


async def correlation_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    correlation_id = request.headers.get(CORRELATION_ID_HEADER) or new_correlation_id()
    token = set_correlation_id(correlation_id)
    try:
        try:
            response = await call_next(request)
        except Exception:
            # An unhandled exception must never leak internals to the
            # client (a generic body regardless of what actually broke)
            # and must never go unlogged (structured, correlation-ID-
            # tagged - the gap this closes).
            _logger.exception(
                "unhandled exception", extra={"path": request.url.path, "method": request.method}
            )
            response = JSONResponse(status_code=500, content={"detail": "internal server error"})
    finally:
        reset_correlation_id(token)
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    return response
