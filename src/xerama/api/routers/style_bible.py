"""Style Bible CRUD/lock/version endpoints (Module 06, ADR-013)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.authorization import require_series_role
from xerama.api.deps import get_style_bible_service
from xerama.domain.enums import ProjectRole
from xerama.domain.style_bible import StyleBible
from xerama.services.style_bible_service import StyleBibleService

router = APIRouter(prefix="/series/{series_id}/style-bible", tags=["style-bible"])


class StyleBibleUpdateRequest(BaseModel):
    style_asset_id: str | None = None
    style_dna: str | None = None
    palette: list[str] | None = None
    lighting: str | None = None
    texture: str | None = None
    color_temperature: str | None = None
    composition_rules: list[str] | None = None
    negatives: list[str] | None = None


@router.get("", response_model=StyleBible, dependencies=[Depends(require_series_role(ProjectRole.VIEWER))])
async def get_style_bible(
    series_id: str, service: StyleBibleService = Depends(get_style_bible_service)
) -> StyleBible:
    return await service.get_or_create(series_id)


@router.patch("", response_model=StyleBible, dependencies=[Depends(require_series_role(ProjectRole.EDITOR))])
async def update_style_bible(
    series_id: str,
    body: StyleBibleUpdateRequest,
    service: StyleBibleService = Depends(get_style_bible_service),
) -> StyleBible:
    try:
        return await service.update(series_id, **body.model_dump(exclude_unset=True))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post(
    "/lock", response_model=StyleBible, dependencies=[Depends(require_series_role(ProjectRole.EDITOR))]
)
async def lock_style_bible(
    series_id: str, service: StyleBibleService = Depends(get_style_bible_service)
) -> StyleBible:
    return await service.lock(series_id)


@router.post(
    "/unlock", response_model=StyleBible, dependencies=[Depends(require_series_role(ProjectRole.EDITOR))]
)
async def unlock_style_bible_for_recast(
    series_id: str, service: StyleBibleService = Depends(get_style_bible_service)
) -> StyleBible:
    return await service.unlock_for_recast(series_id)
