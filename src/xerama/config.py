"""Runtime configuration: environment settings and model-role resolution.

See docs/AI_MODELS.md and ADR-004 - model IDs are configuration, never
hard-coded in business logic. Free-model defaults below were snapshotted
from the OpenRouter catalog on 2026-08-24 (see research/FREE_FIRST_MODEL_STRATEGY.md);
free-tier availability changes, so these are override-able fallbacks, not a
permanent assumption.
"""

from functools import lru_cache

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict

from xerama.domain.enums import ModelRole

# Snapshotted 2026-08-24 from https://openrouter.ai/api/v1/models (":free" ids).
# Re-verify against the live catalog before relying on these in production -
# see research/CODING_READINESS_CHECKLIST.md "Snapshot exact free LLM candidates".
_DEFAULT_FREE_MODELS = {
    ModelRole.CONCEPT_GENERATOR_A: "dots-studio/dots-3-note-preview:free",
    ModelRole.CONCEPT_GENERATOR_B: "nvidia/nemotron-3.5-lightning:free",
    ModelRole.JUDGE: "thinkingmachines/inkling:free",
    ModelRole.STORY_ARCHITECT: "liquid/lfm-2.5-2.6b:free",
    ModelRole.EPISODE_WRITER: "poolside/laguna-s-2.1:free",
    ModelRole.CONTINUITY_CHECKER: "thinkingmachines/inkling-small:free",
    ModelRole.RETENTION_CRITIC: "dots-studio/dots-3-note-preview:free",
    ModelRole.SHOT_PLANNER: "nvidia/nemotron-3.5-lightning:free",
    ModelRole.SHOWRUNNER: "thinkingmachines/inkling:free",
}

# Temperature guidance per docs/AI_MODELS.md "Temperature Guidance".
_DEFAULT_TEMPERATURES = {
    ModelRole.CONCEPT_GENERATOR_A: 0.9,
    ModelRole.CONCEPT_GENERATOR_B: 0.9,
    ModelRole.JUDGE: 0.3,
    ModelRole.STORY_ARCHITECT: 0.7,
    ModelRole.EPISODE_WRITER: 0.85,
    ModelRole.CONTINUITY_CHECKER: 0.1,
    ModelRole.RETENTION_CRITIC: 0.3,
    ModelRole.SHOT_PLANNER: 0.4,
    ModelRole.SHOWRUNNER: 0.4,
}

_ROLE_ENV_VAR = {
    ModelRole.CONCEPT_GENERATOR_A: "CONCEPT_MODEL_A",
    ModelRole.CONCEPT_GENERATOR_B: "CONCEPT_MODEL_B",
    ModelRole.JUDGE: "JUDGE_MODEL",
    ModelRole.STORY_ARCHITECT: "STORY_ARCHITECT_MODEL",
    ModelRole.EPISODE_WRITER: "EPISODE_WRITER_MODEL",
    ModelRole.CONTINUITY_CHECKER: "CONTINUITY_MODEL",
    ModelRole.RETENTION_CRITIC: "RETENTION_CRITIC_MODEL",
    ModelRole.SHOT_PLANNER: "SHOT_PLANNER_MODEL",
    ModelRole.SHOWRUNNER: "SHOWRUNNER_MODEL",
}


class Settings(BaseSettings):
    """Environment-backed application settings. Never log `openrouter_api_key`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    xerama_mode: str = "standard"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./xerama.db"
    asset_storage_path: str = "./storage"

    concept_model_a: str = ""
    concept_model_b: str = ""
    judge_model: str = ""
    story_architect_model: str = ""
    episode_writer_model: str = ""
    continuity_model: str = ""
    retention_critic_model: str = ""
    shot_planner_model: str = ""
    showrunner_model: str = ""


class RoleModelConfig(BaseModel):
    role: ModelRole
    model: str
    temperature: float


class ModelRoleRegistry:
    """Resolves a logical `ModelRole` to a concrete provider model + parameters.

    Application/pipeline code must call `resolve(role)` rather than embed a
    model ID directly - see ADR-004.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def resolve(self, role: ModelRole) -> RoleModelConfig:
        env_field = _ROLE_ENV_VAR[role].lower()
        configured = getattr(self._settings, env_field, "") or ""
        model = configured or _DEFAULT_FREE_MODELS[role]
        return RoleModelConfig(
            role=role,
            model=model,
            temperature=_DEFAULT_TEMPERATURES[role],
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
