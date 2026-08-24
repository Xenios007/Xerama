import httpx
import pytest
import respx

from xerama.domain.enums import ProviderErrorKind
from xerama.providers.errors import ProviderError
from xerama.providers.llm import LLMMessage, LLMRequest
from xerama.providers.openrouter import OpenRouterProvider


def _request() -> LLMRequest:
    return LLMRequest(
        model="test/model:free",
        messages=[LLMMessage(role="user", content="hello")],
        response_schema={"type": "object"},
    )


@pytest.mark.asyncio
async def test_complete_parses_successful_response() -> None:
    async with httpx.AsyncClient() as client:
        provider = OpenRouterProvider(api_key="sk-test", http_client=client)
        with respx.mock(assert_all_called=True) as mock:
            mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
                return_value=httpx.Response(
                    200,
                    json={
                        "model": "test/model:free",
                        "choices": [
                            {
                                "message": {"content": '{"ok": true}'},
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 12, "completion_tokens": 4},
                    },
                )
            )
            response = await provider.complete(_request())

    assert response.content == '{"ok": true}'
    assert response.prompt_tokens == 12
    assert response.completion_tokens == 4
    assert response.finish_reason == "stop"


@pytest.mark.asyncio
async def test_complete_never_sends_request_without_api_key() -> None:
    async with httpx.AsyncClient() as client:
        provider = OpenRouterProvider(api_key="", http_client=client)
        with respx.mock(assert_all_called=False) as mock:
            route = mock.post("https://openrouter.ai/api/v1/chat/completions")
            with pytest.raises(ProviderError) as exc_info:
                await provider.complete(_request())
            assert not route.called
    assert exc_info.value.kind == ProviderErrorKind.AUTHENTICATION


@pytest.mark.asyncio
async def test_complete_maps_rate_limit_status_and_is_retriable() -> None:
    async with httpx.AsyncClient() as client:
        provider = OpenRouterProvider(api_key="sk-test", http_client=client)
        with respx.mock(assert_all_called=True) as mock:
            mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
                return_value=httpx.Response(429, json={"error": {"message": "slow down"}})
            )
            with pytest.raises(ProviderError) as exc_info:
                await provider.complete(_request())

    assert exc_info.value.kind == ProviderErrorKind.RATE_LIMIT
    assert exc_info.value.retriable is True
    assert "slow down" in exc_info.value.message


@pytest.mark.asyncio
async def test_complete_maps_auth_error_status_and_is_not_retriable() -> None:
    async with httpx.AsyncClient() as client:
        provider = OpenRouterProvider(api_key="sk-bad", http_client=client)
        with respx.mock(assert_all_called=True) as mock:
            mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
                return_value=httpx.Response(401, json={"error": {"message": "invalid key"}})
            )
            with pytest.raises(ProviderError) as exc_info:
                await provider.complete(_request())

    assert exc_info.value.kind == ProviderErrorKind.AUTHENTICATION
    assert exc_info.value.retriable is False


@pytest.mark.asyncio
async def test_complete_never_logs_api_key_in_error(caplog) -> None:
    async with httpx.AsyncClient() as client:
        provider = OpenRouterProvider(api_key="sk-super-secret", http_client=client)
        with respx.mock(assert_all_called=True) as mock:
            mock.post("https://openrouter.ai/api/v1/chat/completions").mock(
                return_value=httpx.Response(500, json={"error": {"message": "boom"}})
            )
            with pytest.raises(ProviderError) as exc_info:
                await provider.complete(_request())

    assert "sk-super-secret" not in str(exc_info.value)
    assert "sk-super-secret" not in caplog.text
