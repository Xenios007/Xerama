"""Correlation-ID request middleware (MODULE-050).

Every request gets a correlation ID (from an incoming `X-Correlation-ID`
header, or a freshly generated one) bound for the duration of the
request - every log line emitted while handling it, including inside
pipeline/provider code several calls deep, carries the same ID without
threading it through every function signature.
"""

from collections.abc import Awaitable, Callable

from fastapi import Request, Response

from xerama.observability.logging import new_correlation_id, reset_correlation_id, set_correlation_id

CORRELATION_ID_HEADER = "X-Correlation-ID"


async def correlation_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    correlation_id = request.headers.get(CORRELATION_ID_HEADER) or new_correlation_id()
    token = set_correlation_id(correlation_id)
    try:
        response = await call_next(request)
    finally:
        reset_correlation_id(token)
    response.headers[CORRELATION_ID_HEADER] = correlation_id
    return response
