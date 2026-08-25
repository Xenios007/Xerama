import pytest

from xerama.pipeline.rate_limiting import (
    ConcurrencyLimitExceededError,
    DuplicateRequestError,
    RateLimitExceededError,
    RateLimiter,
)


def _limiter(**overrides) -> RateLimiter:
    defaults = dict(requests_per_window=2, window_seconds=60.0, max_concurrent_per_project=2)
    defaults.update(overrides)
    return RateLimiter(**defaults)


def test_check_request_rate_allows_up_to_the_window_limit() -> None:
    limiter = _limiter(requests_per_window=2)
    limiter.check_request_rate("P1", now=0.0)
    limiter.check_request_rate("P1", now=1.0)  # does not raise


def test_check_request_rate_rejects_the_request_over_the_limit() -> None:
    limiter = _limiter(requests_per_window=2)
    limiter.check_request_rate("P1", now=0.0)
    limiter.check_request_rate("P1", now=1.0)
    with pytest.raises(RateLimitExceededError):
        limiter.check_request_rate("P1", now=2.0)


def test_check_request_rate_reports_a_useful_retry_after() -> None:
    limiter = _limiter(requests_per_window=1, window_seconds=60.0)
    limiter.check_request_rate("P1", now=0.0)
    with pytest.raises(RateLimitExceededError) as exc_info:
        limiter.check_request_rate("P1", now=10.0)
    assert exc_info.value.retry_after_seconds == pytest.approx(50.0)


def test_check_request_rate_resets_after_the_window_elapses() -> None:
    limiter = _limiter(requests_per_window=1, window_seconds=60.0)
    limiter.check_request_rate("P1", now=0.0)
    with pytest.raises(RateLimitExceededError):
        limiter.check_request_rate("P1", now=30.0)
    limiter.check_request_rate("P1", now=61.0)  # window has fully rolled - does not raise


def test_check_request_rate_is_scoped_per_project() -> None:
    limiter = _limiter(requests_per_window=1)
    limiter.check_request_rate("P1", now=0.0)
    limiter.check_request_rate("P2", now=0.0)  # a different project - does not raise


@pytest.mark.asyncio
async def test_acquire_concurrency_slot_allows_up_to_the_limit() -> None:
    limiter = _limiter(max_concurrent_per_project=2)
    async with limiter.acquire_concurrency_slot("P1"):
        async with limiter.acquire_concurrency_slot("P1"):
            pass  # two concurrent slots granted without raising


@pytest.mark.asyncio
async def test_acquire_concurrency_slot_rejects_over_the_limit() -> None:
    limiter = _limiter(max_concurrent_per_project=1)
    async with limiter.acquire_concurrency_slot("P1"):
        with pytest.raises(ConcurrencyLimitExceededError):
            async with limiter.acquire_concurrency_slot("P1"):
                pass


@pytest.mark.asyncio
async def test_acquire_concurrency_slot_releases_on_exit() -> None:
    limiter = _limiter(max_concurrent_per_project=1)
    async with limiter.acquire_concurrency_slot("P1"):
        pass
    async with limiter.acquire_concurrency_slot("P1"):
        pass  # the first slot was released - does not raise


@pytest.mark.asyncio
async def test_acquire_concurrency_slot_releases_even_if_the_body_raises() -> None:
    limiter = _limiter(max_concurrent_per_project=1)
    with pytest.raises(ValueError):
        async with limiter.acquire_concurrency_slot("P1"):
            raise ValueError("boom")
    async with limiter.acquire_concurrency_slot("P1"):
        pass  # released despite the exception


@pytest.mark.asyncio
async def test_suppress_duplicate_rejects_an_identical_in_flight_key() -> None:
    limiter = _limiter()
    async with limiter.suppress_duplicate("P1:keyframe:SB1"):
        with pytest.raises(DuplicateRequestError):
            async with limiter.suppress_duplicate("P1:keyframe:SB1"):
                pass


@pytest.mark.asyncio
async def test_suppress_duplicate_allows_different_keys_concurrently() -> None:
    limiter = _limiter()
    async with limiter.suppress_duplicate("P1:keyframe:SB1"):
        async with limiter.suppress_duplicate("P1:keyframe:SB2"):
            pass  # different resource - does not raise


@pytest.mark.asyncio
async def test_suppress_duplicate_releases_the_key_on_exit() -> None:
    limiter = _limiter()
    async with limiter.suppress_duplicate("P1:keyframe:SB1"):
        pass
    async with limiter.suppress_duplicate("P1:keyframe:SB1"):
        pass  # the first lock was released - does not raise
