"""High-level structured-output gateway used by every pipeline stage.

Application/pipeline code calls `AIGateway.generate(role=..., schema=...)`
and never touches a provider or model ID directly - see ADR-004. Invalid
JSON/schema output triggers an in-process repair retry rather than being
silently accepted - see docs/JSON_CONTRACTS.md Contract Rule 5.

Per explicit project direction, this gateway does not persist per-attempt
telemetry (no `GenerationRecord` table/service) - only structured logging.
"""

import json
import logging

from pydantic import BaseModel, ValidationError

from xerama.config import ModelRoleRegistry
from xerama.domain.enums import ModelRole
from xerama.providers.errors import ProviderError
from xerama.providers.health import ProviderHealthTracker
from xerama.providers.llm import LLMMessage, LLMProvider, LLMRequest

logger = logging.getLogger("xerama.ai_gateway")

DEFAULT_MAX_ATTEMPTS = 3


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
    ) -> None:
        self._provider = provider
        self._roles = roles
        self._health = health or ProviderHealthTracker()
        self._provider_name = provider_name
        self._max_attempts = max_attempts

    def resolve_model(self, role: ModelRole) -> str:
        """Model ID currently configured for a role - for job/telemetry labeling only."""
        return self._roles.resolve(role).model

    async def generate[T: BaseModel](
        self,
        role: ModelRole,
        schema: type[T],
        system_prompt: str,
        user_prompt: str,
    ) -> T:
        role_config = self._roles.resolve(role)
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_prompt),
        ]

        last_error: Exception | None = None
        for attempt in range(1, self._max_attempts + 1):
            request = LLMRequest(
                model=role_config.model,
                messages=messages,
                temperature=role_config.temperature,
                response_schema=schema.model_json_schema(),
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
                if not exc.retriable:
                    raise XeramaGenerationError(role, f"non-retriable provider error: {exc.message}") from exc
                last_error = exc
                continue

            self._health.record_success(self._provider_name, role_config.model)

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
