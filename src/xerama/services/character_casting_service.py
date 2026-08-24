"""Character Casting Studio service (Module 05).

Upgrades a textual `Character` (from the cast-generation pipeline stage)
into a reusable production identity: root identity asset, multi-view
reference pack, wardrobe/physical-state variants, lock state and
provenance/consent metadata. See research/CHARACTER_CONTINUITY_PLAYBOOK.md
and ADR-012 ("persistent character roots + Character DNA").

Locking protects the root identity (visual_identity_id/reference_pack/
character_dna/identity_provenance) from silent drift - "never generate a
recurring character from scratch once the identity is approved." Wardrobe
and physical-state variants are explicitly NOT locked by this: new outfits
and states are expected to accumulate over a season regardless of whether
the character's face/body identity is locked.
"""

from xerama.domain.character import (
    Character,
    CharacterDNA,
    CharacterProvenance,
    PhysicalStateVariant,
    WardrobeVariant,
)
from xerama.repositories.interfaces import CharacterCastingRepository


class CharacterCastingService:
    def __init__(self, repo: CharacterCastingRepository) -> None:
        self._repo = repo

    async def get(self, character_id: str) -> Character:
        character = await self._repo.get_character(character_id)
        if character is None:
            raise ValueError(f"character {character_id} not found")
        return character

    async def lock(self, character_id: str) -> Character:
        return await self._repo.set_lock(character_id, locked=True)

    async def unlock_for_recast(self, character_id: str) -> Character:
        """Explicit, deliberate recast - see playbook "unless the character
        is deliberately recast". Bumps `version`."""
        return await self._repo.unlock_and_bump_version(character_id)

    async def update_identity(
        self,
        character_id: str,
        visual_identity_id: str | None = None,
        reference_pack_updates: dict[str, str] | None = None,
        character_dna: CharacterDNA | None = None,
    ) -> Character:
        character = await self.get(character_id)
        if character.locked:
            raise PermissionError(
                f"character {character_id} identity is locked - call unlock_for_recast first"
            )
        if visual_identity_id is not None:
            character.visual_identity_id = visual_identity_id
        if reference_pack_updates:
            character.reference_pack = {**character.reference_pack, **reference_pack_updates}
        if character_dna is not None:
            character.character_dna = character_dna
        return await self._repo.save_character(character)

    async def set_provenance(self, character_id: str, provenance: CharacterProvenance) -> Character:
        character = await self.get(character_id)
        if character.locked:
            raise PermissionError(
                f"character {character_id} identity is locked - call unlock_for_recast first"
            )
        character.identity_provenance = provenance
        return await self._repo.save_character(character)

    async def add_wardrobe_variant(
        self, character_id: str, label: str, reference_asset_ids: list[str] | None = None, description: str = ""
    ) -> WardrobeVariant:
        await self.get(character_id)  # 404s early if the character doesn't exist
        return await self._repo.create_wardrobe_variant(
            character_id, label, reference_asset_ids or [], description
        )

    async def list_wardrobe_variants(self, character_id: str) -> list[WardrobeVariant]:
        return await self._repo.list_wardrobe_variants(character_id)

    async def add_physical_state_variant(
        self, character_id: str, label: str, reference_asset_ids: list[str] | None = None, description: str = ""
    ) -> PhysicalStateVariant:
        await self.get(character_id)
        return await self._repo.create_physical_state_variant(
            character_id, label, reference_asset_ids or [], description
        )

    async def list_physical_state_variants(self, character_id: str) -> list[PhysicalStateVariant]:
        return await self._repo.list_physical_state_variants(character_id)
