"""High-level structured-output gateway used by every pipeline stage.

Application/pipeline code calls `AIGateway.generate(role=..., schema=...)`
and never touches a provider or model ID directly - see ADR-004. Invalid
JSON/schema output triggers an in-process repair retry rather than being
silently accepted - see docs/JSON_CONTRACTS.md Contract Rule 5.

Per-attempt cost telemetry (MODULE-049) is optional and additive: pass a
`CostRecordService` to persist one `CostRecord` per attempt (token usage
from the provider response, monetary cost `unknown` since no live pricing
API is integrated for any provider in this codebase yet); omit it and
this gateway behaves exactly as it did under the earlier "telemetry
disabled for this build" note - only structured logging, no persistence.
"""

import json
import logging

from pydantic import BaseModel, ValidationError

from xerama.config import ModelRoleRegistry
from xerama.domain.enums import ModelRole
from xerama.providers.errors import ProviderError
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.llm import LLMMessage, LLMProvider, LLMRequest
from xerama.services.cost_service import CostRecordService

logger = logging.getLogger("xerama.ai_gateway")

DEFAULT_MAX_ATTEMPTS = 3


def _strict_json_schema(node: object) -> object:
    """Recursively rewrite a Pydantic-generated JSON Schema so it satisfies
    OpenAI/OpenRouter "strict" structured-output mode: every object schema
    needs `additionalProperties: false` and every property listed in
    `required` (Pydantic only lists fields without a default) - see
    https://platform.openai.com/docs/guides/structured-outputs. Without
    this, strict-mode providers reject the request outright with HTTP 400
    rather than silently ignoring the schema like non-strict providers do."""
    if isinstance(node, dict):
        result = {k: _strict_json_schema(v) for k, v in node.items()}
        if "$ref" in result:
            # OpenAI strict mode: a $ref must be the only key in its object -
            # Pydantic adds a sibling "default" for fields like `x: Enum = Y`.
            return {"$ref": result["$ref"]}
        if result.get("type") == "object":
            if "properties" in result:
                result["additionalProperties"] = False
                result["required"] = list(result["properties"].keys())
            elif "additionalProperties" in result:
                # An open-ended map (e.g. `dict[str, str]`) has no fixed key
                # set, which strict mode can't express (it requires every
                # property enumerated in `required`) - force it to the empty
                # object; these fields default to {} and are populated by
                # non-LLM code later (e.g. Character.reference_pack).
                result["properties"] = {}
                result["required"] = []
                result["additionalProperties"] = False
        return result
    if isinstance(node, list):
        return [_strict_json_schema(item) for item in node]
    return node


class XeramaGenerationError(Exception):
    """Raised when a role's structured output could not be produced/validated
    after retries, or the provider failed with a non-retriable error."""

    def __init__(self, role: ModelRole, message: str) -> None:
        super().__init__(f"[{role.value}] {message}")
        self.role = role


class AIGateway:
    def __init__(
        self,
        provider: LLMProvider,
        roles: ModelRoleRegistry,
        health: ProviderHealthTracker | None = None,
        provider_name: str = "openrouter",
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        cost_recorder: CostRecordService | None = None,
    ) -> None:
        self._provider = provider
        self._roles = roles
        self._health = health or ProviderHealthTracker()
        self._provider_name = provider_name
        self._max_attempts = max_attempts
        self._cost_recorder = cost_recorder

    def resolve_model(self, role: ModelRole) -> str:
        """Model ID currently configured for a role - for job/telemetry labeling only."""
        return self._roles.resolve(role).model

    async def generate[T: BaseModel](
        self,
        role: ModelRole,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
        project_id: str | None = None,
        series_id: str | None = None,
        episode_id: str | None = None,
    ) -> T:
        role_config = self._roles.resolve(role)
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        response_schema = _strict_json_schema(schema.model_json_schema())

        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            request = LLMRequest(
                model=role_config.model,
                messages=messages,
                temperature=role_config.temperature,
                response_schema=response_schema,
                schema_name=schema.__name__,
            )
            try:
                response = await self._provider.complete(request)
            except ProviderError as exc:
                self._health.record_failure(self._provider_name, role_config.model, exc.kind)
                logger.warning(
                    "provider error role=%s model=%s kind=%s attempt=%d",
                    role.value,
                    role_config.model,
                    exc.kind.value,
                    attempt,
                )
                await self._record_cost(
                    role_config.model, role.value, attempt, project_id, series_id, episode_id,
                    failure_reason=f"{exc.kind.value}: {exc.message}",
                )
                if not exc.retriable:
                    raise XeramaGenerationError(role, f"non-retriable provider error: {exc.message}") from exc
                last_error = exc
                continue

            self._health.record_success(self._provider_name, role_config.model)
            tokens = (response.prompt_tokens or 0) + (response.completion_tokens or 0)
            await self._record_cost(
                role_config.model, role.value, attempt, project_id, series_id, episode_id,
                quantity=float(tokens), unit="tokens", latency_ms=response.latency_ms,
            )

            try:
                parsed = schema.model_validate(json.loads(response.content))
                return parsed
            except (json.JSONDecodeError, ValidationError) as exc:
                logger.warning(
                    "schema validation failed role=%s model=%s attempt=%d error=%s",
                    role.value,
                    role_config.model,
                    attempt,
                    exc,
                )
                last_error = exc
                messages.append(LLMMessage(role="assistant", content=response.content))
                messages.append(
                    LLMMessage(
                        role="user",
                        content=(
                            "That response was not valid JSON matching the required schema. "
                            f"Error: {exc}. Reply again with ONLY corrected JSON matching the schema."
                        ),
                    )
                )
                continue

        raise XeramaGenerationError(
            role, f"failed to produce valid {schema.__name__} after {self._max_attempts} attempts"
        ) from last_error

    async def _record_cost(
        self,
        model: str,
        stage: str,
        attempt: int,
        project_id: str | None,
        series_id: str | None,
        episode_id: str | None,
        quantity: float = 0.0,
        unit: str = "",
        latency_ms: float | None = None,
        failure_reason: str = "",
    ) -> None:
        if self._cost_recorder is None:
            return
        await self._cost_recorder.record(
            provider=self._provider_name,
            model=model,
            stage=stage,
            project_id=project_id,
            series_id=series_id,
            episode_id=episode_id,
            attempt=attempt,
            quantity=quantity,
            unit=unit,
            cost_known=False,  # no live pricing API integrated for any provider yet
            latency_ms=latency_ms,
            failure_reason=failure_reason,
        )
