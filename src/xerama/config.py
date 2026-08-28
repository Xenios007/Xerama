"""Runtime configuration: environment settings and model-role resolution.

See docs/AI_MODELS.md and ADR-004 - model IDs are configuration, never
hard-coded in business logic. Free-model defaults below were snapshotted
from the OpenRouter catalog on 2026-08-24 (see research/FREE_FIRST_MODEL_STRATEGY.md);
free-tier availability changes, so these are override-able fallbacks, not a
permanent assumption.
"""

from functools import lru_cache

from pydantic import BaseModel, SecretStr
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

# Public: the `Settings` field name for every role's model override - used by
# `api/app.py`'s `rebuild_providers()` to point every role at one local model
# when the runtime-settings LLM provider is "ollama".
ROLE_MODEL_FIELDS: tuple[str, ...] = tuple(v.lower() for v in _ROLE_ENV_VAR.values())


class Settings(BaseSettings):
    """Environment-backed application settings. `openrouter_api_key` is a
    `SecretStr` so it never appears in plain text in a log line, repr(),
    or accidental str() of the settings object (MODULE-002 "never log or
    commit secrets") - callers must explicitly call `.get_secret_value()`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openrouter_api_key: SecretStr = SecretStr("")
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    # Real image/video adapters (providers/fal_image.py, providers/fal_video.py) -
    # unset falls back to the fake providers, same "fake now, real adapter
    # later" pattern as every other external provider in this codebase.
    fal_api_key: SecretStr = SecretStr("")
    # Chat assistant (api/routers/chat.py) - rides openrouter_api_key above,
    # no separate key: see chat.py's module docstring for why.

    xerama_mode: str = "standard"
    log_level: str = "INFO"

    database_url: str = "sqlite+aiosqlite:///./xerama.db"
    asset_storage_path: str = "./storage"
    # MODULE-066 - ceiling on a single manual `/assets/upload` (see
    # pipeline/upload_validation.py). Provider-generated assets never go
    # through this check - only client-supplied bytes are untrusted.
    max_upload_size_bytes: int = 200 * 1024 * 1024

    # MODULE-068 - rate/concurrency/budget guards on expensive
    # generation endpoints (pipeline/rate_limiting.py,
    # services/budget_service.py). Defaults are deliberately permissive
    # ("local trusted mode may use permissive defaults") so standard
    # (local single-user) mode and the existing test suite are
    # unaffected; a hosted deployment tightens these via env vars.
    rate_limit_requests_per_window: int = 1000
    rate_limit_window_seconds: float = 60.0
    rate_limit_max_concurrent_per_project: int = 20
    # None = unlimited (the standard-mode default).
    project_budget_ceiling_usd: float | None = None
    # Binary name/path for last-frame extraction (Module 08/MODULE-032) and
    # episode assembly (MODULE-046) - override if ffmpeg isn't on PATH
    # under this exact name.
    ffmpeg_path: str = "ffmpeg"
    # Binary name/path for export validation (MODULE-048).
    ffprobe_path: str = "ffprobe"
    # MODULE-070 - a malformed/pathological input can hang ffmpeg/ffprobe
    # indefinitely; every subprocess call is killed and the request fails
    # cleanly past this many seconds rather than hanging the request
    # forever. 300s is generous for a short vertical microdrama episode.
    ffmpeg_timeout_seconds: float = 300.0
    # MODULE-055 - comma-separated allowed origins for the frontend studio
    # shell. Defaults to the Vite dev server; production deployments
    # override with their actual origin(s) - never "*" with credentials.
    cors_allowed_origins: str = "http://localhost:5173"

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
