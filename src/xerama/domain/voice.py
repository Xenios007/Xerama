"""Voice profile domain contract (MODULE-034).

"Never assume cloning rights; provenance is required for external
likeness/voice" - reuses `CharacterProvenance` (Module 05) directly rather
than duplicating an almost-identical identity_type/consent_reference model;
the rights-consent semantics are the same for a face and a voice.
"""

from pydantic import BaseModel, Field

from xerama.domain.character import CharacterProvenance


class VoiceProfile(BaseModel):
    """One profile per character - the stable pointer dialogue audio
    (MODULE-035) and lip sync (MODULE-036) resolve to, so a character's
    voice survives a TTS-provider swap (research/PRODUCTION_STACK_2026.md
    "Voice should be stored as a character asset independent from the
    video provider")."""

    id: str
    character_id: str
    provider: str = ""
    provider_voice_id: str = ""
    language: str = "en"
    style: str = ""
    pronunciation_dictionary: dict[str, str] = Field(default_factory=dict)
    provenance: CharacterProvenance = Field(default_factory=CharacterProvenance)
    locked: bool = False
    version: int = 1
