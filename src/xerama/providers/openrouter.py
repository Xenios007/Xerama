"""OpenRouter LLM provider. First model gateway - see ADR-002.

Uses the OpenAI-compatible `/chat/completions` endpoint with JSON-schema
structured outputs where a schema is supplied - see
research/FREE_FIRST_MODEL_STRATEGY.md "Structured outputs".
"""

import time

import httpx

from xerama.domain.enums import ProviderErrorKind
from xerama.providers.errors import ProviderError, classify_status_code
from xerama.providers.llm import LLMRequest, LLMResponse

_PROVIDER_NAME = "openrouter"


class OpenRouterProvider:
    """Implements the `LLMProvider` Protocol against OpenRouter."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._client = http_client or httpx.AsyncClient(timeout=timeout)

    @property
    def name(self) -> str:
        return _PROVIDER_NAME

    async def aclose(self) -> None:
        if self._owns_client:
            await self._client.aclose()

    def _headers(self) -> dict:
        # Never log this dict - it carries the bearer credential.
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Xenios007/Xerama",
            "X-Title": "Xerama",
        }

    def _payload(self, request: LLMRequest) -> dict:
        payload: dict = {
            "model": request.model,
            "messages": [m.model_dump() for m in request.messages],
            "temperature": request.temperature,
        }
        if request.max_tokens is not None:
            payload["max_tokens"] = request.max_tokens
        if request.response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.response_schema,
                },
            }
        return payload

    async def complete(self, request: LLMRequest) -> LLMResponse:
        if not self._api_key:
            raise ProviderError(
                ProviderErrorKind.AUTHENTICATION,
                "OPENROUTER_API_KEY is not configured",
            )

        started = time.perf_counter()
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers=self._headers(),
                json=self._payload(request),
            )
        except httpx.TimeoutException as exc:
            raise ProviderError(ProviderErrorKind.TIMEOUT, "OpenRouter request timed out") from exc
        except httpx.RequestError as exc:
            raise ProviderError(
                ProviderErrorKind.TRANSIENT_FAILURE, f"OpenRouter request failed: {exc!r}"
            ) from exc

        latency_ms = (time.perf_counter() - started) * 1000

        if response.status_code >= 400:
            kind = classify_status_code(response.status_code)
            message = _safe_error_message(response)
            raise ProviderError(kind, message, status_code=response.status_code)

        body = response.json()
        choices = body.get("choices") or []
        if not choices:
            raise ProviderError(ProviderErrorKind.UNKNOWN, "OpenRouter response had no choices")

        message = choices[0].get("message", {})
        usage = body.get("usage") or {}

        return LLMResponse(
            content=message.get("content", ""),
            latency_ms=latency_ms,
            model=body.get("model", request.model),
            finish_reason=choices[0].get("finish_reason"),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )


def _safe_error_message(response: httpx.Response) -> str:
    try:
        body = response.json()
        return str(body.get("error", {}).get("message", response.text))[:500]
    except ValueError:
        return response.text[:500]
