"""Character Casting Studio CRUD/lock/version endpoints (Module 05)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from xerama.api.deps import get_character_casting_service
from xerama.domain.character import (
    Character,
    CharacterDNA,
    CharacterProvenance,
    PhysicalStateVariant,
    WardrobeVariant,
)
from xerama.services.character_casting_service import CharacterCastingService

router = APIRouter(prefix="/characters", tags=["characters"])


class IdentityUpdateRequest(BaseModel):
    visual_identity_id: str | None = None
    reference_pack_updates: dict[str, str] | None = None
    character_dna: CharacterDNA | None = None


class VariantCreateRequest(BaseModel):
    label: str
    reference_asset_ids: list[str] = Field(default_factory=list)
    description: str = ""


@router.get("/{character_id}", response_model=Character)
async def get_character(
    character_id: str, service: CharacterCastingService = Depends(get_character_casting_service)
) -> Character:
    try:
        return await service.get(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{character_id}/lock", response_model=Character)
async def lock_character(
    character_id: str, service: CharacterCastingService = Depends(get_character_casting_service)
) -> Character:
    try:
        return await service.lock(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{character_id}/unlock", response_model=Character)
async def unlock_character_for_recast(
    character_id: str, service: CharacterCastingService = Depends(get_character_casting_service)
) -> Character:
    """Explicit deliberate recast - unlocks and bumps `version`."""
    try:
        return await service.unlock_for_recast(character_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.patch("/{character_id}/identity", response_model=Character)
async def update_identity(
    character_id: str,
    body: IdentityUpdateRequest,
    service: CharacterCastingService = Depends(get_character_casting_service),
) -> Character:
    try:
        return await service.update_identity(
            character_id,
            visual_identity_id=body.visual_identity_id,
            reference_pack_updates=body.reference_pack_updates,
            character_dna=body.character_dna,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{character_id}/provenance", response_model=Character)
async def set_provenance(
    character_id: str,
    body: CharacterProvenance,
    service: CharacterCastingService = Depends(get_character_casting_service),
) -> Character:
    try:
        return await service.set_provenance(character_id, body)
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/{character_id}/wardrobe", response_model=WardrobeVariant)
async def add_wardrobe_variant(
    character_id: str,
    body: VariantCreateRequest,
    service: CharacterCastingService = Depends(get_character_casting_service),
) -> WardrobeVariant:
    try:
        return await service.add_wardrobe_variant(
            character_id, body.label, body.reference_asset_ids, body.description
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{character_id}/wardrobe", response_model=list[WardrobeVariant])
async def list_wardrobe_variants(
    character_id: str, service: CharacterCastingService = Depends(get_character_casting_service)
) -> list[WardrobeVariant]:
    return await service.list_wardrobe_variants(character_id)


@router.post("/{character_id}/physical-states", response_model=PhysicalStateVariant)
async def add_physical_state_variant(
    character_id: str,
    body: VariantCreateRequest,
    service: CharacterCastingService = Depends(get_character_casting_service),
) -> PhysicalStateVariant:
    try:
        return await service.add_physical_state_variant(
            character_id, body.label, body.reference_asset_ids, body.description
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/{character_id}/physical-states", response_model=list[PhysicalStateVariant])
async def list_physical_state_variants(
    character_id: str, service: CharacterCastingService = Depends(get_character_casting_service)
) -> list[PhysicalStateVariant]:
    return await service.list_physical_state_variants(character_id)
