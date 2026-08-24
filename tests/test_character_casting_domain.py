import pytest

from xerama.domain.character import (
    Character,
    CharacterDNA,
    CharacterProvenance,
    PhysicalStateVariant,
    WardrobeVariant,
    format_character_dna,
)
from xerama.domain.enums import IdentityType


def test_character_identity_defaults() -> None:
    character = Character(id="CHAR_001", name="Mara", role="protagonist")
    assert character.locked is False
    assert character.version == 1
    assert character.reference_pack == {}
    assert character.identity_provenance.identity_type == IdentityType.SYNTHETIC_ORIGINAL
    assert character.identity_provenance.consent_reference == ""


def test_licensed_identity_requires_consent_reference() -> None:
    with pytest.raises(ValueError, match="consent_reference"):
        CharacterProvenance(identity_type=IdentityType.LICENSED_AUTHORIZED)


def test_licensed_identity_with_consent_reference_is_valid() -> None:
    provenance = CharacterProvenance(
        identity_type=IdentityType.LICENSED_AUTHORIZED, consent_reference="LICENSE-2026-001"
    )
    assert provenance.consent_reference == "LICENSE-2026-001"


def test_format_character_dna_uses_structured_fields() -> None:
    character = Character(
        id="CHAR_001",
        name="Mara",
        role="protagonist",
        description="a tired detective",
        character_dna=CharacterDNA(eyes="brown", hairstyle="short bob", hair_color="black"),
    )
    text = format_character_dna(character)
    assert text.startswith("Mara: ")
    assert "brown" in text and "short bob" in text and "black" in text
    assert "tired detective" not in text  # DNA fields present - description is not the fallback


def test_format_character_dna_falls_back_to_description() -> None:
    character = Character(
        id="CHAR_001", name="Mara", role="protagonist", description="a tired detective"
    )
    assert format_character_dna(character) == "Mara: a tired detective"


def test_format_character_dna_falls_back_to_bare_name() -> None:
    character = Character(id="CHAR_001", name="Mara", role="protagonist")
    assert format_character_dna(character) == "Mara"


def test_wardrobe_and_physical_state_variant_construction() -> None:
    wardrobe = WardrobeVariant(
        id="WARD_001",
        character_id="CHAR_001",
        label="office_black_dress",
        reference_asset_ids=["asset-1"],
    )
    state = PhysicalStateVariant(
        id="STATE_001", character_id="CHAR_001", label="injured", reference_asset_ids=["asset-2"]
    )
    assert wardrobe.character_id == state.character_id == "CHAR_001"
    assert wardrobe.reference_asset_ids == ["asset-1"]
    assert state.label == "injured"
