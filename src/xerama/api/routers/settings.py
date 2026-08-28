"""Runtime provider/model settings - lets the Settings UI switch LLM
provider (OpenRouter vs a local Ollama model) and media provider (fal.ai vs
fake placeholders) without a server restart. See `api/app.py`'s
`rebuild_providers()` for how a change takes effect immediately."""

import httpx
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from xerama.api.deps import get_runtime_settings_repo
from xerama.config import get_settings
from xerama.domain.runtime_settings import RuntimeSettings
from xerama.repositories.sqlalchemy_impl import SQLAlchemyRuntimeSettingsRepository

router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    runtime: RuntimeSettings
    openrouter_key_configured: bool
    fal_key_configured: bool
    ollama_reachable: bool


class SettingsUpdateRequest(BaseModel):
    llm_provider: str | None = None
    ollama_model: str | None = None
    ollama_base_url: str | None = None
    media_provider: str | None = None
    chat_model: str | None = None


async def _ollama_reachable(base_url: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            response = await client.get(f"{base_url.rstrip('/')}/models")
        return response.status_code < 500
    except httpx.HTTPError:
        return False


async def _build_response(runtime: RuntimeSettings) -> SettingsResponse:
    settings = get_settings()
    return SettingsResponse(
        runtime=runtime,
        openrouter_key_configured=bool(settings.openrouter_api_key.get_secret_value()),
        fal_key_configured=bool(settings.fal_api_key.get_secret_value()),
        ollama_reachable=await _ollama_reachable(runtime.ollama_base_url),
    )


@router.get("", response_model=SettingsResponse)
async def get_settings_endpoint(
    repo: SQLAlchemyRuntimeSettingsRepository = Depends(get_runtime_settings_repo),
) -> SettingsResponse:
    runtime = await repo.get_or_create()
    return await _build_response(runtime)


@router.patch("", response_model=SettingsResponse)
async def update_settings_endpoint(
    payload: SettingsUpdateRequest,
    http_request: Request,
    repo: SQLAlchemyRuntimeSettingsRepository = Depends(get_runtime_settings_repo),
) -> SettingsResponse:
    fields = {k: v for k, v in payload.model_dump().items() if v is not None}
    runtime = await repo.update(**fields) if fields else await repo.get_or_create()

    # Local import avoids a circular import (app.py imports this router).
    from xerama.api.app import rebuild_providers

    rebuild_providers(http_request.app, get_settings(), runtime, http_request.app.state.http_client)
    return await _build_response(runtime)
