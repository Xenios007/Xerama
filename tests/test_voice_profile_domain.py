import pytest

from xerama.domain.character import CharacterProvenance
from xerama.domain.enums import IdentityType
from xerama.domain.voice import VoiceProfile


def test_voice_profile_defaults() -> None:
    profile = VoiceProfile(id="VP_1", character_id="CHAR_001")
    assert profile.language == "en"
    assert profile.locked is False
    assert profile.version == 1
    assert profile.pronunciation_dictionary == {}
    assert profile.provenance.identity_type == IdentityType.SYNTHETIC_ORIGINAL


def test_voice_profile_reuses_character_provenance_consent_validation() -> None:
    with pytest.raises(ValueError, match="consent_reference"):
        VoiceProfile(
            id="VP_1",
            character_id="CHAR_001",
            provenance=CharacterProvenance(identity_type=IdentityType.LICENSED_AUTHORIZED),
        )


def test_voice_profile_pronunciation_dictionary_round_trips() -> None:
    profile = VoiceProfile(
        id="VP_1",
        character_id="CHAR_001",
        pronunciation_dictionary={"Mara": "MAH-rah"},
    )
    restored = VoiceProfile.model_validate_json(profile.model_dump_json())
    assert restored.pronunciation_dictionary == {"Mara": "MAH-rah"}
