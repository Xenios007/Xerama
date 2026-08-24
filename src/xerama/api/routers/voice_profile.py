"""Voice profile CRUD/lock/version endpoints (MODULE-034)."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from xerama.api.deps import get_voice_profile_service
from xerama.domain.character import CharacterProvenance
from xerama.domain.voice import VoiceProfile
from xerama.services.voice_profile_service import VoiceProfileService

router = APIRouter(prefix="/characters/{character_id}/voice-profile", tags=["voice-profile"])


class VoiceProfileUpdateBody(BaseModel):
    provider: str | None = None
    provider_voice_id: str | None = None
    language: str | None = None
    style: str | None = None
    pronunciation_dictionary: dict[str, str] | None = None
    provenance: CharacterProvenance | None = None


@router.get("", response_model=VoiceProfile)
async def get_voice_profile(
    character_id: str, service: VoiceProfileService = Depends(get_voice_profile_service)
) -> VoiceProfile:
    return await service.get_or_create(character_id)


@router.patch("", response_model=VoiceProfile)
async def update_voice_profile(
    character_id: str,
    body: VoiceProfileUpdateBody,
    service: VoiceProfileService = Depends(get_voice_profile_service),
) -> VoiceProfile:
    try:
        return await service.update(character_id, **body.model_dump(exclude_unset=True))
    except PermissionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/lock", response_model=VoiceProfile)
async def lock_voice_profile(
    character_id: str, service: VoiceProfileService = Depends(get_voice_profile_service)
) -> VoiceProfile:
    return await service.lock(character_id)


@router.post("/unlock", response_model=VoiceProfile)
async def unlock_voice_profile_for_recast(
    character_id: str, service: VoiceProfileService = Depends(get_voice_profile_service)
) -> VoiceProfile:
    return await service.unlock_for_recast(character_id)
