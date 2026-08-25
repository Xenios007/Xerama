"""Rate-limit / concurrency / duplicate-suppression / budget guard for
expensive generation endpoints (MODULE-068).

One helper, `guarded_generation`, wraps the *provider call itself* (not
the whole endpoint - reads, lookups, and prompt compilation ahead of it
are cheap and unmetered) in each of the endpoints that actually spend
provider money: image/video/voice generation (storyboards.py,
video_production.py, audio_production.py) and the LLM-driven pipeline
entry points (generation.py, episodes.py). Standard/local mode's
permissive defaults (`config.py`) mean this never actually throttles
anything in the existing 587-test suite or a single-user deployment;
hosted deployments tighten the same `Settings` fields.
"""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from xerama.config import get_settings
from xerama.pipeline.rate_limiting import (
    ConcurrencyLimitExceededError,
    DuplicateRequestError,
    RateLimitExceededError,
)
from xerama.repositories.sqlalchemy_impl import SQLAlchemyCostRecordRepository
from xerama.services.budget_service import BudgetExceededError, BudgetGuard


@asynccontextmanager
async def guarded_generation(
    request: Request,
    session: AsyncSession,
    project_id: str,
    duplicate_key: str | None = None,
) -> AsyncIterator[None]:
    """Raises before ever reaching the provider: 429 (request-rate or
    concurrency limit, with `Retry-After`), 402 (budget ceiling), or 409
    (an identical request is already in flight, when `duplicate_key` is
    given - e.g. `f"{project_id}:keyframe:{storyboard_id}"`)."""
    rate_limiter = request.app.state.rate_limiter
    settings = get_settings()

    try:
        rate_limiter.check_request_rate(project_id)
    except RateLimitExceededError as exc:
        retry_after = int(exc.retry_after_seconds) + 1
        raise HTTPException(
            status_code=429, detail=str(exc), headers={"Retry-After": str(retry_after)}
        ) from exc

    budget_guard = BudgetGuard(cost_repo=SQLAlchemyCostRecordRepository(session))
    try:
        await budget_guard.check_budget(project_id, settings.project_budget_ceiling_usd)
    except BudgetExceededError as exc:
        raise HTTPException(status_code=402, detail=str(exc)) from exc

    async with AsyncExitStack() as stack:
        try:
            await stack.enter_async_context(rate_limiter.acquire_concurrency_slot(project_id))
        except ConcurrencyLimitExceededError as exc:
            raise HTTPException(
                status_code=429, detail=str(exc), headers={"Retry-After": "1"}
            ) from exc
        if duplicate_key is not None:
            try:
                await stack.enter_async_context(rate_limiter.suppress_duplicate(duplicate_key))
            except DuplicateRequestError as exc:
                raise HTTPException(status_code=409, detail=str(exc)) from exc
        yield
