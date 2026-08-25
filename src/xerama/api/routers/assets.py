"""Asset list/detail/download/accept/reject/upload endpoints (Module 04)."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import Response

from xerama.api.deps import get_asset_service, get_media_qc_service
from xerama.domain.asset import Asset, AssetOwnership, AssetProvenance, AssetType
from xerama.domain.media_qc import MediaQCAttempt
from xerama.services.asset_service import AssetService
from xerama.services.media_qc_service import MediaQCService

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Asset])
async def list_assets(
    project_id: str,
    series_id: str | None = None,
    episode_id: str | None = None,
    character_id: str | None = None,
    scene_number: int | None = None,
    shot_number: int | None = None,
    asset_type: AssetType | None = None,
    service: AssetService = Depends(get_asset_service),
) -> list[Asset]:
    return await service.list_by_ownership(
        project_id,
        series_id=series_id,
        episode_id=episode_id,
        character_id=character_id,
        scene_number=scene_number,
        shot_number=shot_number,
        asset_type=asset_type,
    )


@router.get("/{asset_id}", response_model=Asset)
async def get_asset(asset_id: str, service: AssetService = Depends(get_asset_service)) -> Asset:
    asset = await service.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    return asset


@router.get("/{asset_id}/download")
async def download_asset(asset_id: str, service: AssetService = Depends(get_asset_service)) -> Response:
    asset = await service.get(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="asset not found")
    try:
        data = await service.read_bytes(asset_id)
    except FileNotFoundError:
        raise HTTPException(status_code=410, detail="asset file is missing from storage") from None
    return Response(content=data, media_type=asset.mime_type or "application/octet-stream")


@router.get("/{asset_id}/qc", response_model=list[MediaQCAttempt])
async def list_qc_attempts(
    asset_id: str, service: MediaQCService = Depends(get_media_qc_service)
) -> list[MediaQCAttempt]:
    """See MODULE-044 - the full audit trail (never overwritten) of every
    QC dimension check ever run on this asset."""
    return await service.list_attempts(asset_id)


@router.post("/{asset_id}/accept", response_model=Asset)
async def accept_asset(asset_id: str, service: AssetService = Depends(get_asset_service)) -> Asset:
    try:
        return await service.accept(asset_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{asset_id}/reject", response_model=Asset)
async def reject_asset(
    asset_id: str, reason: str, service: AssetService = Depends(get_asset_service)
) -> Asset:
    try:
        return await service.reject(asset_id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{asset_id}", status_code=204)
async def delete_asset(
    asset_id: str, force: bool = False, service: AssetService = Depends(get_asset_service)
) -> None:
    try:
        await service.delete(asset_id, force=force)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/upload", response_model=Asset)
async def upload_asset(
    file: UploadFile,
    project_id: str,
    asset_type: AssetType,
    series_id: str | None = None,
    episode_id: str | None = None,
    character_id: str | None = None,
    scene_number: int | None = None,
    shot_number: int | None = None,
    service: AssetService = Depends(get_asset_service),
) -> Asset:
    """Manual upload - a first-class fallback so the pipeline is never
    blocked purely by provider availability (see Module 06)."""
    data = await file.read()
    ext = "." + file.filename.rsplit(".", 1)[-1] if file.filename and "." in file.filename else ""
    ownership = AssetOwnership(
        project_id=project_id,
        series_id=series_id,
        episode_id=episode_id,
        character_id=character_id,
        scene_number=scene_number,
        shot_number=shot_number,
    )
    return await service.ingest_bytes(
        data,
        asset_type,
        ownership,
        provenance=AssetProvenance(provider="manual_upload"),
        mime_type=file.content_type or "",
        ext=ext,
    )
