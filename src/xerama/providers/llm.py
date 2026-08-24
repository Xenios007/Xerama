"""LLM provider contract. OpenAI-compatible request/response shape so any
future OpenAI-compatible gateway can implement the same Protocol - see
ADR-002."""

from typing import Literal, Protocol

from pydantic import BaseModel


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    model: str
    messages: list[LLMMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    response_schema: dict | None = None
    schema_name: str = "xerama_output"


class LLMResponse(BaseModel):
    content: str
    latency_ms: float
    model: str
    finish_reason: str | None = None
    prompt_tokens: int | None = None
    completion_tokens: int | None = None


class LLMProvider(Protocol):
    """Any LLM gateway Xerama talks to (OpenRouter today, others later)."""

    async def complete(self, request: LLMRequest) -> LLMResponse: ...
