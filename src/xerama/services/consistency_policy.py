"""Centralized reference/DNA/wardrobe/style selection policy (Module 05,
ADR-014).

"Character/style/location/continuity reference selection belongs in a
centralized policy/compiler layer. Individual generation stages should not
independently improvise reference strategy." This is the one place that
decides, per character per shot, which reference images to send a
provider - the Prompt Compiler (Module 03) consults it instead of picking
`visual_identity_id` on its own.

Pure/deterministic: no I/O, no LLM call - same inputs always produce the
same selection, matching the Prompt Compiler's own determinism requirement.
"""

from pydantic import BaseModel, Field

from xerama.domain.character import Character, PhysicalStateVariant, WardrobeVariant, format_character_dna

# Providers cap how many reference images they accept per subject - see
# research/CHARACTER_CONTINUITY_PLAYBOOK.md "Reference pack" ("excessive
# references can complicate routing and providers cap reference count").
# This is a conservative default until Module 07's provider router exposes
# real per-provider limits.
DEFAULT_MAX_REFERENCES_PER_CHARACTER = 4

# Lean starter reference pack per playbook "For Xerama trial production,
# start lean" - preference order when no specific view is requested.
DEFAULT_VIEW_PREFERENCE: tuple[str, ...] = ("front", "three_quarter", "side", "full_body")


class CharacterReferenceSelection(BaseModel):
    character_id: str
    dna_text: str
    reference_asset_ids: list[str] = Field(default_factory=list)
    wardrobe_asset_ids: list[str] = Field(default_factory=list)
    physical_state_asset_ids: list[str] = Field(default_factory=list)


class ConsistencyPolicy:
    def select_for_character(
        self,
        character: Character,
        max_references: int = DEFAULT_MAX_REFERENCES_PER_CHARACTER,
        preferred_views: tuple[str, ...] = DEFAULT_VIEW_PREFERENCE,
        wardrobe_variant: WardrobeVariant | None = None,
        physical_state_variant: PhysicalStateVariant | None = None,
    ) -> CharacterReferenceSelection:
        candidates: list[str] = []
        if character.visual_identity_id:
            candidates.append(character.visual_identity_id)
        for view in preferred_views:
            asset_id = character.reference_pack.get(view)
            if asset_id:
                candidates.append(asset_id)
        wardrobe_ids = list(wardrobe_variant.reference_asset_ids) if wardrobe_variant else []
        physical_state_ids = (
            list(physical_state_variant.reference_asset_ids) if physical_state_variant else []
        )
        candidates.extend(wardrobe_ids)
        candidates.extend(physical_state_ids)

        # Deduplicate while preserving selection order (root first).
        seen: set[str] = set()
        ordered_unique = [c for c in candidates if not (c in seen or seen.add(c))]

        if not ordered_unique:
            # No identity assets exist yet (pre-image-generation, or an
            # unlocked character mid-recast) - fall back to the character's
            # own id so downstream compilation always has a stable handle.
            ordered_unique = [character.id]

        bounded = ordered_unique[:max_references]
        return CharacterReferenceSelection(
            character_id=character.id,
            dna_text=format_character_dna(character),
            reference_asset_ids=bounded,
            wardrobe_asset_ids=[a for a in wardrobe_ids if a in bounded],
            physical_state_asset_ids=[a for a in physical_state_ids if a in bounded],
        )

    def select_for_shot(
        self,
        characters: list[Character],
        max_references_per_character: int = DEFAULT_MAX_REFERENCES_PER_CHARACTER,
        wardrobe_variants_by_character: dict[str, WardrobeVariant] | None = None,
        physical_state_variants_by_character: dict[str, PhysicalStateVariant] | None = None,
    ) -> list[CharacterReferenceSelection]:
        """Multi-character reference selection: each character's references
        are selected independently from its own identity package, so one
        character's references never leak into another's selection."""
        wardrobe_variants_by_character = wardrobe_variants_by_character or {}
        physical_state_variants_by_character = physical_state_variants_by_character or {}
        return [
            self.select_for_character(
                character,
                max_references=max_references_per_character,
                wardrobe_variant=wardrobe_variants_by_character.get(character.id),
                physical_state_variant=physical_state_variants_by_character.get(character.id),
            )
            for character in characters
        ]
