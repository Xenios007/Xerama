"""Voice profile service (MODULE-034).

Same lock/immutability pattern as `StyleBibleService`/`CharacterCastingService`:
`locked=True` blocks edits until an explicit `unlock_for_recast`, which
bumps `version`. One voice profile per character - a stable identity
pointer, not a kept version history.
"""

from xerama.domain.character import CharacterProvenance
from xerama.domain.voice import VoiceProfile
from xerama.repositories.interfaces import VoiceProfileRepository


class VoiceProfileService:
    def __init__(self, repo: VoiceProfileRepository) -> None:
        self._repo = repo

    async def get_or_create(self, character_id: str) -> VoiceProfile:
        return await self._repo.get_or_create(character_id)

    async def update(
        self,
        character_id: str,
        provider: str | None = None,
        provider_voice_id: str | None = None,
        language: str | None = None,
        style: str | None = None,
        pronunciation_dictionary: dict[str, str] | None = None,
        provenance: CharacterProvenance | None = None,
    ) -> VoiceProfile:
        profile = await self.get_or_create(character_id)
        if profile.locked:
            raise PermissionError(
                f"voice profile for character {character_id} is locked - call unlock_for_recast first"
            )
        if provider is not None:
            profile.provider = provider
        if provider_voice_id is not None:
            profile.provider_voice_id = provider_voice_id
        if language is not None:
            profile.language = language
        if style is not None:
            profile.style = style
        if pronunciation_dictionary is not None:
            profile.pronunciation_dictionary = pronunciation_dictionary
        if provenance is not None:
            profile.provenance = provenance
        return await self._repo.save(profile)

    async def lock(self, character_id: str) -> VoiceProfile:
        await self.get_or_create(character_id)
        return await self._repo.set_lock(character_id, locked=True)

    async def unlock_for_recast(self, character_id: str) -> VoiceProfile:
        await self.get_or_create(character_id)
        return await self._repo.unlock_and_bump_version(character_id)
