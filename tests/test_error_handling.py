"""MODULE-070 - unhandled exceptions must never leak internals and must
always be logged with correlation-ID context."""

import io
import json
import logging

import httpx
import pytest

from xerama.api.app import create_app


@pytest.fixture
async def client():
    app = create_app()

    @app.get("/__boom")
    async def boom() -> None:
        raise RuntimeError("something went genuinely wrong")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_unhandled_exception_returns_a_clean_500(client: httpx.AsyncClient) -> None:
    response = await client.get("/__boom")
    assert response.status_code == 500
    assert response.json() == {"detail": "internal server error"}


@pytest.mark.asyncio
async def test_unhandled_exception_does_not_leak_the_traceback_or_message(
    client: httpx.AsyncClient,
) -> None:
    response = await client.get("/__boom")
    assert "something went genuinely wrong" not in response.text
    assert "Traceback" not in response.text
    assert "RuntimeError" not in response.text


@pytest.mark.asyncio
async def test_unhandled_exception_is_logged_with_correlation_id(client: httpx.AsyncClient) -> None:
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    from xerama.observability.logging import CorrelationIdFilter, JsonLogFormatter

    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(CorrelationIdFilter())
    logger = logging.getLogger("xerama.api")
    logger.handlers = [handler]
    logger.propagate = False
    logger.setLevel(logging.ERROR)

    response = await client.get("/__boom", headers={"X-Correlation-ID": "test-correlation-id"})
    assert response.status_code == 500

    logged = json.loads(stream.getvalue().strip().splitlines()[-1])
    assert logged["correlation_id"] == "test-correlation-id"
    assert logged["path"] == "/__boom"
    assert "exception" in logged
